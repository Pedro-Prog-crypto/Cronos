import asyncio
import io
import json
import math
from pathlib import Path
import struct
import threading
from types import SimpleNamespace
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from cronos import wake,resident
from cronos.app import create_app
from cronos.background_conversation import NativeConversation
from cronos.background_listener import Capture
from cronos.desktop_state import needs_screen,wants_card
from test_backend import settings,AUTH


def wav():
    data=io.BytesIO()
    with wave.open(data,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000)
        output.writeframes(b''.join(struct.pack('<h',int(1500*math.sin(i*.1))) for i in range(16000)))
    return data.getvalue()


@pytest.fixture
def isolated(tmp_path,monkeypatch):
    monkeypatch.setenv('CRONOS_DATA_HOME',str(tmp_path))
    monkeypatch.setattr(wake,'root',lambda:tmp_path/'wake')
    return tmp_path


@pytest.mark.parametrize('name,opening',[('cronos','abrir cronos'),('pastel azul','abrir pastel azul'),('nave','mostrar nave')])
def test_calling_only_activates_conversation_and_opening_is_a_separate_intent(isolated,name,opening):
    config=wake.validate_settings({**wake.DEFAULT_SETTINGS,'activation_phrase':name})
    trigger=wake.Trigger(config)
    def heard(text):return {'text':text,'result':[{'conf':.95}]}
    assert trigger.action(heard(name),now=100)=='activate'
    assert trigger.action(heard(opening),now=103)=='show'
    assert trigger.action(heard('eu falei '+opening+' ontem'),now=106) is None
    assert trigger.action(heard('não '+opening),now=109) is None


def test_native_capture_keeps_a_long_turn_and_manual_send_does_not_need_silence():
    capture=Capture();capture.arm()
    frame=struct.pack('<h',900)*1600
    for _ in range(800):assert capture.feed(frame) is None
    result=capture.submit()
    with wave.open(io.BytesIO(result),'rb') as audio:
        assert audio.getnframes()==800*1600
        assert audio.getframerate()==16000
    assert not capture.armed and not capture.frames


def test_silence_endpoint_and_quiet_recognized_speech_are_preserved():
    now=[0];capture=Capture(lambda:now[0]);capture.arm()
    capture.feed(struct.pack('<h',1000)*1600);now[0]=1.4
    assert capture.feed(b'\0\0'*1600).startswith(b'RIFF')
    capture.arm()
    assert capture.feed(struct.pack('<h',80)*1600,recognized=True) is None
    now[0]+=1.4
    assert capture.feed(b'\0\0'*1600).startswith(b'RIFF')
    capture.arm();now[0]=23
    assert capture.feed(b'\0\0'*1600) is None and not capture.armed


class UI:
    def __init__(self):self.cards=[];self.phases=[]
    def phase(self,text):self.phases.append(text)
    def card(self,title,text):self.cards.append((title,text))


class Speaker:
    def __init__(self,cancel):self.cancel=cancel;self.played=[];self.local_text=[]
    def wav(self,body,volume):
        assert body.startswith(b'RIFF') and volume>0
        self.played.append(body);return True
    def local(self,text,volume=1):self.local_text.append(text);return True
    def stop(self):pass


def test_native_turn_reaches_asr_ai_wav_and_floating_card_without_launching_main(settings,isolated,monkeypatch):
    from dataclasses import replace
    from cronos.reply_stream import deliver_intro
    question='Resuma a matéria que está na minha tela.'
    observed=[];spoken=[];played=[]
    class Fish:
        def __init__(self):self.asr=self;self.tts=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kw):
            assert kw['audio'].startswith(b'RIFF');return SimpleNamespace(text=question)
        async def convert(self,**kw):
            assert kw['format']=='wav';spoken.append(kw['text']);return wav()
    class Provider:
        async def reply(self,system,messages):
            observed.append(messages[-1]);assert messages[-1]['content']==question
            assert messages[-1]['image']['mime_type']=='image/jpeg'
            await deliver_intro('A matéria explica a divisão celular. ')
            return {'reply':'A matéria explica a divisão celular. A mitose mantém o número de cromossomos.','topics':[],'tool_calls':[]}
    app=create_app(replace(settings,fish_key='fixture',fish_format='mp3'),Provider(),fish_factory=Fish)
    from PIL import Image
    image=io.BytesIO();Image.new('RGB',(200,100),'blue').save(image,format='PNG')
    monkeypatch.setattr('cronos.background_listener.launch_window',lambda:pytest.fail('A name or answer must not launch the UI'))
    with TestClient(app,base_url='http://127.0.0.1',client=('127.0.0.1',5010),headers=AUTH) as client:
        app.state.windows.platform='win32';app.state.live_screen.capture=lambda:image.getvalue()
        assert client.post('/assistant/screen',json={'consent':True}).status_code==200
        ui=UI()
        def factory(cancel):value=Speaker(cancel);played.append(value);return value
        native=NativeConversation(SimpleNamespace(client=client),ui,factory)
        assert native.run(wav())
        events=client.get('/voice/delivery').json()['turns'][0]['events']
        assert any(event['stage']=='playback_completed' for event in events)
        assert not any(event['stage']=='playback_started' for event in events),'Native APIs do not provide a physical first-sample timestamp'
        state=client.get('/assistant/state').json()
        assert state['session_id']==native.session and state['opens_on_name'] is False
    assert ' '.join(spoken)=='A matéria explica a divisão celular. A mitose mantém o número de cromossomos.'
    assert len(played[0].played)==2 and ui.cards[0][0]=='Resumo da tela'
    assert not (resident.folder()/'pending-recording.wav').exists()


