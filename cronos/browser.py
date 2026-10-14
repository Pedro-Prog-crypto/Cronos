"""Interface no navegador, com servidor apenas no computador do usuário."""
import os
import secrets
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv


def main():
    managed_token=os.getenv('CRONOS_API_TOKEN','')
    managed_environment={key:os.environ[key] for key in ('CRONOS_SUPERVISED','CRONOS_SUPERVISOR_PID','CRONOS_MANAGED_PORT','CRONOS_OPEN_BROWSER') if key in os.environ}
    load_dotenv('.env', override=True)
    if '--managed' in __import__('sys').argv and managed_environment.get('CRONOS_SUPERVISED')=='1':os.environ.update(managed_environment)
    managed='--managed' in __import__('sys').argv and os.getenv('CRONOS_SUPERVISED')=='1'
    if managed:os.environ['CRONOS_API_TOKEN']=managed_token
    else:os.environ['CRONOS_API_TOKEN'] = secrets.token_urlsafe(32)
    from cronos.app import create_app
    from cronos.config import Settings
    import uvicorn

    settings = Settings.from_env()
    server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level='warning', access_log=False))
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    listener.bind(('127.0.0.1', int(os.getenv('CRONOS_MANAGED_PORT','0')) if managed else 0))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError('O servidor não iniciou. Confira a instalação e o .env.')
            time.sleep(.05)
        url = f'http://127.0.0.1:{listener.getsockname()[1]}/#cronos-session={settings.token}'
        candidates = [shutil.which('brave')]
        for name in ('LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)'):
            root = os.environ.get(name)
            if root:
                candidates.append(str(Path(root) / 'BraveSoftware/Brave-Browser/Application/brave.exe'))
        brave = next((path for path in candidates if path and Path(path).is_file()), None)
        if managed and os.getenv('CRONOS_OPEN_BROWSER')=='0':
            pass
        elif brave:
            subprocess.Popen([brave, '--new-window', url])
        else:
            webbrowser.open(url)
        # A janela de controle mantém o servidor vivo; Ctrl+C encerra os serviços.
        while thread.is_alive():
            thread.join(timeout=.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()


if __name__ == '__main__':
    main()
