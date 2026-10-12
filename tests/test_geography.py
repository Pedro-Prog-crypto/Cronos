from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos.geography import Places
from test_backend import AUTH, settings


def test_world_search_privacy_mode_and_query_bounds(settings):
    with TestClient(create_app(replace(settings,privacy_mode='local'))) as client:
        assert client.get('/world/places?q=Paris',headers=AUTH).status_code==403
    with TestClient(create_app(settings)) as client:
        assert client.get('/world/places?q=a',headers=AUTH).status_code==422


def test_world_search_fixed_endpoint_worldwide_and_cache(monkeypatch):
    import asyncio
    calls=[]
    class Response:
        content=b'{}'
        def raise_for_status(self):pass
        def json(self):return [{'display_name':'Aéroport Charles de Gaulle, France','lat':'49.0097','lon':'2.5479'}]
    class Client:
        def __init__(self,**kwargs):assert kwargs['follow_redirects'] is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):calls.append((url,kwargs));return Response()
    monkeypatch.setattr('cronos.geography.httpx.AsyncClient',Client)
    async def run():
        places=Places();a=await places.search('aeroporto Charles de Gaulle');b=await places.search('aeroporto Charles de Gaulle')
        assert a==b and a[0]['lat']==49.0097
    asyncio.run(run())
    assert len(calls)==1 and calls[0][0]=='https://nominatim.openstreetmap.org/search'


def test_map_context_has_scoped_worker_permissions(settings):
    with TestClient(create_app(settings)) as client:
        root=client.get('/')
        world=client.get('/world/view')
        assert world.status_code==200
        assert "wasm-unsafe-eval" not in root.headers['content-security-policy']
        assert "script-src 'self';" in root.headers['content-security-policy']
        assert "'wasm-unsafe-eval'" in world.headers['content-security-policy']
        assert "'unsafe-eval'" not in world.headers['content-security-policy']
        assert world.headers['x-frame-options']=='SAMEORIGIN'
        assert 'microphone=()' in world.headers['permissions-policy']
        assert client.get('/ui/cesium/Workers/createGeometry.js').status_code==200


def test_voice_requires_explicit_model(settings):
    class ForbiddenFish:
        def __call__(self):raise AssertionError('No model was selected')
    with TestClient(create_app(replace(settings,fish_key='dummy',fish_model=''),fish_factory=ForbiddenFish())) as client:
        assert client.get('/status',headers=AUTH).json()['fish_speech_configured'] is False
        assert client.post('/voice/speech',headers=AUTH,json={'text':'Olá'}).status_code==503
        assert client.post('/voice/stream',headers=AUTH,json={'text':'Olá'}).status_code==503


def test_s2_pro_is_allowed_when_explicitly_selected(settings):
    calls=[]
    class Fish:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        @property
        def tts(self):return self
        async def convert(self,**kwargs):calls.append(kwargs);return b'audio'
    with TestClient(create_app(replace(settings,fish_key='dummy',fish_model='s2-pro'),fish_factory=Fish)) as client:
        assert client.get('/status',headers=AUTH).json()['fish_speech_configured'] is True
        assert client.post('/voice/speech',headers=AUTH,json={'text':'Olá'}).status_code==200
    assert calls[0]['model']=='s2-pro'
