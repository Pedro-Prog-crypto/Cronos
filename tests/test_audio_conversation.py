import asyncio,io,json,wave
from urllib.parse import quote
from dataclasses import replace
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
import pytest
from cronos.app import create_app
from cronos import gemini_live
from cronos.reply_stream import transcript_sink
from cronos.providers import ProviderError
from test_backend import settings,AUTH


def wav():
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x00\x02'*3200)
    return out.getvalue()


def test_audio_is_recognized_and_answered_once_and_actual_question_is_saved(settings):
    class Provider:
        calls=0
        async def reply(self,system,messages):
            self.calls+=1
            assert messages[-1]['audio_pcm']==b'\x00\x02'*3200
            return {'recognized_text':'Quem foi Sócrates?','reply':'Sócrates foi um filósofo grego.','topics':[{'title':'Sócrates','summary':'Filósofo grego.'}],'tool_calls':[]}
    provider=Provider()
    with TestClient(create_app(replace(settings,gemini_transport='live'),provider)) as client:
        assert client.get('/panels',headers=AUTH).json()['preferences']['called_only'] is False
        r=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        assert r.status_code==200
        result=json.loads(r.text)['result']
        assert result['recognized_text']=='Quem foi Sócrates?' and provider.calls==1
        history=client.get('/conversations/'+result['session_id'],headers=AUTH).json()['messages']
        assert history[0]['content']=='Quem foi Sócrates?' and 'Pergunta falada' not in str(history)


def test_audio_permission_format_and_validation(settings):
    class Provider:
        async def reply(self,*args):raise AssertionError('Invalid audio must not reach Google')
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        assert client.post('/chat/audio/stream',content=wav()).status_code==401
        assert client.post('/chat/audio/stream',headers=AUTH,content=wav()).status_code==415
        headers={**AUTH,'Content-Type':'audio/wav'}
        assert client.post('/chat/audio/stream',headers=headers,content=b'broken').status_code==422
        assert client.post('/chat/audio/stream',headers=headers,content=b'\0'*(2*1024*1024+1)).status_code==413
    with TestClient(create_app(replace(settings,privacy_mode='local'),Provider())) as client:
        assert client.post('/chat/audio/stream',headers=headers,content=wav()).status_code==503


@pytest.mark.parametrize(('transcription_provider','fish_key','expected_direct'),[
    ('fish','configured',False),('vosk','',False),('fish','',True),
])
def test_status_routes_through_configured_asr_before_gemini_live(settings,transcription_provider,fish_key,expected_direct):
    configured=replace(settings,provider='gemini',gemini_transport='live',
                       transcription_provider=transcription_provider,fish_key=fish_key)
    with TestClient(create_app(configured,object())) as client:
        status=client.get('/status',headers=AUTH).json()
    assert status['direct_audio_chat'] is expected_direct
    assert status['transcription_provider']==transcription_provider