@pytest.mark.parametrize('failure',['asr','provider','voice'])
def test_native_failure_preserves_recording_and_never_claims_spoken_success(settings,isolated,failure):
    from dataclasses import replace
    class Fish:
        def __init__(self):self.asr=self;self.tts=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kw):
            if failure=='asr':raise RuntimeError('ASR unavailable')
            return SimpleNamespace(text='Quem foi Aristóteles?')
        async def convert(self,**kw):raise RuntimeError('Voice unavailable')
    class Provider:
        async def reply(self,*args):
            if failure=='provider':raise RuntimeError('provider unavailable')
            return {'reply':'Aristóteles foi um filósofo grego.','topics':[],'tool_calls':[]}
    class Silent(Speaker):
        def local(self,*args):raise RuntimeError('No local speech voice')
    with TestClient(create_app(replace(settings,fish_key='fixture'),Provider(),fish_factory=Fish),headers=AUTH) as client:
        ui=UI();native=NativeConversation(SimpleNamespace(client=client),ui,Silent)
        assert not native.run(wav())
        assert (resident.folder()/'pending-recording.wav').read_bytes()==wav()
        assert ui.cards and not native.processing.is_set()
        assert json.loads((resident.folder()/'last-delivery.json').read_text())['stage']=='failed'


def test_tts_failure_uses_same_actual_ai_answer_with_local_voice(settings,isolated):
    from dataclasses import replace
    local=[]
    class Fish:
        def __init__(self):self.asr=self;self.tts=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kw):return SimpleNamespace(text='Como você está?')
        async def convert(self,**kw):raise RuntimeError('TTS failure')
    class Provider:
        async def reply(self,*args):return {'reply':'Estou aqui, senhor. Como foi o dia?','topics':[],'tool_calls':[]}
    class Device(Speaker):
        def local(self,text,volume):local.append(text);return True
    with TestClient(create_app(replace(settings,fish_key='fixture'),Provider(),fish_factory=Fish),headers=AUTH) as client:
        assert NativeConversation(SimpleNamespace(client=client),UI(),Device).run(wav())
    assert local==['Estou aqui, senhor. Como foi o dia?']


