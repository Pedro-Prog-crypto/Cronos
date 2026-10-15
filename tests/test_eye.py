import shutil
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from test_backend import settings,AUTH
from cronos.app import create_app
from cronos import eye_runtime


def test_original_eye_document_assets_and_privacy_boundary(settings):
    with TestClient(create_app(settings)) as client:
        response=client.get('/world/view')
        assert response.status_code==200
        assert 'first-run-launcher' in response.text and 'key-setup' in response.text
        assert '/style.css' not in response.text
        assert client.get('/eye/cesium/Cesium.js').status_code==200
        assert 'camera=()' in response.headers['permissions-policy']
        assert "script-src 'self' 'unsafe-eval' blob:;" in response.headers['content-security-policy']
        assert "script-src 'self' 'wasm-unsafe-eval';" in client.get('/').headers['content-security-policy']
        assert client.post('/world/eye/heartbeat').status_code==401
        assert client.get('/api/setup/status').status_code==401
        assert client.app.state.eye.process is None


@pytest.mark.skipif(shutil.which('node') is None,reason='Node runtime unavailable')
def test_actual_packaged_service_auth_cookie_and_close(settings,tmp_path,monkeypatch):
    monkeypatch.setattr(eye_runtime,'STATE',tmp_path/'eye-state')
    with TestClient(create_app(settings)) as client:
        assert client.app.state.eye.process is None
        assert client.post('/world/eye/heartbeat',headers=AUTH).status_code==200
        response=client.get('/api/cronos/browser-config',headers=AUTH)
        assert response.status_code==200,response.text
        assert response.json()=={'googleApiKey':'','cesiumToken':''}
        process=client.app.state.eye.process
        assert process is not None and process.poll() is None
        # EventSource/images cannot attach Authorization. The scoped ticket works.
        status=client.get('/api/setup/status')
        assert status.status_code==200 and 'keys' in status.json()
        assert not any('value' in key for key in status.json()['keys'])
        assert client.post('/world/close',headers=AUTH).status_code==200
        assert process.poll() is not None and client.app.state.eye.process is None
        assert client.get('/api/setup/status').status_code==401
        assert client.post('/world/eye/heartbeat',headers=AUTH).status_code==200
        assert client.get('/api/cronos/browser-config',headers=AUTH).status_code==200
        assert client.app.state.eye.process.pid!=process.pid


def test_eye_local_mode_cannot_start_external_services(settings):
    with TestClient(create_app(replace(settings,privacy_mode='local'))) as client:
        assert client.post('/world/eye/heartbeat',headers=AUTH).status_code==403
        assert client.get('/api/cronos/browser-config',headers=AUTH).status_code==403
        assert client.app.state.eye.process is None


def test_map_streams_have_a_separate_bounded_budget_from_voice(settings):
    import asyncio
    from cronos.security import SecurityMiddleware
    async def run():
        gate=asyncio.Event();statuses=[]
        async def inner(scope,receive,send):
            if scope['path'].startswith(('/api/','/static/','/chat/')):await gate.wait()
            await send({'type':'http.response.start','status':200,'headers':[]})
            await send({'type':'http.response.body','body':b'ok'})
        middleware=SecurityMiddleware(inner,settings)
        async def request(path):
            result=[]
            async def receive():return {'type':'http.request','body':b'','more_body':False}
            async def send(event):
                if event['type']=='http.response.start':result.append(event['status'])
            await middleware({'type':'http','scheme':'http','method':'GET','path':path,'client':('127.0.0.1',1234),'headers':[(b'host',b'127.0.0.1'),(b'authorization',b'Bearer test-token')]},receive,send)
            return result[0]
        tasks=[asyncio.create_task(request('/api/stream')) for _ in range(13)]
        assets=[asyncio.create_task(request('/static/asset')) for _ in range(5)]
        await asyncio.sleep(.01)
        assert middleware.active==0
        assert middleware.eye_active==12
        assert await request('/voice/status')==200
        normal=[asyncio.create_task(request('/chat/hold')) for _ in range(4)]
        await asyncio.sleep(.01)
        assert await request('/world/close')==200
        assert await request('/world/eye/heartbeat')==200
        assert await request('/voice/status')==429
        gate.set();statuses=await asyncio.gather(*tasks)
        assert await asyncio.gather(*assets)==[200]*5
        assert await asyncio.gather(*normal)==[200]*4
        assert statuses.count(200)==12 and statuses.count(429)==1
        assert middleware.active==middleware.eye_active==0
    asyncio.run(run())