def test_engine_is_explicitly_cautious_with_ambiguous_names(settings):
    class Provider:
        async def reply(self,system,messages):
            assert 'não transforme nomes próprios curtos' in system
            assert 'pergunte qual nome/contexto' in system
            return {'reply':'Qual Jim o senhor quer dizer?','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,Provider())) as client:
        response=client.post('/chat',headers=AUTH,json={'message':'Quem foi o Jim na cultura norte?'})
    assert response.status_code==200


def test_missing_transcript_does_not_save_placeholder_or_execute_tools(settings):
    class Provider:
        async def reply(self,*args):
            return {'reply':'Abrindo','topics':[],'tool_calls':[{'name':'obsidian_search','arguments':{'query':'Algo'}}]}
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        r=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        event=json.loads(r.text)
        assert event['type']=='error' and event['status']==502


@pytest.mark.parametrize('with_screen',[False,True])
def test_native_audio_preserves_history_and_delivers_input_transcript(settings,with_screen):
    sent=[];configs=[];recognized=[]
    raw=json.dumps({'tool_calls':[],'reply':'Resposta completa.','topics':[]})
    class Session:
        async def send_client_content(self,**kw):sent.append(('history',kw))
        async def send_realtime_input(self,**kw):sent.append(('audio',kw))
        async def receive(self):
            yield NS(server_content=NS(input_transcription=NS(text='Quem foi Sócrates?',finished=True),turn_complete=False))
            yield NS(server_content=NS(output_transcription=NS(text=raw),turn_complete=True))
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):pass
    def connect(**kw):configs.append(kw['config']);return Connection()
    async def run():
        async def sink(text):recognized.append(text)
        token=transcript_sink.set(sink)
        try:return await gemini_live.turn(NS(aio=NS(live=NS(connect=connect))),settings.gemini_live_model,'persona',[{'role':'user','content':'Mensagem anterior'},{'role':'assistant','content':'Resposta anterior'},{'role':'user','content':'Pergunta falada','audio_pcm':b'\0\0'*5000,**({'image':{'mime_type':'image/jpeg','data':'aW1hZ2U='}} if with_screen else {})}])
        finally:transcript_sink.reset(token)
    result=asyncio.run(run())
    assert result['recognized_text']=='Quem foi Sócrates?' and recognized==['Quem foi Sócrates?']
    assert configs[0].thinking_config.thinking_budget==0
    assert configs[0].input_audio_transcription is not None
    assert configs[0].realtime_input_config.automatic_activity_detection.disabled
    assert sent[0][1]['turn_complete'] is False and len(sent[0][1]['turns'])==2+with_screen
    if with_screen:assert sent[0][1]['turns'][-1]['parts'][-1]['inline_data']['mime_type']=='image/jpeg'
    packets=[kw['audio'] for _,kw in sent if 'audio' in kw]
    assert b''.join(packet.data for packet in packets)==b'\0\0'*5000
    assert all(packet.mime_type=='audio/pcm;rate=16000' for packet in packets)


def test_wake_gate_does_not_store_or_execute_uncalled_audio(settings):
    class Provider:
        async def reply(self,*args):
            from cronos.reply_stream import deliver_intro, transcript_sink
            sink=transcript_sink.get()
            if sink:await sink('Abra uma pasta')
            await deliver_intro('Uma frase que não deve chegar à voz. ')
            return {'recognized_text':'Abra uma pasta','reply':'Vou abrir.','topics':[],'tool_calls':[{'name':'obsidian_search','arguments':{'query':'Pasta'}}]}
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        client.patch('/panels/preferences',headers=AUTH,json={'called_only':True})
        r=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        events=[json.loads(line) for line in r.text.splitlines()]
        assert events[0]['type']=='transcript' and events[0]['text']=='Abra uma pasta'
        assert events[-1]['type']=='result'
        result=events[-1]['result']
        assert result['ignored'] and result['notes']==[] and result['tool_results']==[]
        assert client.get('/conversations/'+result['session_id'],headers=AUTH).json()['messages']==[]


def test_audio_waits_briefly_for_late_input_transcription(settings):
    raw=json.dumps({'tool_calls':[],'reply':'Resposta completa.','topics':[]})
    class Session:
        rounds=0
        async def send_realtime_input(self,**kw):pass
        async def receive(self):
            self.rounds+=1
            if self.rounds==1:yield NS(server_content=NS(output_transcription=NS(text=raw),turn_complete=True))
            else:yield NS(server_content=NS(input_transcription=NS(text='Quem foi Sócrates?',finished=True),turn_complete=True))
    session=Session()
    class Connection:
        async def __aenter__(self):return session
        async def __aexit__(self,*args):pass
    result=asyncio.run(gemini_live.turn(NS(aio=NS(live=NS(connect=lambda **kw:Connection()))),settings.gemini_live_model,'persona',[{'role':'user','content':'Pergunta falada','audio_pcm':b'\0\0'*400}]))
    assert result['recognized_text']=='Quem foi Sócrates?' and session.rounds==2


def test_missing_live_transcript_emits_no_partial_reply_and_is_recoverable(settings):
    raw=json.dumps({'tool_calls':[],'reply':'Não deve aparecer antes da transcrição.','topics':[]})
    delivered=[]
    class Session:
        async def send_realtime_input(self,**kw):pass
        async def receive(self):
            yield NS(server_content=NS(output_transcription=NS(text=raw),turn_complete=True))
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):pass
    async def run():
        from cronos.reply_stream import reply_sink
        async def sink(text):delivered.append(text)
        token=reply_sink.set(sink)
        try:
            with pytest.raises(ProviderError) as error:
                await gemini_live.turn(NS(aio=NS(live=NS(connect=lambda **kw:Connection()))),settings.gemini_live_model,'persona',[{'role':'user','content':'Pergunta falada','audio_pcm':b'\0\0'*400}])
            assert getattr(error.value,'kind',None)=='audio_transcription_missing'
        finally:reply_sink.reset(token)
    asyncio.run(run())
    assert delivered==[]