def test_non_screen_question_does_not_send_the_live_frame(settings,isolated):
    class Provider:
        async def reply(self,system,messages):
            assert 'image' not in messages[-1]
            return {'reply':'A mitose é uma divisão celular.','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,Provider()),headers=AUTH) as client:
        manager=client.app.state.live_screen
        async def snapshot(session):pytest.fail('Unrelated question must not request a screenshot')
        manager.active=lambda session:True;manager.snapshot=snapshot
        response=client.post('/chat/stream',json={'message':'Explique a mitose.','screen_context':False})
        assert '"type": "result"' in response.text


@pytest.mark.parametrize('url',['https://example.org','http://localhost:80','http://127.0.0.1:45/evil','http://x:secret@127.0.0.1:45','http://127.0.0.1:45/?token=x'])
def test_resident_descriptor_never_sends_credentials_to_another_host_or_document(url):
    with pytest.raises(ValueError):resident.Connection({'url':url,'token':'x'*32})


def test_background_screen_requires_local_authenticated_request_and_saved_consent(settings,isolated):
    from dataclasses import replace
    app=create_app(settings)
    with TestClient(app,client=('203.0.113.10',30)) as client:
        app.state.windows.platform='win32'
        assert client.post('/assistant/screen',headers=AUTH,json={'consent':True}).status_code==403
    with TestClient(app,base_url='http://127.0.0.1',client=('127.0.0.1',30)) as client:
        app.state.windows.platform='win32'
        assert client.post('/assistant/screen',json={'consent':True}).status_code==401
        wake.save_settings({'screen_enabled':False})
        assert client.post('/assistant/screen',headers=AUTH,json={'consent':True}).status_code==403
        assert client.post('/assistant/screen',headers=AUTH,json={'consent':False}).status_code==422


def test_intent_scope_keeps_screen_and_card_optional():
    assert needs_screen('Resuma a matéria da Wikipedia.') and wants_card('Resuma a matéria da Wikipedia.')
    assert not needs_screen('Quem foi Sócrates?') and not wants_card('Quem foi Sócrates?')
    assert needs_screen('O que aparece na minha tela?')


def test_native_cancel_releases_an_asr_request_already_waiting_on_the_provider(settings,isolated):
    from dataclasses import replace
    entered,cancelled=threading.Event(),threading.Event()
    class Fish:
        def __init__(self):self.asr=self;self.tts=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kw):
            entered.set()
            try:await asyncio.sleep(60)
            finally:cancelled.set()
    with TestClient(create_app(replace(settings,fish_key='fixture',gemini_key=''),fish_factory=Fish),headers=AUTH) as client:
        native=NativeConversation(SimpleNamespace(client=client),UI(),Speaker)
        result=[];thread=threading.Thread(target=lambda:result.append(native.run(wav())),daemon=True)
        thread.start();assert entered.wait(3)
        native.stop();thread.join(timeout=3)
        assert not thread.is_alive() and cancelled.is_set()
        assert result==[False] and not native.processing.is_set()
        assert json.loads((resident.folder()/'last-delivery.json').read_text())['stage']=='cancelled'
        assert (resident.folder()/'pending-recording.wav').exists()


def test_cancelling_before_http_arrives_does_not_start_synthesis(settings,isolated):
    from dataclasses import replace
    from uuid import uuid4
    synthesized=[]
    class Fish:
        def __init__(self):self.tts=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def convert(self,**kw):synthesized.append(kw);return wav()
    turn=str(uuid4())
    with TestClient(create_app(replace(settings,fish_key='fixture'),fish_factory=Fish),headers=AUTH) as client:
        assert client.post('/assistant/cancel',json={'turn_id':turn}).status_code==200
        result=client.post('/voice/speech',headers={'X-Cronos-Turn':turn},json={'text':'Resposta recebida','format':'wav'})
        assert result.status_code==499 and not synthesized


def test_failed_local_voice_with_a_long_reply_does_not_block_a_full_queue(settings,isolated):
    from dataclasses import replace
    class Fish:
        def __init__(self):self.asr=self;self.tts=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kw):return SimpleNamespace(text='Explique um assunto muito longo.')
        async def convert(self,**kw):raise RuntimeError('cloud voice failed')
    class Provider:
        async def reply(self,*args):return {'reply':'Uma explicação extensa. '*800,'tool_calls':[],'topics':[]}
    class NoVoice(Speaker):
        def local(self,*args):raise RuntimeError('local voice failed')
    with TestClient(create_app(replace(settings,fish_key='fixture'),Provider(),fish_factory=Fish),headers=AUTH) as client:
        native=NativeConversation(SimpleNamespace(client=client),UI(),NoVoice)
        result=[];thread=threading.Thread(target=lambda:result.append(native.run(wav())),daemon=True)
        thread.start();thread.join(timeout=4)
        assert not thread.is_alive() and result==[False]


