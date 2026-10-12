"""Barreiras da aplicação local. Não substituem isolamento e segurança do Windows."""
import asyncio
import ipaddress
import secrets
import stat
import time
from collections import deque
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import JSONResponse


class SecurityError(ValueError):
    pass


def safe_path(root, relative, *, private=False):
    root = root.resolve()
    value = str(relative)
    if "\x00" in value or ":" in value or PureWindowsPath(value).drive or Path(value).is_absolute():
        raise SecurityError("Use um caminho relativo, sem drive, stream NTFS ou caracteres especiais.")
    candidate = root / value
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise SecurityError("Caminho fora da pasta autorizada.")
    parts = candidate.relative_to(root).parts
    if ".." in parts:
        raise SecurityError("Navegação para pasta superior não autorizada.")
    if not private and (any(part.startswith(".") for part in parts) or resolved.name.casefold() in {
        "api_keys.json", "fish_audio.json", "ai_council.json", "credentials.json", "token.json"
    }):
        raise SecurityError("Arquivos internos e credenciais não são acessíveis.")
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise SecurityError("Links simbólicos não são permitidos.")
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024):
            raise SecurityError("Junctions e outros reparse points não são permitidos.")
        if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink > 1:
            raise SecurityError("Arquivos com hard links não são permitidos.")
    return candidate


def local_endpoint(url):
    parsed = urlsplit(url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SecurityError("Modo local: o modelo deve executar no loopback deste computador.")


class SecurityMiddleware:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings
        self.failures = deque()
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        application = scope.get('app')
        monitor = getattr(application.state, 'monitor', None) if application else None
        def denied():
            if monitor:
                monitor.denied()
        host = headers.get('host', '')
        try:
            parsed = urlsplit('http://' + host)
            valid_host = parsed.hostname in {'localhost', '127.0.0.1', '::1'} and not parsed.username and not parsed.password
            parsed.port  # valida também o formato da porta
        except ValueError:
            valid_host = False
        if not valid_host:
            denied()
            return await JSONResponse({'detail': 'Host não autorizado.'}, 400)(scope, receive, send)
        client = scope.get('client')
        try:
            local = bool(client) and ipaddress.ip_address(client[0]).is_loopback
        except ValueError:
            local = False
        if not local:
            denied()
            return await JSONResponse({'detail': 'O Cronos aceita somente conexões deste computador.'}, 403)(scope, receive, send)
        origin = headers.get('origin')
        own_origin = scope.get('scheme', 'http') + '://' + host
        allowed = {own_origin, *[value.rstrip('/') for value in self.settings.origins]}
        if origin and origin not in allowed:
            denied()
            return await JSONResponse({'detail': 'Origin não autorizada.'}, 403)(scope, receive, send)
        path = scope.get('path', '')
        public = path in {'/', '/tests', '/health', '/docs', '/docs/oauth2-redirect', '/redoc', '/openapi.json'} or path.startswith(('/static/', '/ui/'))
        preflight = scope.get('method') == 'OPTIONS' and bool(origin)
        if not public and not preflight:
            now = time.monotonic()
            while self.failures and self.failures[0] < now - 60:
                self.failures.popleft()
            if len(self.failures) >= 30:
                return await JSONResponse({'detail': 'Muitas tentativas de acesso. Aguarde um minuto.'}, 429)(scope, receive, send)
            if not self.settings.token:
                return await JSONResponse({'detail': 'Configure CRONOS_API_TOKEN antes de acessar os dados.'}, 503)(scope, receive, send)
            supplied = headers.get('authorization', '').encode('utf-8')
            expected = ('Bearer ' + self.settings.token).encode('utf-8')
            if not secrets.compare_digest(supplied, expected):
                self.failures.append(now)
                denied()
                return await JSONResponse({'detail': 'Autenticação necessária.'}, 401)(scope, receive, send)
        limit = 10 * 1024 * 1024 if path == '/voice/transcribe' else 3 * 1024 * 1024 if path == '/vision/analyze' else 2 * 1024 * 1024 if path == '/vision/preview' else 256 * 1024
        try:
            length = int(headers.get('content-length', '0'))
            if length < 0:
                raise ValueError()
        except ValueError:
            return await JSONResponse({'detail': 'Content-Length inválido.'}, 400)(scope, receive, send)
        if length > limit:
            return await JSONResponse({'detail': 'Requisição acima do limite de tamanho.'}, 413)(scope, receive, send)
        async def secure_send(event):
            if event['type'] == 'http.response.start':
                if monitor:
                    monitor.response(path, event['status'])
                additions = {
                    'x-content-type-options': 'nosniff', 'x-frame-options': 'SAMEORIGIN' if path == '/tests' else 'DENY',
                    'referrer-policy': 'no-referrer', 'cache-control': 'no-store',
                    'permissions-policy': 'microphone=(self), camera=(self), geolocation=()',
                    'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'; frame-ancestors " + ("'self'" if path == '/tests' else "'none'") + "; base-uri 'none'; form-action 'self'",
                }
                event['headers'] = [(key, value) for key, value in event.get('headers', []) if key.decode().lower() not in additions]
                event['headers'] += [(key.encode(), value.encode()) for key, value in additions.items()]
            await send(event)
        if not public and not preflight and self.active >= 4:
            return await JSONResponse({'detail': 'Cronos ocupado. Aguarde as solicitações atuais.'}, 429)(scope, receive, secure_send)
        self.active += 1
        try:
            body = bytearray()
            if scope.get('method') in {'POST', 'PUT', 'PATCH'} or length or headers.get('transfer-encoding'):
                deadline = time.monotonic() + 30
                while True:
                    try:
                        event = await asyncio.wait_for(receive(), timeout=max(.01, deadline - time.monotonic()))
                    except asyncio.TimeoutError:
                        return await JSONResponse({'detail': 'Envio da requisição excedeu o tempo permitido.'}, 408)(scope, receive, secure_send)
                    if event['type'] == 'http.disconnect':
                        return
                    body.extend(event.get('body', b''))
                    if len(body) > limit:
                        return await JSONResponse({'detail': 'Requisição acima do limite de tamanho.'}, 413)(scope, receive, secure_send)
                    if not event.get('more_body', False):
                        break
            delivered = False
            async def buffered_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
            try:
                await self.app(scope, buffered_receive, secure_send)
            except Exception:
                if monitor:
                    monitor.response(path, 500)
                raise
        finally:
            self.active -= 1