@pytest.mark.parametrize('status,kind',[(502,'audio_transcription_missing'),(504,None),(503,None),(429,None)])
def test_live_transcription_failure_falls_back_to_configured_asr_and_preserves_question(settings,status,kind):
    question='Cronos, explique quem foi Zeus em detalhes.'
    heard='Pergunta anterior: quem foi Zeus. Trecho já ouvido: Zeus era filho de Cronos.'
    class ASR:
        async def transcribe(self,**kwargs):
            assert kwargs['audio']==wav() and kwargs['language']=='pt'
            return NS(text=question)
    class Fish:
        asr=ASR()
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    class Provider:
        async def reply(self,system,messages):
            if messages[-1].get('audio_pcm'):
                raise ProviderError('Falha recuperável do Live',status,kind=kind)
            assert 'Trecho já ouvido' in system and 'não repita toda a explicação' in system
            return {'reply':'Zeus era o principal deus do Olimpo.','topics':[],'tool_calls':[]}
    with TestClient(create_app(replace(settings,gemini_transport='live',fish_key='configured'),Provider(),fish_factory=Fish)) as client:
        response=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav','X-Cronos-Heard-Context':quote(heard,safe='')},content=wav())
        events=[json.loads(line) for line in response.text.splitlines()]
        assert [event['type'] for event in events if event['type'] in {'transcript','result'}]==['transcript','result']
        assert events[0]['text']==question
        assert events[-1]['result']['recognized_text']==question
        assert events[-1]['result']['reply']=='Zeus era o principal deus do Olimpo.'


def test_partial_input_transcript_is_not_used_as_a_complete_command(settings):
    raw=json.dumps({'tool_calls':[],'reply':'Resposta completa.','topics':[]})
    received=[]
    class Session:
        async def send_realtime_input(self,**kw):pass
        async def receive(self):
            yield NS(server_content=NS(input_transcription=NS(text='Quem foi ',finished=False),turn_complete=False))
            yield NS(server_content=NS(output_transcription=NS(text=raw[:12]),turn_complete=False))
            assert received==[]
            yield NS(server_content=NS(input_transcription=NS(text='Sócrates?',finished=True),turn_complete=False))
            yield NS(server_content=NS(output_transcription=NS(text=raw[12:]),turn_complete=True))
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):pass
    async def run():
        async def sink(text):received.append(text)
        token=transcript_sink.set(sink)
        try:return await gemini_live.turn(NS(aio=NS(live=NS(connect=lambda **kw:Connection()))),settings.gemini_live_model,'persona',[{'role':'user','content':'Pergunta falada','audio_pcm':b'\0\0'*400}])
        finally:transcript_sink.reset(token)
    result=asyncio.run(run())
    assert received==['Quem foi Sócrates?'] and result['recognized_text']==received[0]


def test_chronos_spelling_is_allowed_by_native_wake_gate(settings):
    from cronos.reply_stream import reply_sink
    class Provider:
        async def reply(self,system,messages):
            recognized='Chronos, explique Tomás de Aquino em cards'
            sink=transcript_sink.get()
            if sink:await sink(recognized)
            sink=reply_sink.get()
            if sink:await sink('## Contexto\nTomás de Aquino viveu no século XIII.')
            return {'recognized_text':recognized,'reply':'## Contexto\nTomás de Aquino viveu no século XIII.','topics':[],'tool_calls':[]}
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        assert client.patch('/panels/preferences',headers=AUTH,json={'called_only':True}).status_code==200
        response=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        events=[json.loads(line) for line in response.text.splitlines()]
        assert any(e['type']=='reply' for e in events)
        assert events[-1]['type']=='result'
        assert not events[-1]['result'].get('ignored')
