"""Small independent browser supervisor. Copied outside replaceable application code."""
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    from update_transaction import apply, restore, read_json, write_json, regular, snapshot_private, restore_private, restore_memory
except ImportError:
    from cronos.update_transaction import apply, restore, read_json, write_json, regular, snapshot_private, restore_private, restore_memory


def status(folder, phase, message, progress, **extra):
    write_json(folder/'status.json', {'phase':phase,'message':message,'progress':progress,**extra})


def open_browser(port,token):
    import webbrowser
    url=f'http://127.0.0.1:{port}/#cronos-session={token}'
    if os.name=='nt':
        # Let Windows open the default browser; launching a browser executable
        # through subprocess can briefly expose a console window.
        os.startfile(url)
        return
    candidates=[shutil.which('brave')]
    for name in ('LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)'):
        if os.getenv(name):candidates.append(str(Path(os.environ[name])/'BraveSoftware/Brave-Browser/Application/brave.exe'))
    brave=next((p for p in candidates if p and Path(p).is_file()),None)
    if brave:subprocess.Popen([brave,'--new-window',url],shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0)
    elif os.name=='nt':os.startfile(url)
    else:webbrowser.open(url)


def ui_command(platform=None, webview_available=None):
    platform = os.name if platform is None else platform
    # The app interface belongs in the user's browser, not a Python WebView.
    return [sys.executable, '-m', 'cronos.browser', '--managed']


def healthy(port, token):
    try:
        request=urllib.request.Request(f'http://127.0.0.1:{port}/updates/health',headers={'Authorization':'Bearer '+token})
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request,timeout=2) as response:
            return json.load(response).get('ready') is True
    except (OSError,ValueError):return False


def maintenance_server(port, token, folder):
    import http.server
    import threading
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.headers.get('Host')!=f'127.0.0.1:{port}':self.send_error(403);return
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://127.0.0.1:{port}':self.send_error(403);return
            if self.path=='/updates':
                if not secrets.compare_digest(self.headers.get('Authorization','').encode('utf-8'),('Bearer '+token).encode('utf-8')):self.send_error(401);return
                body=json.dumps({'state':read_json(folder/'status.json',{}),'managed':True}).encode()
                content='application/json'
            elif self.path=='/':
                body=b'<meta charset="utf-8"><title>Atualizando Cronos</title><p>Atualizacao em andamento. Aguarde alguns segundos e recarregue esta pagina.</p>'
                content='text/html; charset=utf-8'
            else:self.send_error(503);return
            self.send_response(200);self.send_header('Content-Type',content);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',port),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    return server


def close_maintenance(server):
    if server:
        server.shutdown();server.server_close()


def stop(child):
    if child.poll() is None:
        child.terminate()
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)