def test_public_page_content_is_source_data_and_not_rewritten_as_user_speech(settings,isolated):
    class Provider:
        async def reply(self,system,messages):
            assert 'não confiável' in system and 'Conteúdo obtido da página' in system
            assert messages[-1]['content']=='Resuma esta página.'
            return {'reply':'A página trata de biologia.','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,Provider()),headers=AUTH) as client:
        response=client.post('/chat/stream',json={'message':'Resuma esta página.','screen_context':False,'page_context':json.dumps({'url':'https://example.org','text':'Texto de biologia','truncated':True})})
        assert '"type": "result"' in response.text


def test_ui_microphone_reservation_expires_and_does_not_claim_permanent_capture(isolated,monkeypatch):
    now=[100]
    monkeypatch.setattr(wake.time,'time',lambda:now[0])
    wake.set_ui_open(True);assert wake.ui_owns_microphone()
    now[0]=113;assert not wake.ui_owns_microphone()
    wake.set_ui_listening(True);assert wake.ui_owns_microphone()
    wake.set_ui_listening(False);wake.set_ui_open(False);assert not wake.ui_owns_microphone()


def test_control_routing_distinguishes_calls_opening_negation_and_screen_requests():
    from cronos.desktop_state import control_intent
    config=wake.DEFAULT_SETTINGS
    assert control_intent('Cronos',config) is None
    assert control_intent('Cronos, abra o Cronos',config)=='show'
    assert control_intent('Cronos, feche o Cronos',config)=='hide'
    assert control_intent('Por que você abre o Cronos sozinho?',config) is None
    assert control_intent('Não abra o Cronos.',config) is None
    assert control_intent('Cronos, pare de ver a minha tela.',config)=='screen_off'
    assert control_intent('Cronos, veja minha tela.',config)=='screen_on'


def test_native_cancel_during_synthesis_does_not_start_a_backup_voice(settings,isolated):
    from dataclasses import replace
    entered,cancelled=threading.Event(),threading.Event()
    class Fish:
        def __init__(self):self.asr=self;self.tts=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kw):return SimpleNamespace(text='Como foi seu dia?')
        async def convert(self,**kw):
            entered.set()
            try:await asyncio.sleep(60)
            finally:cancelled.set()
    class Provider:
        async def reply(self,*args):return {'reply':'Estou aqui para conversar, senhor.','topics':[],'tool_calls':[]}
    class Guard(Speaker):
        def local(self,*args):pytest.fail('Cancelling must not start another voice')
    with TestClient(create_app(replace(settings,fish_key='fixture'),Provider(),fish_factory=Fish),headers=AUTH) as client:
        native=NativeConversation(SimpleNamespace(client=client),UI(),Guard)
        result=[];thread=threading.Thread(target=lambda:result.append(native.run(wav())),daemon=True)
        thread.start();assert entered.wait(3)
        native.stop();thread.join(timeout=3)
        assert not thread.is_alive() and result==[False] and cancelled.is_set()


def test_native_input_is_closed_for_ui_and_reopened_after_the_window_releases_it(isolated,monkeypatch):
    import queue
    from contextlib import nullcontext
    from cronos import persistent_data
    from cronos import background_listener as listener
    import sys
    opened,closed,resumed,finished=(threading.Event() for _ in range(4))
    streams=[]
    monkeypatch.setattr(persistent_data,'activate',lambda root:None)
    monkeypatch.setattr(wake,'single_instance',lambda name:nullcontext(True))
    monkeypatch.setattr(wake,'verify_model',lambda:isolated)
    monkeypatch.setattr(listener,'launch_window',lambda:pytest.fail('No explicit open command was given'))
    class Client:
        def post(self,*args,**kwargs):return SimpleNamespace(raise_for_status=lambda:None)
    monkeypatch.setattr(resident,'ensure',lambda:SimpleNamespace(client=Client(),close=lambda:None))
    class Recognizer:
        def __init__(self,*args):pass
        def SetWords(self,*args):pass
    class Stream:
        def __init__(self,**kwargs):self.active=False;streams.append(self)
        def __enter__(self):
            self.active=True
            (opened if len(streams)==1 else resumed).set();return self
        def __exit__(self,*args):self.active=False;closed.set()
    class Overlay:
        def __init__(self):self.actions=queue.Queue()
        def phase(self,*args):pass
        def card(self,*args):pass
        def close(self):finished.set()
        def run(self):
            assert opened.wait(2)
            wake.set_ui_open(True);assert closed.wait(2)
            assert not streams[0].active
            wake.set_ui_open(False);assert resumed.wait(2)
            (wake.root()/'stop.request').write_text('stop')
            assert finished.wait(2)
    monkeypatch.setitem(sys.modules,'vosk',SimpleNamespace(KaldiRecognizer=Recognizer,Model=lambda path:None,SetLogLevel=lambda n:None))
    monkeypatch.setitem(sys.modules,'sounddevice',SimpleNamespace(RawInputStream=Stream))
    listener.run(Overlay())
    assert len(streams)==2 and not any(stream.active for stream in streams)


def test_corrupt_native_settings_do_not_silently_enable_capture(isolated):
    wake.root().mkdir(parents=True)
    (wake.root()/'settings.json').write_text('{invalid json')
    config=wake.settings()
    assert config['screen_enabled'] is False and config['background_enabled'] is False


def test_explicit_vision_stop_is_saved_and_clears_even_a_foreground_session(settings,isolated):
    with TestClient(create_app(settings),base_url='http://127.0.0.1',client=('127.0.0.1',30),headers=AUTH) as client:
        client.app.state.windows.platform='win32'
        manager=client.app.state.live_screen;manager.session='foreground-session';manager.frame={'data':'fixture'}
        result=client.post('/assistant/vision-setting',json={'consent':True,'enabled':False})
        assert result.status_code==200 and result.json()['screen_enabled'] is False
        assert manager.frame is None and manager.session is None
        assert wake.settings()['screen_enabled'] is False
