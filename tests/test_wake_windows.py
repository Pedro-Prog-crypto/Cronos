import asyncio
import hashlib
import io
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import httpx
import pytest

from cronos import wake, windows_system


def result(text,confidence=.9):
    return {'text':text,'result':[{'word':word,'conf':confidence} for word in text.split()]}


def test_voice_trigger_exact_phrase_confidence_and_cooldown():
    trigger=wake.Trigger({'activation_phrase':'abrir cronos','pause_phrase':'pausar cronos','resume_phrase':'retomar cronos'})
    for text in ('abrir chrome','abrir cronos e apagar arquivos','executar powershell','[unk]',''):
        assert not trigger.accept(result(text),now=100)
    assert not trigger.accept(result('abrir cronos',.49),now=100)
    assert not trigger.accept({'text':'abrir cronos'},now=100)
    assert trigger.accept(result('Abrir Cronos'),now=100)
    assert not trigger.accept(result('cronos abrir'),now=110)
    assert trigger.accept(result('Abrir Cronos'),now=121)
    assert not trigger.accept(result('abrir kronos'),now=130)
    assert trigger.accept(result('Abrir Cronos'),now=142)


def test_wake_phrases_are_user_configurable_and_persisted(tmp_path,monkeypatch):
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    saved=wake.save_settings({'activation_phrase':'Pastel azul','pause_phrase':'silêncio agora','resume_phrase':'voltar ao trabalho','start_with_windows':False})
    assert saved['activation_phrase']=='Pastel azul'
    assert wake.settings()['resume_phrase']=='voltar ao trabalho'
    trigger=wake.Trigger(saved)
    assert trigger.action(result('Pastel azul'),now=100)=='activate'
    assert trigger.action(result('silêncio agora'),now=101)=='paused'
    assert wake.paused()
    assert trigger.action(result('Pastel azul'),now=110) is None
    assert trigger.action(result('voltar ao trabalho'),now=103)=='resumed'
    assert not wake.paused()


def test_default_voice_commands_accept_spoken_variants_and_report_recognition(tmp_path,monkeypatch):
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    trigger=wake.Trigger(wake.DEFAULT_SETTINGS)
    phrases=wake.command_phrases(wake.DEFAULT_SETTINGS)
    assert phrases['cromos']=='activate'
    assert phrases['abrir cromos']=='activate'
    assert phrases['pausar cromos']=='paused'
    assert phrases['retomar cromos']=='resumed'
    assert trigger.action(result('cromos'),now=90)=='activate'
    trigger=wake.Trigger(wake.DEFAULT_SETTINGS)
    assert trigger.action(result('pausar cronos'),now=100)=='paused'
    assert trigger.last_action=='paused' and trigger.last_heard=='pausar cronos'
    assert trigger.action(result('cronos'),now=101) is None
    assert trigger.last_action=='ignored_while_paused'
    assert trigger.action(result('abrir cronos'),now=102) is None
    assert trigger.action(result('retomar cronos'),now=103)=='resumed'
    assert trigger.action(result('abrir cronos'),now=104)=='activate'


def test_desktop_voice_activation_prefers_the_cronos_window(monkeypatch):
    monkeypatch.setattr(wake.importlib.util,'find_spec',lambda name:object() if name=='webview' else None)
    assert wake.app_launch_module()=='cronos.desktop'
    monkeypatch.setattr(wake.importlib.util,'find_spec',lambda name:None)
    assert wake.app_launch_module()=='cronos.browser'


def test_custom_activation_has_open_alias_and_preserves_exact_phrase_priority():
    config={'activation_phrase':'pastel azul','pause_phrase':'pausar cronos','resume_phrase':'retomar cronos'}
    commands=wake.command_phrases(config)
    assert commands['pastel azul']=='activate'
    assert commands['abrir pastel azul']=='activate'
    assert commands['pausar cronos']=='paused'


