import asyncio,json,socket,threading,time
from dataclasses import replace
import httpx,uvicorn
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos.fish_legacy import stream_json
from test_backend import settings,AUTH


def test_legacy_stream_exposes_first_bytes_without_consuming_rest():
    entered=[]
    class Bytes(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'\0\1'*20
            entered.append('rest')
            yield b'\2\3'*20
    requests=[]
    def respond(request):requests.append(request);return httpx.Response(200,stream=Bytes())
    async def run():
        iterator=stream_json('test-key',text='Olá',reference_id='same-voice',format='pcm',transport=httpx.MockTransport(respond))
        try:
            assert await anext(iterator)==b'\0\1'*20 and entered==[]
            assert await anext(iterator)==b'\2\3'*20
        finally:await iterator.aclose()
    asyncio.run(run())
    request=requests[0];payload=json.loads(request.content)
    assert request.headers['model']=='s2.1-pro-free' and payload['format']=='pcm'
    assert payload['sample_rate']==24000 and payload['reference_id']=='same-voice'


def test_pcm_endpoint_is_authenticated_and_preserves_billing_error(settings,monkeypatch):
    from cronos import fish_legacy
    from fishaudio.exceptions import APIError
    async def failure(*args,**kw):
        raise APIError(402,'private provider body')
        yield b''
    monkeypatch.setattr(fish_legacy,'stream_json',failure)
    with TestClient(create_app(replace(settings,fish_model='s2.1-pro-free',fish_key='test-fish'))) as client:
        assert client.post('/voice/pcm',json={'text':'Olá'}).status_code==401
        response=client.post('/voice/pcm',headers=AUTH,json={'text':'Olá'})
        assert response.status_code==502 and '402' in response.text and 'private provider body' not in response.text


def test_network_pcm_does_not_wait_for_complete_synthesis(settings,monkeypatch):
    from cronos import fish_legacy
    release=threading.Event();closed=threading.Event()
    async def synthesize(key,**kw):
        assert kw['format']=='pcm' and kw['reference_id']==(settings.fish_reference or None)
        try:
            yield b'\0\1'*100
            await asyncio.to_thread(release.wait,3)
            yield b'\0\2'*100
        finally:closed.set()
    monkeypatch.setattr(fish_legacy,'stream_json',synthesize)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(create_app(replace(settings,fish_model='s2.1-pro-free',fish_key='test-fish')),log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:
        until=time.monotonic()+5
        while not server.started and time.monotonic()<until:time.sleep(.01)
        assert server.started
        with httpx.Client(timeout=5) as client:
            with client.stream('POST',f'http://127.0.0.1:{port}/voice/pcm',headers=AUTH,json={'text':'Olá'}) as response:
                assert response.status_code==200 and response.headers['X-PCM-Sample-Rate']=='24000'
                chunks=response.iter_bytes();assert next(chunks)==b'\0\1'*100 and not closed.is_set()
                release.set();assert b''.join(chunks)==b'\0\2'*100
    finally:release.set();server.should_exit=True;thread.join(5);sock.close()
