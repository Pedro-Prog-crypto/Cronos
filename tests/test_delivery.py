import json,asyncio,re
from dataclasses import replace
from uuid import uuid4
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos import wake
from cronos.delivery import DeliveryLog
from test_backend import settings,AUTH
from test_audio_conversation import wav

class Fish:
    spoken=[]
    def __init__(self):self.tts=self;self.asr=self
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def transcribe(self,**kwargs):return type('Text',(),{'text':'Quanto é dezessete mais vinte e seis?'})()
    async def convert(self,**kwargs):self.spoken.append(kwargs['text']);return wav()


def test_receipts_confirm_same_turn_across_actual_routes_without_private_content(settings):
    called=[]
    class Provider:
        async def reply(self,system,messages):
            called.append(messages[-1]['content'])
            return {'reply':'O resultado é quarenta e três.','tool_calls':[],'topics':[]}
    turn=str(uuid4());headers={**AUTH,'X-Cronos-Turn':turn}
    with TestClient(create_app(replace(settings,fish_key='fixture'),Provider(),fish_factory=Fish)) as client:
        text=client.post('/voice/transcribe',headers={**headers,'Content-Type':'audio/wav'},content=wav()).json()['text']
        events=[json.loads(line) for line in client.post('/chat/stream',headers=headers,json={'message':text}).text.splitlines()]
        answer=events[-1]['result']['reply']
        assert client.post('/voice/speech',headers=headers,json={'text':answer}).status_code==200
        client.post('/panels/latency',headers=AUTH,json={'turn_id':turn,'source':'voice','chat_ms':240,'first_audio_ms':400,'response_ms':600})
        assert client.get('/voice/delivery').status_code==401
        report=client.get('/voice/delivery',headers=AUTH).json()
        assert len(report['turns'])==1 and report['turns'][0]['turn_id']==turn
        stages=[row['stage'] for row in report['turns'][0]['events']]
        for stage in ['audio_received','recognition_requested','recognition_response','question_recognized','question_received','answer_requested','answer_received','voice_requested','voice_received','playback_started']:assert stage in stages
        assert stages.index('audio_received')<stages.index('answer_requested')<stages.index('voice_requested')<stages.index('playback_started')
        assert text not in json.dumps(report) and answer not in json.dumps(report) and 'fixture' not in json.dumps(report)
        assert called==[text] and Fish.spoken[-1]==answer


def test_real_check_requires_actual_computed_answer_and_audio(settings):
    class Provider:
        async def reply(self,system,messages):
            nums=re.findall(r'\d+',messages[-1]['content'])
            return {'reply':'O resultado é '+str(sum(map(int,nums)))+'.','tool_calls':[],'topics':[]}
    with TestClient(create_app(replace(settings,fish_key='fixture',fish_format='wav'),Provider(),fish_factory=Fish)) as client:
        assert client.post('/voice/check',json={}).status_code==401
        r=client.post('/voice/check',headers=AUTH,json={});assert r.status_code==200,r.text
        data=r.json();assert data['audio_base64'] and data['answer'].startswith('O resultado é ')
        assert Fish.spoken[-1]==data['answer']
        report=client.get('/voice/delivery',headers=AUTH).json()
        assert [e['stage'] for e in report['turns'][0]['events']]==['question_received','answer_requested','answer_received','voice_requested','voice_received']


def test_canned_greeting_never_passes_integration_check(settings):
    class Provider:
        async def reply(self,*args):return {'reply':'Pois não, senhor? O que deseja?','tool_calls':[],'topics':[]}
    def forbidden():raise AssertionError('No TTS for an invalid response')
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider(),fish_factory=forbidden)) as client:
        r=client.post('/voice/check',headers=AUTH,json={})
        assert r.status_code==502
        events=client.get('/voice/delivery',headers=AUTH).json()['turns'][0]['events']
        assert events[-1]['stage']=='failed' and not any(e['stage']=='voice_received' for e in events)
        native=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        assert json.loads(native.text)['type']=='error'
        native_events=client.get('/voice/delivery',headers=AUTH).json()['turns'][0]['events']
        assert native_events[0]['stage']=='audio_received'
        assert not any(e['stage']=='question_received' for e in native_events)



def test_delivery_memory_is_bounded_and_rejects_unlisted_payload():
    log=DeliveryLog()
    for i in range(45):log.record(str(i),'audio_received',bytes=10,api_key='private',question='private')
    for i in range(45):log.record('44','voice_received',bytes=i)
    rows=log.snapshot();assert len(rows)==10 and len(rows[0]['events'])==40
    assert 'private' not in json.dumps(rows)


def test_wake_greeting_does_not_override_a_live_window_microphone(tmp_path,monkeypatch):
    monkeypatch.setattr(wake,'root',lambda:tmp_path)
    clock=[1000.0];monkeypatch.setattr(wake.time,'time',lambda:clock[0])
    assert not wake.ui_is_listening()
    wake.set_ui_listening(True);assert wake.ui_is_listening()
    clock[0]=1013;assert not wake.ui_is_listening()
    wake.set_ui_listening(True);assert wake.ui_is_listening()
    wake.set_ui_listening(False);assert not wake.ui_is_listening()


def test_received_silence_is_distinguished_from_audio_never_reaching_server(settings):
    import io,wave
    out=io.BytesIO()
    with wave.open(out,'wb') as writer:
        writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(16000);writer.writeframes(b'\0\0'*3200)
    with TestClient(create_app(settings)) as client:
        response=client.post('/voice/transcribe',headers={**AUTH,'Content-Type':'audio/wav'},content=out.getvalue())
        assert response.status_code==422
        events=client.get('/voice/delivery',headers=AUTH).json()['turns'][0]['events']
        assert events[0]['stage']=='audio_received' and events[0]['bytes']==len(out.getvalue())
        assert events[-1]['stage']=='failed' and events[-1]['http_status']==422
        assert not any(event['stage']=='recognition_requested' for event in events)
