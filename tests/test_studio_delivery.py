import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from cronos.providers import Gemini,ProviderError
from cronos.studio.delivery import bundle,string_prefix
from cronos.studio.store import Store
from cronos.studio.provider_pool import ProviderPool
from cronos.studio.validation import parse_bundle
from test_backend import settings

CLIENT=httpx.AsyncClient
OUTPUT={'summary':'Uma composição específica.','files':{'index.html':'<html>Loja AURA \\" beleza</html>','styles.css':'body{color:#123}','app.js':'console.log("olá");'}}
RAW=json.dumps(OUTPUT,ensure_ascii=False)
PAYLOAD=json.dumps({'request':'Crie uma loja de maquiagem de R$ 4.000.'})


def setup(tmp_path,adapters):
    store=Store(tmp_path/'vault')
    project=store.new({'name':'AURA','provider':next(iter(adapters)),'category':'loja'})
    pool=pool_for(store,project,adapters)
    return store,project,pool


def pool_for(store,project,adapters):
    project['provider']=next(iter(adapters))
    return ProviderPool(project,[{'id':key,'configured':True} for key in adapters],adapters.__getitem__,store.event,{},timeout=1)


def sse(text,finish):
    halfway=len(text)//2
    pieces=[{'candidates':[{'content':{'parts':[{'text':text[:halfway]}]}}]},
            {'candidates':[{'content':{'parts':[{'text':text[halfway:]}]},'finishReason':finish}],'usageMetadata':{'candidatesTokenCount':12}}]
    return httpx.Response(200,headers={'content-type':'text/event-stream'},content=''.join('data: '+json.dumps(p)+'\n\n' for p in pieces))


