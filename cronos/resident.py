"""Private loopback backend, independent of the visible desktop window."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit

import httpx

VERSION = 12


def folder(project=None):
    project = Path(project or Path(__file__).resolve().parents[1])
    return Path(os.getenv('CRONOS_DATA_HOME') or project) / '.cronos-local' / 'assistant'


def revision(project):
    try:return json.loads((Path(project)/'tools/interface_update_manifest.json').read_text())['revision']
    except (OSError, ValueError, KeyError):return 'development'


def active_file():
    from cronos.wake import root
    return root()/'active-backend.json'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(4) + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        temporary.chmod(0o600)
        for attempt in range(4):
            try:temporary.replace(path);break
            except PermissionError:
                if attempt==3:raise
                time.sleep(.025)
    finally:temporary.unlink(missing_ok=True)


class Connection:
    def __init__(self, data, client=None):
        parsed = urlsplit(data.get('url', ''))
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or parsed.path or parsed.query or parsed.fragment or parsed.username is not None:
            raise ValueError('Endereço do assistente local inválido.')
        token = data.get('token', '')
        if not isinstance(token, str) or not 20 <= len(token) <= 256:raise ValueError('Credencial local indisponível.')
        self.data = data
        self.client = client or httpx.Client(base_url=data['url'], headers={'Authorization': 'Bearer ' + token},
                                             timeout=httpx.Timeout(45, connect=3), trust_env=False, follow_redirects=False)

    def healthy(self):
        try:
            response = self.client.get('/status', timeout=2)
            return response.status_code == 200 and isinstance(response.json().get('provider'), str)
        except (httpx.HTTPError, ValueError):return False

    def close(self):self.client.close()


def discover(project=None):
    try:return Connection(json.loads((folder(project) / 'endpoint.json').read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError):return None


def ensure(project=None, timeout=35):
    project = Path(project or Path(__file__).resolve().parents[1]).resolve()
    current = discover(project)
    if current:
        healthy = current.healthy()
        compatible = current.data.get('version') == VERSION and current.data.get('installation') == str(project) and current.data.get('revision') == revision(project)
        if healthy and compatible:return current
        current.close()
        if healthy:
            request_stop(project)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                old = discover(project)
                if not old:break
                running = old.healthy();old.close()
                if not running:break
                time.sleep(.15)
            else:raise RuntimeError('A versão anterior ainda está encerrando. Os dados foram preservados; tente abrir novamente.')
    # A previous installation can keep serving after its window closed. Hand
    # it off before a new folder starts another backend and consumes more RAM.
    try:
        previous=Connection(json.loads(active_file().read_text()))
        try:
            if previous.healthy():
                previous.client.post('/assistant/shutdown',json={},timeout=3).raise_for_status()
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    if not previous.healthy():break
                    time.sleep(.1)
                else:raise RuntimeError('A instalação anterior ainda está encerrando. Tente novamente em alguns segundos.')
        finally:previous.close()
    except (OSError,ValueError):pass
    from cronos.wake import independent_environment, python_windowless
    subprocess.Popen([str(python_windowless()), '-m', 'cronos.resident'], cwd=project, env=independent_environment(),
                     shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = discover(project)
        if current:
            if current.data.get('version') == VERSION and current.data.get('installation') == str(project) and current.data.get('revision') == revision(project) and current.healthy():return current
            current.close()
        time.sleep(.15)
    raise RuntimeError('O serviço local não iniciou. Confira a instalação; nenhuma janela foi aberta automaticamente.')


def request_stop(project=None):
    path = folder(project) / 'stop.request'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('stop', encoding='utf-8')


def stop_active():
    """Explicit user shutdown, including a resident from an older code folder."""
    try:
        connection=Connection(json.loads(active_file().read_text()))
        try:
            return connection.client.post('/assistant/shutdown',json={},timeout=3).raise_for_status().json()
        finally:connection.close()
    except (OSError,ValueError,httpx.HTTPError):
        request_stop();return {'requested':True}


def main():
    from dotenv import load_dotenv
    from cronos.persistent_data import activate
    from cronos.wake import single_instance
    project = Path(__file__).resolve().parents[1]
    activate(project)
    load_dotenv('.env', override=True)
    directory = folder(project);directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    identity = __import__('hashlib').sha256(str(directory.resolve()).encode()).hexdigest()[:20]
    with single_instance('CronosResident-' + identity) as acquired:
        if not acquired:return
        from cronos.app import create_app
        from cronos.config import Settings
        from cronos.desktop_state import session_id
        import uvicorn
        session_id()
        os.environ['CRONOS_API_TOKEN'] = secrets.token_urlsafe(32)
        settings = Settings.from_env()
        try:
            preferred = int(json.loads((directory / 'port.json').read_text()).get('port', 0))
            if not 1024 <= preferred <= 65535:preferred = 0
        except (OSError, ValueError, TypeError):preferred = 0
        listener = socket.socket();listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:listener.bind(('127.0.0.1', preferred))
        except OSError:listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1];write_json(directory / 'port.json', {'port': port})
        stop = directory / 'stop.request';stop.unlink(missing_ok=True)
        app=create_app(settings)
        app.state.resident_shutdown=lambda:request_stop(project)
        server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False,timeout_graceful_shutdown=10))
        data = {'url': f'http://127.0.0.1:{port}', 'token': settings.token, 'pid': os.getpid(),
                'installation': str(project), 'version': VERSION, 'revision': revision(project)}
        def supervise():
            while not server.should_exit:
                if server.started:
                    try:write_json(directory / 'endpoint.json', data)
                    except OSError:server.should_exit=True;return
                    try:write_json(active_file(),data)
                    except OSError:pass
                    break
                time.sleep(.1)
            while not server.should_exit:
                if stop.exists():server.should_exit = True;break
                time.sleep(.3)
        thread = threading.Thread(target=supervise, daemon=True);thread.start()
        try:server.run(sockets=[listener])
        finally:
            server.should_exit = True;thread.join(timeout=2);listener.close()
            try:
                path = directory / 'endpoint.json'
                if json.loads(path.read_text()).get('pid') == os.getpid():path.unlink(missing_ok=True)
            except (OSError, ValueError):pass
            try:
                path=active_file()
                if json.loads(path.read_text()).get('pid')==os.getpid():path.unlink(missing_ok=True)
            except (OSError,ValueError):pass


if __name__ == '__main__':main()