@pytest.mark.parametrize('values',[
    {'activation_phrase':'pastel','pause_phrase':'pastel','resume_phrase':'retomar'},
    {'activation_phrase':'','pause_phrase':'pausar','resume_phrase':'retomar'},
    {'activation_phrase':'x '*11,'pause_phrase':'pausar','resume_phrase':'retomar'},
])
def test_wake_phrase_validation_rejects_empty_duplicate_or_excessive_phrases(values):
    with pytest.raises(ValueError):wake.validate_settings(values)


def package(extra=None):
    stream=io.BytesIO()
    with ZipFile(stream,'w') as archive:
        archive.writestr(wake.MODEL_NAME+'/am/final.mdl',b'test model data')
        archive.writestr(wake.MODEL_NAME+'/conf/model.conf',b'test configuration')
        if extra: archive.writestr(extra,b'unexpected')
    return stream.getvalue()


def test_model_download_fixed_https_hashes_and_no_repeated_download(tmp_path,monkeypatch):
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    captured=[];original=httpx.Client
    def handler(request):
        captured.append(str(request.url));return httpx.Response(200,content=package())
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    output=wake.prepare_model()
    assert output['installed'] and output['downloaded']
    assert captured==[wake.MODEL_URL]
    assert output['archive_sha256']==hashlib.sha256(package()).hexdigest()
    assert wake.verify_model()==tmp_path/wake.MODEL_NAME
    assert not wake.prepare_model()['downloaded']
    assert len(captured)==1
    (tmp_path/wake.MODEL_NAME/'am/final.mdl').write_bytes(b'changed')
    with pytest.raises(ValueError,match='alterado'): wake.verify_model()


@pytest.mark.parametrize('extra',['../escape.txt',wake.MODEL_NAME+'/danger.exe'])
def test_download_rejects_traversal_and_executables(tmp_path,monkeypatch,extra):
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    original=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=package(extra))),**kwargs))
    with pytest.raises(ValueError):wake.prepare_model()
    assert not (tmp_path/wake.MODEL_NAME).exists()


def test_voice_launch_starts_only_fixed_desktop_command(tmp_path,monkeypatch):
    calls=[];monkeypatch.setattr(wake,'root',lambda:tmp_path)
    monkeypatch.setattr(wake,'sys',SimpleNamespace(platform='win32',executable=str(tmp_path/'python.exe')))
    monkeypatch.setattr(wake,'verify_model',lambda:tmp_path)
    monkeypatch.setattr(wake,'status',lambda:{'dependencies_installed':True})
    monkeypatch.setattr(wake.subprocess,'Popen',lambda argv,**kwargs:calls.append((argv,kwargs)))
    assert wake.start()['requested']
    assert calls[0][0]==[str(tmp_path/'python.exe'),'-m','cronos.wake']
    assert calls[0][1]['shell'] is False
    assert wake.stop()['requested']
    assert (tmp_path/'stop.request').is_file()


def test_windows_runner_uses_constant_commands_and_no_shell(monkeypatch):
    monkeypatch.setattr(windows_system,'sys',SimpleNamespace(platform='win32'))
    def directory(buffer,count):buffer.value='C:/Windows';return 10
    monkeypatch.setattr(windows_system.ctypes,'windll',SimpleNamespace(kernel32=SimpleNamespace(GetWindowsDirectoryW=directory)),raising=False)
    monkeypatch.setattr(windows_system.subprocess,'CREATE_NO_WINDOW',0,raising=False)
    calls=[]
    class Process:
        returncode=0
        def __init__(self,argv,**kwargs):self.args=argv;calls.append((argv,kwargs))
        def communicate(self,**kwargs):return ('{"completed":true}','')
        def poll(self):return 0
    monkeypatch.setattr(windows_system.subprocess,'Popen',Process)
    assert windows_system.powershell('update_signatures')['completed']
    assert calls[0][1]['shell'] is False
    assert '-ExecutionPolicy' not in calls[0][0]
    assert 'Update-MpSignature' in calls[0][0][-1]
    with pytest.raises(ValueError):windows_system.powershell('arbitrary shell')
    assert len(calls)==1


