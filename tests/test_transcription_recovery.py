import asyncio
import base64
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.transcription import gemini_transcribe
from cronos.providers import ProviderError
from test_backend import settings,AUTH
from test_audio_conversation import wav


@pytest.mark.parametrize('failure',['exception','empty'])
def test_same_audio_uses_configured_gemini_when_fish_cannot_transcribe(settings,monkeypatch,failure):
    original=httpx.AsyncClient;requests=[];recordings=[]
    def handle(request):
        requests.append(request);body=json.loads(request.content)
        assert base64.b64decode(body['contents'][0]['parts'][1]['inlineData']['data'])==wav()
        assert body['contents'][0]['parts'][1]['inlineData']['mimeType']=='audio/wav'
        assert len(body['contents'])==1  # No history or fabricated candidate question.
        return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps({'text':'Quem foi Sócrates?'})}]}}]})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handle),**kwargs))
    class Fish:
        def __init__(self):self.asr=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kwargs):
            recordings.append(kwargs['audio'])
            if failure=='exception':raise RuntimeError('controlled ASR offline')
            return type('Result',(),{'text':''})()
    with TestClient(create_app(replace(settings,gemini_key='fixture',fish_key='fixture'),fish_factory=Fish)) as client:
        response=client.post('/voice/transcribe',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        assert response.status_code==200 and response.json()['text']=='Quem foi Sócrates?'
    assert len(requests)==1 and recordings==[wav()]


@pytest.mark.parametrize('text',['',None,{},' '])
def test_invalid_alternative_is_not_turned_into_a_question(settings,monkeypatch,text):
    original=httpx.AsyncClient
    payload={'candidates':[{'content':{'parts':[{'text':json.dumps({'text':text})}]}}]}
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda request:httpx.Response(200,json=payload)),**kw))
    with pytest.raises(ProviderError):asyncio.run(gemini_transcribe(replace(settings,gemini_key='fixture'),wav(),'audio/wav'))


def test_local_mode_never_sends_a_recording_to_gemini(settings,monkeypatch):
    def forbidden(**kw):raise AssertionError('No external audio in local mode')
    monkeypatch.setattr(httpx,'AsyncClient',forbidden)
    with pytest.raises(ProviderError):asyncio.run(gemini_transcribe(replace(settings,privacy_mode='local',gemini_key='fixture'),wav(),'audio/wav'))


def test_incomplete_alternative_transcript_is_rejected(settings,monkeypatch):
    original=httpx.AsyncClient
    payload={'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'{"text":"partial"}'}]}}]}
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda request:httpx.Response(200,json=payload)),**kw))
    with pytest.raises(ProviderError):asyncio.run(gemini_transcribe(replace(settings,gemini_key='fixture'),wav(),'audio/wav'))


def test_local_endpoint_does_not_call_online_fish(settings):
    def forbidden():raise AssertionError('Local mode must not construct a cloud recognizer')
    with TestClient(create_app(replace(settings,privacy_mode='local',fish_key='fixture'),fish_factory=forbidden)) as client:
        response=client.post('/voice/transcribe',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        assert response.status_code==503


def test_recognized_question_survives_native_failure_without_transcribing_again(settings):
    from cronos.reply_stream import transcript_sink
    class Provider:
        async def reply(self,system,messages):
            if messages[-1].get('audio_pcm') is not None:
                await transcript_sink.get()('Quem foi Sócrates?')
                raise ProviderError('Controlled native answer failure',503)
            assert messages[-1]['content']=='Quem foi Sócrates?'
            return {'reply':'Sócrates foi um filósofo grego.','topics':[],'tool_calls':[]}
    def forbidden():raise AssertionError('Known question must not be transcribed again')
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider(),fish_factory=forbidden)) as client:
        r=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=wav())
        events=[json.loads(line) for line in r.text.splitlines()]
        assert [e['type'] for e in events]==['transcript','reply','result']
        assert events[-1]['result']['recognized_text']=='Quem foi Sócrates?'
