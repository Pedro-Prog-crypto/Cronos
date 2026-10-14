import asyncio
import json
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos import gemini_live
from cronos.reply_stream import ready_reply,reply_sink,deliver
from cronos.providers import ProviderError
from test_backend import settings,AUTH
import pytest


@pytest.mark.parametrize('raw',[
    '{"reply":"action","tool_calls":[]}',
    '{"tool_calls":[{"name":"execute"}],"reply":"Executed",',
    '{"tool_calls":[],"reply":"unfinished',
    '{"tool_calls":[],"reply":"Text"garbage',
    '{"tool_calls":[],"reply":"   ",',
])
def test_unsafe_or_incomplete_prefix_is_not_spoken(raw):assert ready_reply(raw) is None


def test_prefix_handles_escaped_text_without_waiting_for_topics():
    prefix=json.dumps({'tool_calls':[],'reply':'Texto com "aspas", } e linha\nseguinte'})[:-1]+',"topics":['
    assert ready_reply(prefix)=='Texto com "aspas", } e linha\nseguinte'


def test_live_delivers_complete_reply_before_memory_metadata(settings):
    emitted=[]
    prefix='{"tool_calls":[],"reply":"Resposta completa.",'
    class Session:
        async def send_client_content(self,**kwargs):pass
        async def receive(self):
            yield NS(server_content=NS(output_transcription=NS(text=prefix),turn_complete=False))
            assert emitted==['Resposta completa.']
            yield NS(server_content=NS(output_transcription=NS(text='"topics":[{"title":"Tema","summary":"Resumo"}]}'),turn_complete=True))
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):pass
    async def run():
        async def sink(text):emitted.append(text)
        token=reply_sink.set(sink)
        try:return await gemini_live.turn(NS(aio=NS(live=NS(connect=lambda **kw:Connection()))),settings.gemini_live_model,'persona',[{'role':'user','content':'Pergunta'}])
        finally:reply_sink.reset(token)
    result=asyncio.run(run())
    assert result['topics'][0]['title']=='Tema'


def test_stream_delivers_reply_then_final_and_saves_memory(settings):
    class Provider:
        async def reply(self,*args):
            await deliver('Sócrates foi um filósofo.')
            await asyncio.sleep(.01)
            return {'tool_calls':[],'reply':'Sócrates foi um filósofo.','topics':[{'title':'Sócrates','summary':'Filósofo grego.'}]}
    with TestClient(create_app(settings,Provider())) as client:
        assert client.post('/chat/stream',json={'message':'Olá'}).status_code==401
        r=client.post('/chat/stream',headers=AUTH,json={'message':'Quem foi Sócrates?'})
        events=[json.loads(line) for line in r.text.splitlines()]
        assert [e['type'] for e in events]==['reply','result']
        result=events[1]['result']
        assert result['reply']==events[0]['reply']
        assert client.get('/conversations/'+result['session_id'],headers=AUTH).json()['messages'][-1]['content']==result['reply']


def test_stream_errors_do_not_retry_or_lose_status(settings):
    class Provider:
        calls=0
        async def reply(self,*args):
            self.calls+=1
            raise ProviderError('Limite do provedor',429)
    provider=Provider()
    with TestClient(create_app(settings,provider)) as client:
        r=client.post('/chat/stream',headers=AUTH,json={'message':'Olá'})
        event=json.loads(r.text)
        assert event['type']=='error' and event['status']==429 and provider.calls==1


def test_intro_requires_empty_tools_and_safely_decodes_partial_string():
    from cronos.reply_stream import ready_intro
    text='Sócrates foi um filósofo grego. Ele fez muitas perguntas.'
    raw=json.dumps({'tool_calls':[],'reply':text},ensure_ascii=False)
    partial=raw[:raw.index('Ele')+3]
    assert ready_intro(partial)=='Sócrates foi um filósofo grego. '
    assert ready_intro(partial.replace('"tool_calls": []','"tool_calls": [{"name":"execute"}]')) is None
    assert ready_intro('untrusted '+partial) is None
    assert ready_intro('{"tool_calls":[],"reply":"Muito curto') is None


