"""Runtime exportável, somente biblioteca padrão. Nunca executa código do modelo."""
import argparse
import json
import re
import secrets
import sqlite3
import time
from datetime import date, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


class FormError(ValueError):
    pass


def validated(kind, data):
    if kind not in {'contact', 'booking'} or not isinstance(data, dict):
        raise FormError('Formulário inválido.')
    allowed = {'name', 'email', 'phone', 'message', 'date', 'time', 'service', 'consent', 'company'}
    if set(data) - allowed:
        raise FormError('Campo inesperado.')
    if data.get('company'):
        raise FormError('Envio recusado.')
    if data.get('consent') is not True:
        raise FormError('Confirme o consentimento para usar seus dados no atendimento.')
    result = {}
    for key, limit in {'name': 100, 'email': 180, 'phone': 32, 'message': 3000, 'service': 120, 'date': 10, 'time': 5}.items():
        value = data.get(key, '')
        if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
            raise FormError('Campo inválido ou acima do limite: ' + key)
        result[key] = value.strip()
    if len(result['name']) < 2:
        raise FormError('Informe seu nome.')
    if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', result['email']):
        raise FormError('Informe um e-mail válido.')
    if result['phone'] and not re.fullmatch(r'[+()\d .-]{7,32}', result['phone']):
        raise FormError('Telefone inválido.')
    if kind == 'booking':
        try:
            day = date.fromisoformat(result['date'])
            datetime.strptime(result['time'], '%H:%M')
            if len(result['time']) != 5 or day < date.today(): raise ValueError()
        except ValueError:
            raise FormError('Escolha uma data futura e um horário válido.') from None
        if not result['service']: raise FormError('Informe o serviço.')
    elif not result['message']:
        raise FormError('Escreva uma mensagem.')
    return result


def connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS slots(day TEXT,hour TEXT,submission TEXT NOT NULL,PRIMARY KEY(day,hour))')
    return db


def submit(path, kind, data):
    value = validated(kind, data)
    identifier = secrets.token_hex(12)
    try:
        with connect(path) as db:
            if kind == 'booking':
                db.execute('INSERT INTO slots VALUES(?,?,?)', (value['date'], value['time'], identifier))
            db.execute('INSERT INTO submissions VALUES(?,?,?,?)', (identifier, kind, json.dumps(value, ensure_ascii=False), time.time()))
    except sqlite3.IntegrityError:
        raise FormError('Esse horário já foi solicitado. Escolha outro.') from None
    return {'ok': True, 'id': identifier, 'message': 'Solicitação registrada. O atendimento deve confirmar a disponibilidade.'}


# Included unchanged in each export. No read/list/admin endpoint is public.
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server, directory=str(server.site_root))

    def log_message(self, *args):
        pass  # No personal contact data or tokens in console logs.

    def end_headers(self):
        for key, value in {
            'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
            'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' blob:; media-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            'Permissions-Policy': 'camera=(), microphone=(), geolocation=()', 'X-Frame-Options': 'DENY',
        }.items(): super().send_header(key, value)
        super().end_headers()

    def respond(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers(); self.wfile.write(payload)

    def allowed_host(self):
        try:
            parsed = urlsplit('http://' + self.headers.get('Host', ''))
            return parsed.hostname in self.server.hostnames and not parsed.username and parsed.port == self.server.server_port
        except ValueError: return False

    def do_GET(self):
        if not self.allowed_host(): return self.respond(403, {'error': 'Host não autorizado.'})
        path = urlsplit(self.path).path
        if path == '/api/session':
            origin = self.headers.get('Origin')
            if (origin and origin != 'http://' + self.headers.get('Host')) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.respond(403, {'error': 'Origem não autorizada.'})
            token = self.server.csrf
            return self.respond(200, {'csrf': token})
        if not re.fullmatch(r'/(?:index\.html|styles\.css|app\.js|studio-runtime\.js|assets/[a-f0-9]{32}\.(?:jpg|png|glb)|product-3d\.js|procedural-3d\.js)?', path):
            return self.respond(404, {'error': 'Arquivo não encontrado.'})
        if path == '/': self.path = '/index.html'
        super().do_GET()

    def do_HEAD(self):
        if not self.allowed_host(): return self.respond(403, {'error': 'Host não autorizado.'})
        if not re.fullmatch(r'/(?:index\.html|styles\.css|app\.js|studio-runtime\.js|assets/[a-f0-9]{32}\.(?:jpg|png|glb)|product-3d\.js|procedural-3d\.js)?', urlsplit(self.path).path):
            return self.respond(404, {'error': 'Arquivo não encontrado.'})
        super().do_HEAD()

    def do_POST(self):
        if not self.allowed_host(): return self.respond(403, {'error': 'Host não autorizado.'})
        expected = 'http://' + self.headers.get('Host', '')
        if self.headers.get('Origin') != expected or not secrets.compare_digest(self.headers.get('X-Studio-CSRF', ''), self.server.csrf):
            return self.respond(403, {'error': 'Origem ou sessão inválida.'})
        kind = {'/api/contact': 'contact', '/api/booking': 'booking'}.get(urlsplit(self.path).path)
        if not kind: return self.respond(404, {'error': 'Formulário não encontrado.'})
        now = time.monotonic(); key = self.client_address[0]
        with self.server.rate_lock:
            # Bound storage as well as requests. This server is for local evaluation;
            # production rate limiting belongs at a configured reverse proxy too.
            recent = [t for t in self.server.rates.get(key, []) if now - t < 60]
            if len(recent) >= 10: return self.respond(429, {'error': 'Aguarde antes de enviar novamente.'})
            self.server.rates[key] = [*recent, now]
            if len(self.server.rates) > 1000:
                self.server.rates = {k: v for k, v in self.server.rates.items() if now - v[-1] < 60}
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond(413, {'error': 'Envio inválido ou grande demais.'})
            self.connection.settimeout(5)
            data = json.loads(self.rfile.read(length))
            return self.respond(201, submit(self.server.database, kind, data))
        except (ValueError, OSError): return self.respond(422, {'error': 'Dados inválidos. Confira nome, e-mail, consentimento e horário disponível.'})


def run():
    import threading
    parser = argparse.ArgumentParser(description='Prévia local do site exportado; produção exige hospedagem configurada e HTTPS.')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.site_root = root / 'site'
    server.database = root / 'private' / 'contacts.sqlite3'
    server.database.parent.mkdir(exist_ok=True)
    server.csrf = secrets.token_urlsafe(32)
    server.hostnames = {'localhost', '127.0.0.1'}
    server.rates = {}; server.rate_lock = threading.Lock()
    print(f'Site local: http://127.0.0.1:{server.server_port} — Ctrl+C para encerrar.')
    server.serve_forever()


if __name__ == '__main__': run()
