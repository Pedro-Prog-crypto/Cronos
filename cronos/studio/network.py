"""Small bounded public-page reader. Pins each connection to a validated public IP."""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit


class PublicFetchError(ValueError):
    pass


def public_target(url, *, max_length=2000):
    try:
        p = urlsplit(url)
        if (p.scheme not in {'https', 'http'} or not p.hostname or p.username or p.password
                or p.port not in {None, 80, 443} or len(url) > max_length
                or any(ord(c) < 33 for c in url) or '\\' in url): raise ValueError()
        host = p.hostname.encode('idna').decode('ascii')
        if host.lower() == 'localhost' or host.lower().endswith(('.local', '.localhost', '.internal')): raise ValueError()
        port = p.port or (443 if p.scheme == 'https' else 80)
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        ips = list(dict.fromkeys(row[4][0] for row in addresses))
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips): raise ValueError()
        return p, host, port, ips[0]
    except (ValueError, OSError, UnicodeError):
        raise PublicFetchError('Use um endereço público HTTP(S), sem credenciais ou acesso à rede local.') from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, port):
        super().__init__(host, port=port, timeout=8, context=ssl.create_default_context())
        self.ip = ip

    def connect(self):
        sock = socket.create_connection((self.ip, self.port), timeout=self.timeout)
        try: self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException: sock.close(); raise


def public_fetch(url, *, max_bytes=1_500_000, accept='text/html'):
    deadline = time.monotonic() + 32
    for _ in range(4):
        if time.monotonic() >= deadline: raise PublicFetchError('Tempo total de leitura esgotado.')
        p, host, port, ip = public_target(url)
        conn = PinnedHTTPS(host, ip, port) if p.scheme == 'https' else http.client.HTTPConnection(ip, port, timeout=8)
        try:
            conn.request('GET', (p.path or '/') + ('?' + p.query if p.query else ''), headers={
                'Host': host + (f':{port}' if port not in {80, 443} else ''), 'Accept': accept,
                'User-Agent': 'Cronos-Studio/1.0', 'Accept-Encoding': 'identity'})
            response = conn.getresponse()
            headers = {k.lower(): v for k, v in response.getheaders()}
            if response.status in {301, 302, 303, 307, 308}:
                target = urljoin(url, headers.get('location', ''))
                if target == url: raise PublicFetchError('Redirecionamento sem destino.')
                if p.scheme == 'https' and urlsplit(target).scheme != 'https': raise PublicFetchError('Redirecionamento para conexão sem TLS recusado.')
                url = target
                continue
            if response.status >= 400: return {'url': url, 'status': response.status, 'headers': headers, 'body': b''}
            if headers.get('content-encoding', '').lower() not in {'', 'identity'}:
                raise PublicFetchError('A fonte respondeu com compressão não suportada pelo leitor limitado. Confira diretamente no navegador.')
            chunks = []; size = 0
            while True:
                if time.monotonic() >= deadline: raise PublicFetchError('Tempo total de leitura esgotado.')
                chunk = response.read1(min(65536, max_bytes + 1 - size))
                if not chunk: break
                chunks.append(chunk); size += len(chunk)
                if size > max_bytes: raise PublicFetchError('Resposta acima do limite de leitura do estúdio.')
            raw = b''.join(chunks)
            return {'url': url, 'status': response.status, 'headers': headers, 'body': raw}
        except (OSError, http.client.HTTPException):
            raise PublicFetchError('Não foi possível ler a página pública dentro do prazo; TLS permanece verificado.') from None
        finally: conn.close()
    raise PublicFetchError('A página redirecionou vezes demais.')