def test_job_failure_and_local_privacy_download_block(monkeypatch):
    def failure(*args):raise windows_system.WindowsError('PRIVATE_ERROR')
    async def scenario():
        service=windows_system.WindowsSystem(failure,platform='win32',privacy_mode='local')
        with pytest.raises(ValueError,match='bloqueado'):await service.action('prepare_voice')
        job=await service.action('quick_scan')
        await asyncio.gather(*service.tasks)
        assert service.jobs[job['id']]['status']=='failed'
        assert 'PRIVATE_ERROR' not in json.dumps(service.jobs)
        with pytest.raises(ValueError):await service.action('disable_firewall')
        await service.close()
    asyncio.run(scenario())


def test_status_expires_and_does_not_store_audio(tmp_path,monkeypatch):
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    monkeypatch.setattr(wake.time,'time',lambda:100)
    wake._write_status('listening')
    assert wake.status()['state']=='listening'
    monkeypatch.setattr(wake.time,'time',lambda:121)
    assert wake.status()['state']=='stopped'
    assert set(json.loads((tmp_path/'status.json').read_text()))=={'state','heartbeat','last_opened','worker_version','installation'}


def test_status_heartbeat_keeps_last_recognition_without_recording_audio(tmp_path,monkeypatch):
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    wake._write_status('listening',last_heard='pausar cronos',last_action='paused',
                       last_confidence=.92,greeting_status='windows_voice')
    wake._write_status('listening')
    result=wake.status()
    assert result['last_heard']=='pausar cronos'
    assert result['last_action']=='paused'
    assert result['last_confidence']==.92
    assert result['greeting_status']=='windows_voice'


def test_child_launch_drops_server_ownership_but_keeps_personal_data(monkeypatch):
    for key in ('CRONOS_SUPERVISED','CRONOS_SUPERVISOR_PID','CRONOS_MANAGED_PORT','CRONOS_API_TOKEN','CRONOS_OPEN_BROWSER'):
        monkeypatch.setenv(key, 'parent-session')
    monkeypatch.setenv('CRONOS_DATA_HOME', '/personal/data')
    inherited = wake.independent_environment()
    assert inherited['CRONOS_DATA_HOME'] == '/personal/data'
    assert 'CRONOS_MANAGED_PORT' not in inherited and 'CRONOS_API_TOKEN' not in inherited
    assert 'CRONOS_SUPERVISED' not in inherited and 'CRONOS_SUPERVISOR_PID' not in inherited
    assert 'CRONOS_OPEN_BROWSER' not in inherited
    assert wake.os.environ['CRONOS_API_TOKEN'] == 'parent-session'


def test_current_worker_in_an_old_installation_is_replaced(tmp_path, monkeypatch):
    monkeypatch.setattr(wake, 'sys', SimpleNamespace(platform='win32', executable=str(tmp_path/'python.exe')))
    monkeypatch.setattr(wake, 'root', lambda: tmp_path)
    monkeypatch.setattr(wake, 'verify_model', lambda: tmp_path)
    statuses = iter([{'state':'listening', 'worker_version':wake.WAKE_VERSION, 'installation':'old', 'dependencies_installed':True}, {'state':'stopped'}])
    monkeypatch.setattr(wake, 'status', lambda: next(statuses))
    calls=[]
    monkeypatch.setattr(wake.subprocess, 'Popen', lambda *args, **kwargs: calls.append(kwargs))
    assert wake.start()['requested']
    assert (tmp_path/'stop.request').exists() and len(calls)==1