def test_real_gemini_sse_truncation_is_completed_without_losing_prefix(settings,tmp_path,monkeypatch):
    cut=RAW.index('beleza')+2;calls=[]
    def handle(request):
        assert ':streamGenerateContent' in request.url.path and request.url.params['alt']=='sse'
        data=json.loads(request.content);calls.append(data)
        if len(calls)==1:return sse(RAW[:cut],'MAX_TOKENS')
        content=json.loads(data['contents'][0]['parts'][0]['text'])
        assert content['received_prefix']==RAW[:cut]
        return sse(json.dumps({'continuation':RAW[cut:]}),'STOP')
    monkeypatch.setattr('cronos.providers.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    provider=Gemini(replace(settings,gemini_key='fixture-only',gemini_transport='rest'))
    store,project,pool=setup(tmp_path,{'gemini':provider})
    result=asyncio.run(bundle(pool,'Build site',PAYLOAD,store,project))
    assert json.loads(result['reply'])==OUTPUT and len(calls)==2
    assert pool.current=='gemini' and not pool.failures
    assert any(e['phase']=='checkpoint' for e in project['events'])
    assert all('beleza' not in e['text'] for e in project['events'])


def test_quota_during_continuation_passes_saved_prefix_to_reserve(tmp_path):
    cut=len(RAW)//2
    class Primary:
        calls=0
        async def reply(self,system,messages):
            self.calls+=1
            if self.calls==1:raise ProviderError('cut',502,kind='output_limit',partial_output=RAW[:cut])
            raise ProviderError('quota',429)
    class Reserve:
        async def reply(self,system,messages):
            assert json.loads(messages[0]['content'])['received_prefix']==RAW[:cut]
            return {'reply':json.dumps({'continuation':RAW[cut:]})}
    primary=Primary();store,project,pool=setup(tmp_path,{'gemini':primary,'mistral':Reserve()})
    result=asyncio.run(bundle(pool,'Build',PAYLOAD,store,project))
    assert json.loads(result['reply'])==OUTPUT and pool.current=='mistral' and primary.calls==2


def test_explicit_retry_after_restart_resumes_private_checkpoint(tmp_path):
    cut=len(RAW)//2
    class Interrupted:
        calls=0
        async def reply(self,*args):
            self.calls+=1
            if self.calls==1:raise ProviderError('cut',502,kind='output_interrupted',partial_output=RAW[:cut])
            raise ProviderError('down',503)
    store,project,pool=setup(tmp_path,{'gemini':Interrupted()})
    with pytest.raises(ProviderError):asyncio.run(bundle(pool,'Build',PAYLOAD,store,project))
    assert 'raw' not in json.dumps(store.get(project['id']))
    assert not store.history(project)  # No partial code can become a revision.
    store=Store(tmp_path/'vault');project=store.get(project['id'])
    class Resume:
        async def reply(self,system,messages):
            assert json.loads(messages[0]['content'])['received_prefix']==RAW[:cut]
            return {'reply':json.dumps({'continuation':RAW[cut:]})}
    result=asyncio.run(bundle(pool_for(store,project,{'mistral':Resume()}),'Build',PAYLOAD,store,project))
    assert json.loads(result['reply'])==OUTPUT
    store.clear_generation_draft(project)
    with store.connect() as db:assert db.execute('SELECT count(*) FROM generation_drafts').fetchone()[0]==0


def test_other_request_does_not_inherit_partial_code(tmp_path):
    class Provider:
        calls=0
        async def reply(self,system,messages):
            self.calls+=1
            if self.calls==1:raise ProviderError('cut',502,kind='output_limit',partial_output=RAW[:20])
            if self.calls==2:raise ProviderError('down',503)
            assert messages[0]['content']=='{"request":"A different site"}'
            return {'reply':RAW}
    provider=Provider();store,project,pool=setup(tmp_path,{'gemini':provider})
    with pytest.raises(ProviderError):asyncio.run(bundle(pool,'Build',PAYLOAD,store,project))
    result=asyncio.run(bundle(pool_for(store,project,{'gemini':provider}),'Build','{"request":"A different site"}',store,project))
    assert json.loads(result['reply'])==OUTPUT


def test_retry_can_resume_the_validation_repair_stage_of_same_request(tmp_path):
    repaired=json.dumps({'request':'same site','validation_error':'Fix spacing'})
    cut=len(RAW)//2
    class Interrupted:
        calls=0
        async def reply(self,*args):
            self.calls+=1
            if self.calls==1:raise ProviderError('cut',502,kind='output_limit',partial_output=RAW[:cut])
            raise ProviderError('offline',503)
    store,project,pool=setup(tmp_path,{'gemini':Interrupted()})
    with pytest.raises(ProviderError):asyncio.run(bundle(pool,'Build',repaired,store,project,key_payload=PAYLOAD))
    class Resume:
        async def reply(self,system,messages):
            data=json.loads(messages[0]['content'])
            assert data['original_request']['validation_error']=='Fix spacing'
            return {'reply':json.dumps({'continuation':RAW[cut:]})}
    result=asyncio.run(bundle(pool_for(store,project,{'mistral':Resume()}),'Build',PAYLOAD,store,project,key_payload=PAYLOAD))
    assert json.loads(result['reply'])==OUTPUT


def test_final_repeated_closing_brace_is_valid_continuation(tmp_path):
    class Provider:
        calls=0
        async def reply(self,*args):
            self.calls+=1
            if self.calls==1:raise ProviderError('cut',502,kind='output_limit',partial_output=RAW[:-1])
            return {'reply':json.dumps({'continuation':RAW[-1:]})}
    store,project,pool=setup(tmp_path,{'gemini':Provider()})
    result=asyncio.run(bundle(pool,'Build',PAYLOAD,store,project))
    assert json.loads(result['reply'])==OUTPUT


@pytest.mark.parametrize('value',['abc\\','abc\\u00','abc\\ud8'])
def test_partial_continuation_does_not_guess_incomplete_escape(value):
    assert string_prefix('{"continuation":"'+value)=='abc'


def test_stream_quota_remains_classified_without_echoing_body(settings,monkeypatch):
    def handle(request):return httpx.Response(429,json={'error':{'message':'PRIVATE_ACCOUNT_DATA'}})
    monkeypatch.setattr('cronos.providers.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    with pytest.raises(ProviderError) as failure:asyncio.run(Gemini(replace(settings,gemini_key='quota-fixture-only',gemini_transport='rest')).reply_structured('Site',[]))
    assert failure.value.status==429 and 'PRIVATE_ACCOUNT_DATA' not in str(failure.value)


def test_cancelled_stream_keeps_received_bytes_without_starting_a_reserve(settings,tmp_path,monkeypatch):
    received=asyncio.Event();prefix='{"files":{"index.html":"'+('x'*9000)
    class Streaming(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield ('data: '+json.dumps({'candidates':[{'content':{'parts':[{'text':prefix}]}}]})+'\n\n').encode()
            await asyncio.Event().wait()
    def handle(request):return httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Streaming())
    monkeypatch.setattr('cronos.providers.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    provider=Gemini(replace(settings,gemini_key='cancel-fixture-only',gemini_transport='rest'))
    class Reserve:
        async def reply(self,*args):raise AssertionError('Cancel must never call a reserve')
    store,project,pool=setup(tmp_path,{'gemini':provider,'reserve':Reserve()})
    save=store.save_generation_draft
    def snapshot(*args):save(*args);received.set()
    store.save_generation_draft=snapshot
    async def run():
        task=asyncio.create_task(bundle(pool,'Build',PAYLOAD,store,project))
        await asyncio.wait_for(received.wait(),1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(run())
    with store.connect() as db:
        saved=json.loads(db.execute('SELECT payload FROM generation_drafts WHERE project=?',(project['id'],)).fetchone()[0])
    assert saved['raw']==prefix and not store.history(project)


@pytest.mark.parametrize('failure',['network','timeout'])
def test_stream_disconnect_or_deadline_continues_received_code(settings,tmp_path,monkeypatch,failure):
    cut=len(RAW)//2;calls=[]
    class Streaming(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield ('data: '+json.dumps({'candidates':[{'content':{'parts':[{'text':RAW[:cut]}]}}]})+'\n\n').encode()
            if failure=='network':raise httpx.ReadError('PRIVATE connection details')
            await asyncio.Event().wait()
    def handle(request):
        calls.append(request)
        if len(calls)==1:return httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Streaming())
        content=json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])
        assert content['received_prefix']==RAW[:cut]
        return sse(json.dumps({'continuation':RAW[cut:]}),'STOP')
    monkeypatch.setattr('cronos.providers.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    provider=Gemini(replace(settings,gemini_key=failure+'-fixture-only',gemini_transport='rest'))
    store,project,pool=setup(tmp_path,{'gemini':provider});pool.timeout=.04
    result=asyncio.run(bundle(pool,'Build',PAYLOAD,store,project))
    assert json.loads(result['reply'])==OUTPUT and len(calls)==2
    assert all('PRIVATE' not in event['text'] for event in project['events'])
