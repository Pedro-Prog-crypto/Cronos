"""Conversation latency regressions. External generation is controlled, never timed as a real API."""
import asyncio
import json
import threading
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from cronos import conversation_transport as transport, evolution, conversation_metrics
from cronos.app import create_app
from cronos.memory_policy import greeting_only
from cronos.providers import ProviderError
from cronos.reply_stream import intro_sink, reply_sink, deliver_intro
from cronos.storage import Memory
from test_backend import settings, AUTH


def sse(text):
    return ('data: '+json.dumps({'candidates':[{'content':{'parts':[{'text':text}]}}]})+'\n\n').encode()


def mock_http(monkeypatch, handler):
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))


def test_text_conversation_streams_intro_and_full_reply_before_metadata(settings,monkeypatch):
    emitted=[]
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse('{"tool_calls":[],"reply":"Tudo certo, senhor. ')
            assert emitted==[('intro','Tudo certo, senhor.')]
            yield sse('Pronto para conversar.",')
            assert emitted[-1]==('reply','Tudo certo, senhor. Pronto para conversar.')
            yield sse('"topics":[]}')
    async def handle(request):
        assert request.url.path.endswith(':streamGenerateContent')
        assert request.url.params['alt']=='sse'
        body=json.loads(request.content)
        assert body['generationConfig']['thinkingConfig']=={'thinkingBudget':0}
        assert 'audio' not in str(body).lower()
        return httpx.Response(200,headers={'Content-Type':'text/event-stream'},stream=Stream())
    mock_http(monkeypatch,handle)
    async def forbidden(*args):raise AssertionError('Healthy text request must not generate Live audio')
    monkeypatch.setattr('cronos.gemini_live.reply',forbidden)
    async def run():
        async def intro(value):emitted.append(('intro',value))
        async def reply(value):emitted.append(('reply',value))
        a=intro_sink.set(intro);b=reply_sink.set(reply)
        try:
            return await transport.conversation_provider(replace(settings,gemini_key='fixture',gemini_transport='live')).reply('persona',[{'role':'user','content':'Oi'}])
        finally:intro_sink.reset(a);reply_sink.reset(b)
    assert asyncio.run(run())['reply']=='Tudo certo, senhor. Pronto para conversar.'


def test_live_only_configuration_can_recover_before_any_speech(settings,monkeypatch):
    async def unavailable(request):return httpx.Response(404,json={'error':{'code':404}})
    mock_http(monkeypatch,unavailable)
    async def live(*args):return {'reply':'Voz alternativa.','topics':[],'tool_calls':[]}
    monkeypatch.setattr('cronos.gemini_live.reply',live)
    result=asyncio.run(transport.conversation_provider(replace(settings,gemini_key='fixture',gemini_transport='live')).reply('persona',[{'role':'user','content':'Oi'}]))
    assert result['reply']=='Voz alternativa.'


def test_broken_stream_after_intro_does_not_start_a_second_answer(settings,monkeypatch):
    emitted=[]
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse('{"tool_calls":[],"reply":"Uma resposta que já começou. ')
            raise httpx.ReadError('fixture connection interrupted')
    mock_http(monkeypatch,lambda request:httpx.Response(200,headers={'Content-Type':'text/event-stream'},stream=Stream()))
    async def forbidden(*args):raise AssertionError('Cannot replay after spoken prefix')
    monkeypatch.setattr('cronos.gemini_live.reply',forbidden)
    async def run():
        async def intro(value):emitted.append(value)
        token=intro_sink.set(intro)
        try:
            with pytest.raises(ProviderError):
                await transport.conversation_provider(replace(settings,gemini_key='fixture',gemini_transport='live')).reply('',[{'role':'user','content':'Oi'}])
        finally:intro_sink.reset(token)
    asyncio.run(run());assert len(emitted)==1


def test_heartbeats_do_not_keep_a_silent_connection_alive(settings,monkeypatch):
    monkeypatch.setattr(transport,'FIRST_TEXT_TIMEOUT',.04)
    closed=[]
    class Heartbeats(httpx.AsyncByteStream):
        async def __aiter__(self):
            while True:
                yield b': ping\n\n'
                await asyncio.sleep(.005)
        async def aclose(self):closed.append(True)
    mock_http(monkeypatch,lambda request:httpx.Response(200,headers={'Content-Type':'text/event-stream'},stream=Heartbeats()))
    async def run():
        with pytest.raises(ProviderError) as caught:
            await asyncio.wait_for(transport.conversation_provider(replace(settings,gemini_key='fixture')).reply('',[{'role':'user','content':'Oi'}]),.5)
        assert caught.value.retryable
    asyncio.run(run());assert closed


def test_in_progress_answer_survives_first_reply_deadline(settings,monkeypatch):
    monkeypatch.setattr(evolution,'FIRST_REPLY_TIMEOUT_SECONDS',.02)
    class Streaming:
        async def reply(self,*args):
            await deliver_intro('Uma explicação longa começou. ')
            await asyncio.sleep(.06)
            return {'reply':'Uma explicação longa começou. E continua até o fim.','topics':[],'tool_calls':[]}
    async def run():
        async def intro(value):assert value.startswith('Uma explicação')
        token=intro_sink.set(intro)
        try:return await evolution.ResilientProvider(settings,Streaming()).reply('',[])
        finally:intro_sink.reset(token)
    assert asyncio.run(run())['reply'].endswith('até o fim.')


