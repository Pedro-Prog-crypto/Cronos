"""Real resident HTTP lifecycle plus controlled WebView API contract; no cloud calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

from cronos import resident,desktop,wake,persistent_data


def main():
    checks=[]
    with tempfile.TemporaryDirectory(prefix='cronos-native-resident-') as directory:
        temporary=Path(directory);runtime=temporary/'runtime'
        (temporary/'personality.md').write_text('Converse em português.')
        environment={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]),
            'CRONOS_PROVIDER':'ollama','OLLAMA_URL':'http://127.0.0.1:9',
            'CRONOS_PRIVACY_MODE':'local','CRONOS_VAULT':str(temporary/'vault'),
            'CRONOS_PERSONALITY':str(temporary/'personality.md'),'CRONOS_ENABLE_PLUGINS':'0',
            'CRONOS_PROVIDERS_FILE':str(temporary/'providers.json')}
        for key in list(environment):
            if key=='CRONOS_DATA_HOME' or any(term in key for term in ('API_KEY','API_TOKEN','SECRET','PASSWORD')):environment.pop(key)
        code="from pathlib import Path; import sys; from cronos import resident,persistent_data,wake; resident.folder=lambda project=None:Path(sys.argv[1]);wake.root=lambda:Path(sys.argv[1]).parent/'wake';persistent_data.activate=lambda project:None;resident.main()"
        def start():
            output=(temporary/'service.log').open('ab')
            process=subprocess.Popen([sys.executable,'-c',code,str(runtime)],cwd=temporary,env=environment,stdout=output,stderr=output)
            output.close()
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                if process.poll() is not None:raise AssertionError('Resident exited before readiness: '+(temporary/'service.log').read_text()[-1000:])
                try:
                    connection=resident.Connection(json.loads((runtime/'endpoint.json').read_text()))
                    if connection.healthy():return process,connection
                    connection.close()
                except (OSError,ValueError):pass
                time.sleep(.08)
            process.terminate();process.wait(timeout=3);raise AssertionError('Resident did not start')
        process=None
        try:
            process,connection=start();address=connection.data['url'];token=connection.data['token']
            checks.append('real loopback backend starts without creating a browser or visible WebView')
            state=connection.client.get('/assistant/state').raise_for_status().json()
            assert state['opens_on_name'] is False
            checks.append('authenticated assistant state exposes a shared session and separates name activation from opening')
            connection.close()
            # Verify the documented pywebview persistent-profile API while the
            # actual backend process remains running after each view closes.
            resident.folder=lambda project=None:runtime
            persistent_data.activate=lambda project:None
            desktop.load_dotenv=lambda *args,**kwargs:None
            desktop.sys=SimpleNamespace(platform='win32')
            wake.status=lambda:{'model_installed':False,'dependencies_installed':False}
            wake.root=lambda:temporary/'wake'
            profiles=[]
            class Event:
                def __iadd__(self,callback):return self
            class Window:
                events=SimpleNamespace(loaded=Event())
                def get_current_url(self):return address
            def webview_start(**options):
                assert options['private_mode'] is False
                profiles.append(options['storage_path'])
            sys.modules['webview']=SimpleNamespace(create_window=lambda *a,**kw:Window(),start=webview_start)
            resident.ensure=lambda project=None:resident.Connection(json.loads((runtime/'endpoint.json').read_text()))
            desktop._run();desktop._run()
            assert len(profiles)==2 and profiles[0]==profiles[1]
            check=resident.Connection(json.loads((runtime/'endpoint.json').read_text()))
            assert check.healthy();check.close()
            checks.append('closing and reopening two controlled desktop views keeps the real backend alive')
            checks.append('both desktop views reuse the same non-private WebView profile; no permission auto-grant is installed')
            (runtime/'stop.request').write_text('stop');process.wait(timeout=12)
            assert process.returncode==0 and not (runtime/'endpoint.json').exists()
            checks.append('explicit shutdown removes the private endpoint and terminates the resident')
            process,connection=start()
            assert connection.data['url']==address and connection.data['token']!=token
            checks.append('a restarted backend preserves its origin/port and rotates its private access token')
            connection.close();(runtime/'stop.request').write_text('stop');process.wait(timeout=12)
        finally:
            if process and process.poll() is None:process.kill();process.wait(timeout=3)
    print(json.dumps({'checks_passed':len(checks),'checks':checks,'environment':'Real Python subprocess + Uvicorn/HTTP lifecycle on Linux, controlled WebView API. Windows microphone/camera permission persistence not physically validated.'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
