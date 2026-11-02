"""Version-independent connection to the Brain Cloud v1 HTTP contract.

The pairing file is private user data, stored inside the persistent vault.
Neither the Brain source tree nor its release name is an input to this client.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from cronos.providers import ProviderError


class BrainCloud:
    def __init__(self, vault: Path, config_path: Path | None = None):
        self.path = config_path or vault / '.cronos' / 'brain-cloud.json'
        self.sessions_path = vault / '.cronos' / 'brain-sessions.json'
        self._fingerprint = None
        self._token = ''
        self._expires_at = 0.0
        self._sessions: dict[str, str] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def validate(config: object) -> dict[str, str]:
        if not isinstance(config, dict) or not all(isinstance(config.get(k), str) for k in ('baseUrl', 'deviceId', 'credential')):
            raise ValueError('Arquivo de conexão do Brain Cloud incompleto.')
        url = urlsplit(config['baseUrl'])
        local = url.hostname in {'localhost', '127.0.0.1'}
        if url.scheme != 'https' and not (url.scheme == 'http' and local):
            raise ValueError('Brain Cloud exige HTTPS ou servidor local em localhost.')
        if not url.hostname or url.username or url.password or url.path not in {'', '/'} or url.query or url.fragment:
            raise ValueError('O endereço do Brain Cloud deve conter somente a origem da API.')
        if not re.fullmatch(r'[0-9a-fA-F-]{36}', config['deviceId']):
            raise ValueError('Identificador de dispositivo inválido.')
        try:
            UUID(config['deviceId'])
        except ValueError:
            raise ValueError('Identificador de dispositivo inválido.') from None
        if not re.fullmatch(r'[a-fA-F0-9]{64}', config['credential']):
            raise ValueError('Credencial do dispositivo inválida.')
        return {k: config[k] for k in ('baseUrl', 'deviceId', 'credential')}

    def configured(self) -> bool:
        return self.path.is_file()

    def _read(self) -> dict[str, str]:
        try:
            data = self.validate(json.loads(self.path.read_text(encoding='utf-8')))
        except (OSError, ValueError) as exc:
            raise ProviderError('Conexão Brain Cloud inválida; confira o arquivo de pareamento.', 503, kind='brain_configuration') from exc
        fingerprint = (data['baseUrl'], data['deviceId'], data['credential'])
        if fingerprint != self._fingerprint:
            self._fingerprint = fingerprint
            self._token = ''
            self._expires_at = 0
            self.sessions_path = self.sessions_path.parent / ('brain-sessions-' + data['deviceId'] + '.json')
            self._sessions = self._load_sessions()
        return data

    def _load_sessions(self) -> dict[str, str]:
        try:
            data = json.loads(self.sessions_path.read_text(encoding='utf-8'))
            return {str(UUID(k)): str(UUID(v)) for k, v in data.items()} if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_sessions(self) -> None:
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.sessions_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self._sessions), encoding='utf-8')
        os.replace(temporary, self.sessions_path)

    async def _authenticate(self, client: httpx.AsyncClient, config: dict[str, str]) -> str:
        if self._token and time.monotonic() < self._expires_at:
            return self._token
        response = await client.post('/v1/auth/sessions', json={'deviceId': config['deviceId'], 'credential': config['credential']})
        if response.status_code != 201:
            raise ProviderError('Brain Cloud recusou a credencial do dispositivo.', response.status_code, kind='brain_auth')
        data = response.json()
        token = data.get('accessToken')
        if not isinstance(token, str) or not token:
            raise ProviderError('Brain Cloud não devolveu uma sessão válida.', 502, kind='brain_contract')
        self._token = token
        self._expires_at = time.monotonic() + max(1, min(720, int(data.get('expiresIn', 900)) - 90))
        return token

    async def chat(self, session: UUID, message: str) -> dict:
        # The Brain's request schema accepts at most 8000 characters.
        if not message.strip() or len(message) > 8000:
            raise ValueError('A pergunta ultrapassa o limite atual do Brain Cloud.')
        async with self._lock:
            config = self._read()
            try:
                local = urlsplit(config['baseUrl']).hostname in {'localhost', '127.0.0.1'}
                async with httpx.AsyncClient(base_url=config['baseUrl'], follow_redirects=False,
                                             trust_env=not local, timeout=httpx.Timeout(75.0, connect=8.0)) as client:
                    token = await self._authenticate(client, config)
                    body = {'message': message, 'remember': True}
                    previous = self._sessions.get(str(session))
                    if previous:
                        body['conversationId'] = previous
                    response = await client.post('/v1/chat', json=body, headers={'Authorization': 'Bearer ' + token})
                    if response.status_code == 401:
                        self._token = ''
                        token = await self._authenticate(client, config)
                        response = await client.post('/v1/chat', json=body, headers={'Authorization': 'Bearer ' + token})
                    if response.is_redirect:
                        raise ProviderError('Brain Cloud redirecionou a conversa.', 502, kind='brain_redirect')
                    if response.status_code != 200:
                        code = ''
                        try: code = str(response.json().get('error', {}).get('code', ''))[:80]
                        except (ValueError, AttributeError, TypeError): pass
                        raise ProviderError('Brain Cloud não concluiu a resposta' + (f' ({code}).' if code else '.'),
                                            response.status_code, kind='brain_response')
                    result = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                if isinstance(exc, ProviderError): raise
                raise ProviderError('Brain Cloud está indisponível nesta tentativa.', 503, kind='brain_transport') from exc
            if not isinstance(result, dict) or result.get('status') != 'completed' or not isinstance(result.get('text'), str) or not result['text'].strip():
                raise ProviderError('Brain Cloud devolveu uma resposta incompleta.', 502, kind='brain_contract')
            try:
                remote_id = str(UUID(result['conversationId']))
            except (KeyError, ValueError, TypeError):
                raise ProviderError('Brain Cloud não informou uma conversa válida.', 502, kind='brain_contract') from None
            self._sessions[str(session)] = remote_id
            try: self._save_sessions()
            except OSError: pass  # The answer is valid even if this local continuity index cannot be written.
            return result

    async def heartbeat(self) -> bool:
        """Tell the Brain that the desktop is present without running commands."""
        if not self.configured() or self._lock.locked(): return False
        async with self._lock:
            config = self._read()
            local = urlsplit(config['baseUrl']).hostname in {'localhost', '127.0.0.1'}
            async with httpx.AsyncClient(base_url=config['baseUrl'], follow_redirects=False,
                                         trust_env=not local, timeout=httpx.Timeout(10, connect=5)) as client:
                token = await self._authenticate(client, config)
                response = await client.post('/v1/devices/heartbeat',
                                             json={'client':'CRONOS Desktop'},
                                             headers={'Authorization':'Bearer '+token})
                if response.status_code == 401:
                    self._token = ''
                    token = await self._authenticate(client, config)
                    response = await client.post('/v1/devices/heartbeat',
                                                 json={'client':'CRONOS Desktop'},
                                                 headers={'Authorization':'Bearer '+token})
                return response.status_code == 200 and response.json().get('connected') is True


def local_action(message: str) -> bool:
    """Keep device/application operations in the desktop, whose tools can perform them."""
    from cronos.study_intent import normalize
    value = normalize(message).strip()
    value = re.sub(r'^(?:ei\s+)?(?:cronos|kronos|chronos)[,\s:]*', '', value)
    return bool(re.match(
        r'^(?:abre|abrir|abra|feche|fecha|fechar|pause|pausa|pare|parar|continue|continuar|'
        r'toque|toca|tocar|reproduza|reproduzir|coloque|coloca|envie|enviar|crie|criar|'
        r'pesquise|pesquisar|busque|buscar|veja|ver|mostre|mostrar|leia|ler|'
        r'clique|clicar|digite|digitar|mova|mover|salve|salvar|agende|agendar|'
        r'fa[cç]a|fazer)\b', value
    ))