@pytest.mark.parametrize(('text','expected'),[
    ('E aí, Kronos, de boa? Como é que você tá, mano?',True),
    ('Bom dia, Cronos!',True),
    ('Oi Cronos, quem foi Sócrates?',False),
    ('E aí, como está a economia?',False),
    ('Cronos, veja minha tela.',False),
    ('De boa, mas estou triste hoje.',False),
])
def test_only_complete_greetings_use_lightweight_context(text,expected):
    assert greeting_only(text) is expected


def test_greeting_skips_screen_and_tool_catalog_but_is_answered_by_model(settings,monkeypatch):
    class Provider:
        async def reply(self,system,messages):
            assert settings.personality.read_text() in system
            assert len(messages)==1 and messages[0]['content'].startswith('E aí')
            return {'reply':'Tudo certo, senhor. Como foi seu dia?','tool_calls':[],'topics':[]}
    with TestClient(create_app(settings,Provider())) as client:
        def forbidden(*args,**kwargs):raise AssertionError('Greeting must not load catalog, screen or recall')
        monkeypatch.setattr(client.app.state.engine.registry,'catalog',forbidden)
        monkeypatch.setattr(client.app.state.memory,'recall',forbidden)
        result=client.post('/chat/stream',headers=AUTH,json={'message':'E aí, Kronos, de boa? Como é que você tá, mano?'})
        events=[json.loads(line) for line in result.text.splitlines()]
        assert [event['type'] for event in events]==['reply','result']
        assert events[-1]['result']['reply']=='Tudo certo, senhor. Como foi seu dia?'


def test_background_memory_scan_does_not_lock_a_greeting(settings,monkeypatch):
    started=threading.Event();release=threading.Event()
    class Provider:
        async def reply(self,*args):return {'reply':'Tudo certo, senhor.','tool_calls':[],'topics':[]}
    with TestClient(create_app(settings,Provider())) as client:
        def slow_scan():started.set();assert release.wait(4)
        monkeypatch.setattr(client.app.state.memory,'sync_notes',slow_scan)
        thread=threading.Thread(target=lambda:client.post('/memory/sync',headers=AUTH));thread.start()
        try:
            assert started.wait(2)
            result=client.post('/chat/stream',headers=AUTH,json={'message':'Oi Cronos'})
            assert json.loads(result.text.splitlines()[-1])['type']=='result'
            assert not release.is_set()
        finally:release.set();thread.join(5)


def test_indexing_uses_short_transactions_and_cached_recall(settings,monkeypatch):
    memory=Memory(settings.vault)
    (settings.vault/'a.md').write_text('# Física\nEnergia e força.',encoding='utf-8')
    memory.sync_notes()
    def forbidden():raise AssertionError('No vault walk on every question')
    monkeypatch.setattr(memory,'_markdown_files',forbidden)
    assert 'Energia' in memory.recall('física',refresh=False)
    # Persisting a greeting also does not re-index unrelated notes.
    memory.record(uuid4(),'Oi','Olá',[])


def test_timing_history_keeps_failures_cancellations_and_out_of_order_updates():
    first,second=str(uuid4()),str(uuid4())
    common={'source':'voice','chat_ms':0}
    conversation_metrics.save_client({**common,'turn_id':first,'status':'waiting','sequence':1})
    conversation_metrics.save_client({**common,'turn_id':first,'status':'cancelled','sequence':3})
    conversation_metrics.save_client({**common,'turn_id':second,'status':'failed','sequence':2})
    conversation_metrics.save_client({**common,'turn_id':first,'status':'waiting','sequence':2})
    rows=conversation_metrics.read_client_history()
    assert [row['status'] for row in rows]==['cancelled','failed']
    assert conversation_metrics.read_client()['turn_id']==second
    assert all('response_ms' not in row for row in rows)  # No invented success timing.


def test_timing_history_retains_only_latest_200_turns():
    for i in range(203):conversation_metrics.save_client({'turn_id':str(i),'source':'text','chat_ms':i,'status':'completed'})
    rows=conversation_metrics.read_client_history()
    assert len(rows)==200 and rows[0]['turn_id']=='3' and rows[-1]['turn_id']=='202'


def test_silent_provider_uses_reserve_without_waiting_full_generation_budget(settings,monkeypatch):
    monkeypatch.setattr(evolution,'FIRST_REPLY_TIMEOUT_SECONDS',.02)
    monkeypatch.setattr(evolution,'read',lambda _: {'routing':{'enabled':True,'fallbacks':['reserve']}})
    monkeypatch.setattr(evolution,'provider_catalog',lambda _: [{'id':'reserve','configured':True}])
    cancelled=[]
    class Silent:
        async def reply(self,*args):
            try:await asyncio.sleep(30)
            finally:cancelled.append(True)
    class Reserve:
        async def reply(self,*args):return {'reply':'Resposta da reserva.','tool_calls':[],'topics':[]}
    monkeypatch.setattr(transport,'conversation_provider',lambda _: Reserve())
    async def run():
        return await asyncio.wait_for(evolution.ResilientProvider(replace(settings,provider_timeout=180),Silent()).reply('',[]),.5)
    assert asyncio.run(run())['provider_used']=='reserve'
    assert cancelled==[True]