def _serve(root):
    root=regular(root);folder=regular(root/'.cronos-local/updater');folder.mkdir(parents=True,exist_ok=True)
    # The independent entry point is reused after a failed/half-finished update.
    active=read_json(folder/'active.json')
    if active:
        transaction=regular(folder/'transactions'/active['id'])
        journal=read_json(transaction/'journal.json',{})
        if journal.get('phase') in {'applying','testing','restored'}:
            restore(root,transaction)
            restore_private(root,transaction)
            restore_memory(transaction)
            status(folder,'restored','Versão anterior restaurada após atualização interrompida.',0)
        elif not journal:
            status(folder,'failed','Instalação interrompida antes de alterar o código. Versão anterior preservada.',0,id=active['id'])
        (folder/'active.json').unlink(missing_ok=True)
    interrupted=read_json(folder/'status.json',{})
    if interrupted.get('phase') in {'downloading','validating','generating'} or (interrupted.get('phase')=='queued' and not (folder/'install.request.json').exists()):
        status(folder,'failed','Preparação interrompida. A versão em uso foi preservada.',0,id=interrupted.get('id'))
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];listener.close()
    token=secrets.token_urlsafe(32)
    environment={**os.environ,'CRONOS_SUPERVISED':'1','CRONOS_MANAGED_PORT':str(port),
                 'CRONOS_API_TOKEN':token,'CRONOS_SUPERVISOR_PID':str(os.getpid()),'PYTHONDONTWRITEBYTECODE':'1'}
    data_home=Path(os.environ['CRONOS_DATA_HOME']) if os.getenv('CRONOS_DATA_HOME') else None
    if data_home:
        if read_json(data_home/'DADOS-CRONOS.json',{}).get('complete') is not True:
            raise ValueError('Pasta permanente incompleta; abertura interrompida.')
        # Relative .env/config access works for older browser entry points too.
        environment['PYTHONPATH']=str(root)+os.pathsep+environment.get('PYTHONPATH','')
    (folder/'stop.request').unlink(missing_ok=True)
    initial=True
    def launch():
        nonlocal initial
        environment['CRONOS_OPEN_BROWSER']='1' if initial else '0';initial=False
        log=folder/'server.log'
        if log.exists() and log.stat().st_size>1024*1024:log.replace(folder/'server.previous.log')
        command=ui_command()
        with log.open('ab') as output:
            return subprocess.Popen(command,cwd=data_home or root,env=environment,
                                    stdout=output,stderr=output,creationflags=0x08000000 if os.name=='nt' else 0)
    write_json(folder/'heartbeat.json',{'pid':os.getpid(),'at':time.time()})
    child=launch();heartbeat=0
    try:
        while child.poll() is None:
            time.sleep(.5)
            if time.monotonic()-heartbeat>5:
                write_json(folder/'heartbeat.json',{'pid':os.getpid(),'at':time.time()});heartbeat=time.monotonic()
            if (folder/'stop.request').exists():break
            if (folder/'open.request').exists():
                (folder/'open.request').unlink();open_browser(port,token)
            request=read_json(folder/'install.request.json')
            if not request:continue
            (folder/'install.request.json').unlink()
            ident=request.get('id','')
            if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):continue
            transaction=regular(folder/'transactions'/ident)
            if not (transaction/'prepared.json').is_file():continue
            write_json(folder/'active.json',{'id':ident})
            status(folder,'installing','Encerrando serviços para instalar a atualização.',60,id=ident)
            stop(child)
            maintenance=None
            try:
                maintenance=maintenance_server(port,token,folder)
                snapshot_private(root,transaction)
                apply(root,transaction)
                status(folder,'testing','Verificando a inicialização da nova versão.',85,id=ident)
                close_maintenance(maintenance);maintenance=None
                child=launch();deadline=time.monotonic()+45
                while child.poll() is None and time.monotonic()<deadline:
                    if healthy(port,token):break
                    time.sleep(.5)
                else:raise RuntimeError('A nova versão não passou na verificação de inicialização.')
                # Keep the trial closed to conversations until a short probation succeeds.
                probation=time.monotonic()+5
                while time.monotonic()<probation:
                    if child.poll() is not None or not healthy(port,token):raise RuntimeError('Falha durante verificação da nova versão.')
                    time.sleep(.5)
                journal=read_json(transaction/'journal.json')
                write_json(transaction/'journal.json',{**journal,'phase':'completed'})
                prepared=read_json(transaction/'prepared.json')
                write_json(folder/'installed.json',{'revision':prepared['revision']})
                status(folder,'completed','Atualização instalada. Recarregue a página.',100,id=ident)
            except Exception:
                stop(child)
                close_maintenance(maintenance);maintenance=None
                try:
                    restored=restore(root,transaction)
                    if restored:
                        restore_private(root,transaction)
                        restore_memory(transaction)
                    status(folder,'testing','Conferindo a inicialização da versão anterior.',0,id=ident)
                    child=launch();deadline=time.monotonic()+45
                    while child.poll() is None and time.monotonic()<deadline:
                        if healthy(port,token):break
                        time.sleep(.5)
                    else:raise RuntimeError('A versão anterior não passou na verificação de inicialização.')
                    status(folder,'restored' if restored else 'failed','Atualização não aplicada. Versão anterior preservada/restaurada.',0,id=ident)
                except Exception:
                    status(folder,'recovery_failed','Recuperação não concluída. Backup preservado na pasta local do atualizador.',0,id=ident)
                    raise
            finally:
                close_maintenance(maintenance)
                if read_json(folder/'status.json',{}).get('phase')!='recovery_failed':
                    (folder/'active.json').unlink(missing_ok=True)
    except KeyboardInterrupt:pass
    finally:
        stop(child)
        (folder/'heartbeat.json').unlink(missing_ok=True)
        if (folder/'install.request.json').exists():
            (folder/'install.request.json').unlink()
            status(folder,'failed','Instalação cancelada ao encerrar o supervisor. Código preservado.',0)


def serve(root):
    if os.getenv('CRONOS_DATA_HOME'):
        # One live version per permanent folder; avoid competing voice services
        # and migrations against the same databases across different code roots.
        import importlib.util
        spec=importlib.util.spec_from_file_location('cronos_data_guard',Path(__file__).with_name('persistent_data.py'))
        data=importlib.util.module_from_spec(spec);spec.loader.exec_module(data)
        home=data.validate(os.environ['CRONOS_DATA_HOME'])
        try:
            with data.locked(home/'.launcher/session.lock'):
                data.write_json(home/'.launcher/active-installation.json',{'root':str(root)})
                return serve_installation(root)
        except BlockingIOError:
            active=read_json(home/'.launcher/active-installation.json',{}).get('root')
            if active:
                regular(Path(active)/'.cronos-local/updater/open.request').write_text('open')
            return
    return serve_installation(root)


def serve_installation(root):
    folder=regular(Path(root)/'.cronos-local/updater');folder.mkdir(parents=True,exist_ok=True)
    with (folder/'supervisor.lock').open('a+b') as lock:
        try:
            if os.name=='nt':
                import msvcrt
                lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
                msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            (folder/'open.request').write_text('open');return
        _serve(root)


def main():
    if '--run' in sys.argv:
        serve(Path(sys.argv[-1]));return
    root=Path(__file__).resolve().parents[1]
    from cronos.persistent_data import activate
    activate(root)
    if os.getenv('CRONOS_DATA_HOME'):
        # The current supervisor understands shared data. Do not reuse a cached
        # pre-migration runner which could roll it back on update failure.
        serve(root)
        return
    folder=regular(root/'.cronos-local/updater');folder.mkdir(parents=True,exist_ok=True)
    for name,source in [('runner.py',Path(__file__)),('update_transaction.py',Path(__file__).with_name('update_transaction.py'))]:
        destination=regular(folder/name)
        if not destination.exists():shutil.copy2(source,destination)
    # Run in the bootstrap outside cronos/, which the transaction never replaces.
    os.execv(sys.executable,[sys.executable,str(folder/'runner.py'),'--run',str(root)])


if __name__=='__main__':main()