def test_stream_intro_precedes_complete_reply(settings):
    from cronos.reply_stream import deliver_intro
    class Provider:
        async def reply(self,*args):
            await deliver_intro('Sócrates foi um filósofo grego. ')
            await deliver('Sócrates foi um filósofo grego. Questionava ideias.')
            return {'tool_calls':[],'reply':'Sócrates foi um filósofo grego. Questionava ideias.','topics':[]}
    with TestClient(create_app(settings,Provider())) as client:
        response=client.post('/chat/stream',headers=AUTH,json={'message':'Quem foi Sócrates?'})
        events=[json.loads(line) for line in response.text.splitlines()]
        assert [e['type'] for e in events]==['intro','reply','result']
        assert events[1]['reply'].startswith(events[0]['reply'])


def test_network_delivers_intro_before_provider_finishes(settings):
    import socket,threading,time
    import httpx,uvicorn
    from cronos.reply_stream import deliver_intro
    release=threading.Event();finished=threading.Event()
    class Provider:
        async def reply(self,*args):
            await deliver_intro('Sócrates foi um filósofo grego. ')
            await asyncio.to_thread(release.wait,3)
            finished.set()
            return {'tool_calls':[],'reply':'Sócrates foi um filósofo grego. Questionava ideias.','topics':[]}
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(create_app(settings,Provider()),log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:
        until=time.monotonic()+5
        while not server.started and time.monotonic()<until:time.sleep(.01)
        assert server.started
        with httpx.Client(timeout=5) as client:
            with client.stream('POST',f'http://127.0.0.1:{port}/chat/stream',headers=AUTH,json={'message':'Quem foi Sócrates?'}) as response:
                lines=response.iter_lines();first=json.loads(next(lines))
                assert first['type']=='intro' and not finished.is_set()
                release.set()
                assert json.loads(next(lines))['type']=='result'
    finally:
        release.set();server.should_exit=True;thread.join(5);sock.close()


def test_closing_stream_cancels_pending_generation(settings):
    import socket,threading,time
    import httpx,uvicorn
    from cronos.reply_stream import deliver_intro
    cancelled=threading.Event()
    class Provider:
        async def reply(self,*args):
            try:
                await deliver_intro('Uma resposta inicial completa. ')
                await asyncio.sleep(30)
            finally:cancelled.set()
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(create_app(settings,Provider()),log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:
        until=time.monotonic()+5
        while not server.started and time.monotonic()<until:time.sleep(.01)
        assert server.started
        with httpx.Client(timeout=5) as client:
            with client.stream('POST',f'http://127.0.0.1:{port}/chat/stream',headers=AUTH,json={'message':'Pergunta'}) as response:
                assert json.loads(next(response.iter_lines()))['type']=='intro'
            assert cancelled.wait(2), 'ESC/disconnect must not leave Gemini running'
    finally:
        server.should_exit=True;thread.join(5);sock.close()


def test_short_intro_does_not_wait_for_answer_to_finish():
    from cronos.reply_stream import ready_intro
    assert ready_intro('{"tool_calls":[],"reply":"Sim. Ainda estou') == 'Sim. '
    assert ready_intro('{"tool_calls":[],"reply":"Não. Explico') == 'Não. '
    assert ready_intro('{"tool_calls":[{"name":"execute"}],"reply":"Sim. Depois') is None
    assert ready_intro('{"tool_calls":[],"reply":"...') is None


def test_long_first_sentence_can_start_at_word_boundary():
    from cronos.reply_stream import ready_intro
    text='A filosofia examina as ideias que orientam nossas escolhas e ajuda a avaliar os argumentos com cuidado e clareza'
    raw=json.dumps({'tool_calls':[],'reply':text},ensure_ascii=False)[:-2]
    intro=ready_intro(raw)
    assert intro and text.startswith(intro) and len(intro)<=80 and intro.endswith(' ')