@pytest.mark.parametrize("conversation_active",[False,True])
def test_listener_keeps_recognizing_while_the_voice_service_is_slow(tmp_path, monkeypatch,conversation_active):
    from contextlib import nullcontext
    started, release = threading.Event(), threading.Event()
    history=[]; original=wake._write_status
    def write(state, *args, **kwargs):
        history.append(kwargs)
        original(state, *args, **kwargs)
        if kwargs.get('last_action')=='paused':
            assert not release.is_set(), 'Voice network wait blocked the microphone loop'
            (tmp_path/'stop.request').write_text('stop')
    monkeypatch.setattr(wake, '_write_status', write)
    monkeypatch.setattr(wake, 'root', lambda: tmp_path)
    monkeypatch.setattr(wake, 'sys', SimpleNamespace(platform='win32',executable='python.exe'))
    monkeypatch.setattr(wake, 'verify_model', lambda: tmp_path)
    monkeypatch.setattr(wake, 'single_instance', lambda name: nullcontext(True))
    if conversation_active:wake.set_ui_listening(True)
    monkeypatch.setattr(wake, 'app_launch_module', lambda: 'cronos.desktop')
    monkeypatch.setattr(wake.subprocess,'Popen',lambda *args,**kwargs:SimpleNamespace(poll=lambda:None))
    def greeting(speaking):
        started.set(); release.wait(3); return 'cronos_voice'
    monkeypatch.setattr(wake, 'speak_activation_greeting', greeting)
    class Recognizer:
        def __init__(self,*args): self.step=0
        def SetWords(self,value): pass
        def AcceptWaveform(self,frame):
            self.step+=1
            if self.step==2 and not conversation_active: assert started.wait(1)
            return True
        def Result(self): return json.dumps(result('abrir cromos' if self.step==1 else 'pausar cromos'))
    class Stream:
        def __init__(self,**kwargs): self.callback=kwargs['callback']; assert kwargs['blocksize']==1600
        def __enter__(self):
            self.callback(b'audio',1600,None,None); self.callback(b'audio',1600,None,None); return self
        def __exit__(self,*args): pass
    monkeypatch.setitem(sys.modules,'vosk',SimpleNamespace(KaldiRecognizer=Recognizer,Model=lambda path:None,SetLogLevel=lambda n:None))
    monkeypatch.setitem(sys.modules,'sounddevice',SimpleNamespace(RawInputStream=Stream))
    try: wake.listen()
    finally: release.set()
    assert any(item.get('last_action')=='activate' for item in history)
    assert any(item.get('last_action')=='paused' for item in history)
    assert started.is_set() is (not conversation_active)


def test_wake_uses_saved_fish_voice_and_repairs_streaming_wav(tmp_path,monkeypatch):
    import wave
    from cronos.config import Settings
    import cronos.fish_legacy as legacy
    stream=io.BytesIO()
    with wave.open(stream,'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(b'\x00\x00'*80)
    raw=bytearray(stream.getvalue());raw[4:8]=b'\xff'*4;raw[40:44]=b'\xff'*4
    monkeypatch.setenv('CRONOS_DATA_HOME', str(tmp_path))
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    monkeypatch.setattr(wake,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(Settings,'from_env',lambda:SimpleNamespace(privacy_mode='online',fish_key='fixture',fish_model='s2.1-pro-free',fish_reference='saved-voice',fish_speed=1,fish_latency='balanced'))
    speaking=threading.Event();played=[]
    async def synthesize(key,**kwargs):
        assert kwargs['reference_id']=='saved-voice' and kwargs['text']==wake.WAKE_GREETING
        assert not speaking.is_set() # Network wait must not mute recognition.
        return bytes(raw)
    monkeypatch.setattr(legacy,'synthesize_json',synthesize)
    def play(audio,flags):
        assert speaking.is_set()
        assert int.from_bytes(audio[4:8],'little')==len(audio)-8
        played.append(audio)
    monkeypatch.setitem(sys.modules,'winsound',SimpleNamespace(PlaySound=play,SND_MEMORY=1,SND_NODEFAULT=2))
    assert wake.speak_activation_greeting(speaking)=='cronos_voice'
    assert len(played)==1 and not speaking.is_set()
    async def forbidden(*args,**kwargs): raise AssertionError('Cached greeting should not call a provider')
    monkeypatch.setattr(legacy,'synthesize_json',forbidden)
    assert wake.speak_activation_greeting(speaking)=='cronos_voice'
    assert len(played)==2 and not speaking.is_set()


def test_windows_desktop_extra_is_installable():
    import tomllib
    package=tomllib.loads((Path(__file__).parents[1]/'pyproject.toml').read_text())
    assert any(dependency.startswith('pywebview==') for dependency in package['project']['optional-dependencies']['desktop'])
