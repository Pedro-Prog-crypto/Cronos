import asyncio,io,json,wave
from dataclasses import replace
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
import pytest
from cronos.app import create_app
from cronos import gemini_live
from cronos.reply_stream import transcript_sink
from test_backend import settings,AUTH


def wav():
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x00\x00'*3200)
    return out.getvalue()


def test_audio_is_recognized_and_answered_once_and_actual_question_is_saved(settings):
    class Provider:
        calls=0
        async def reply(self,system,messages):
            self.calls+=1
            assert messages[-1]['audio_pcm']==b'\0\0'*3200
            return {'recognized_text':'Quem foi Sócrates?','reply':'Sócrates foi um filósofo grego.','topics':[{'title':'Sócrates','summary':'Filósofo grego.'}],'tool_calls':[]}
    provider=Provider()
    with TestClient(create_app(replace(settings,gemini_transport='live'),provider)) as client:
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


def test_missing_transcript_does_not_save_placeholder_or_execute_tools(settings):
    class Provider:
        async def reply(self,*args):
            return {'reply':'Abrindo','topics':[],'tool_calls':[{'name':'obsidian_search','arguments':{'query':'Algo'}}]}
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        r=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        event=json.loads(r.text)
        assert event['type']=='error' and event['status']==502


def test_native_audio_preserves_history_and_delivers_input_transcript(settings):
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
        try:return await gemini_live.turn(NS(aio=NS(live=NS(connect=connect))),settings.gemini_live_model,'persona',[{'role':'user','content':'Mensagem anterior'},{'role':'assistant','content':'Resposta anterior'},{'role':'user','content':'Pergunta falada','audio_pcm':b'\0\0'*5000}])
        finally:transcript_sink.reset(token)
    result=asyncio.run(run())
    assert result['recognized_text']=='Quem foi Sócrates?' and recognized==['Quem foi Sócrates?']
    assert configs[0].input_audio_transcription is not None
    assert configs[0].realtime_input_config.automatic_activity_detection.disabled
    assert sent[0][1]['turn_complete'] is False and len(sent[0][1]['turns'])==2
    packets=[kw['audio'] for _,kw in sent if 'audio' in kw]
    assert b''.join(packet.data for packet in packets)==b'\0\0'*5000
    assert all(packet.mime_type=='audio/pcm;rate=16000' for packet in packets)


def test_wake_gate_does_not_store_or_execute_uncalled_audio(settings):
    class Provider:
        async def reply(self,*args):
            from cronos.reply_stream import deliver_intro
            await deliver_intro('Uma frase que não deve chegar à voz. ')
            return {'recognized_text':'Abra uma pasta','reply':'Vou abrir.','topics':[],'tool_calls':[{'name':'obsidian_search','arguments':{'query':'Pasta'}}]}
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        client.patch('/panels/preferences',headers=AUTH,json={'called_only':True})
        r=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        result=json.loads(r.text)['result']
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
