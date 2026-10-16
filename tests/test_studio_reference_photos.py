"""Reference photos are embedded without giving generated scripts a network channel."""
import asyncio
import base64
from dataclasses import replace
import io
from zipfile import ZipFile

import httpx
from PIL import Image
import pytest
from fastapi.testclient import TestClient

import cronos.studio.threed.reference_images as photos
from cronos.app import create_app
from cronos.studio.validation import reference_images
from test_backend import settings, AUTH
from test_studio import Builder

REAL_DOWNLOAD=photos.download
URL=sorted(reference_images())[0]


def test_download_only_accepts_exact_reference_urls_and_normalizes_images(monkeypatch):
    image=io.BytesIO();Image.new('RGB',(2000,1000),'#25445e').save(image,'PNG')
    requested=[]
    def respond(request):
        requested.append(str(request.url))
        return httpx.Response(200,content=image.getvalue(),headers={'content-type':'image/png'})
    client=httpx.AsyncClient
    monkeypatch.setattr(photos.httpx,'AsyncClient',lambda **kwargs:client(transport=httpx.MockTransport(respond),**kwargs))
    async def check():
        with pytest.raises(ValueError):await REAL_DOWNLOAD(URL+'&secret=private')
        assert not requested
        result=await REAL_DOWNLOAD(URL)
        picture=Image.open(io.BytesIO(base64.b64decode(result.split(',')[1])))
        assert picture.size==(1600,800) and picture.format=='JPEG'
        assert requested==[URL]
    asyncio.run(check())


@pytest.mark.parametrize('status,headers,body',[(302,{'location':'http://127.0.0.1/private'},b''),(200,{'content-type':'text/html'},b'<html>'),(200,{'content-type':'image/png'},b'not a png'),(200,{'content-type':'image/png'},b'x'*2_000_001)])
def test_redirect_invalid_or_oversized_reference_does_not_become_a_photo(monkeypatch,status,headers,body):
    client=httpx.AsyncClient
    monkeypatch.setattr(photos.httpx,'AsyncClient',lambda **kwargs:client(transport=httpx.MockTransport(lambda request:httpx.Response(status,headers=headers,content=body)),**kwargs))
    async def check():
        with pytest.raises((ValueError,OSError,httpx.HTTPError)):await REAL_DOWNLOAD(URL)
    asyncio.run(check())


def test_cache_reuses_photo_keeps_source_link_and_local_mode_disables_it(monkeypatch):
    calls=[]
    async def fixture(url):calls.append(url);return 'data:image/jpeg;base64,cGhvdG8='
    monkeypatch.setattr(photos,'download',fixture)
    html='<html><body><img src="'+URL+'"><a href="'+URL+'">Fonte</a></body></html>'
    async def check():
        bank=photos.ReferencePhotos()
        await bank.prepare(html);await bank.prepare(html)
        assert calls==[URL]
        output=bank.embed(html,online=True)
        assert 'src="data:image/jpeg;base64,cGhvdG8="' in output
        assert 'href="'+URL.replace('&','&amp;')+'"' in output
        offline=bank.embed(html,online=False)
        assert 'src="data:image/svg+xml;base64,' in offline
        assert 'cGhvdG8=' not in offline
    asyncio.run(check())


def test_preview_and_export_embed_photo_but_cannot_send_dynamic_remote_image_requests(settings,monkeypatch):
    image=io.BytesIO();Image.new('RGB',(40,30),'#25445e').save(image,'JPEG')
    data='data:image/jpeg;base64,'+base64.b64encode(image.getvalue()).decode()
    calls=[]
    async def fixture(url):calls.append(url);return data
    monkeypatch.setattr(photos,'download',fixture)
    with TestClient(create_app(settings,Builder())) as client:
        item=client.post('/studio/projects',headers=AUTH,json={'name':'Teste de fotos','category':'restaurante','create_from_template':True}).json()
        preview=client.post('/studio/projects/'+item['id']+'/preview',headers=AUTH).json()
        response=client.get(preview['url'])
        assert data in response.text and calls
        assert "img-src data: blob:;" in response.headers['content-security-policy']
        assert 'https://images.unsplash.com' not in response.headers['content-security-policy']
        count=len(calls)
        archive=client.get('/studio/projects/'+item['id']+'/export',headers=AUTH)
        with ZipFile(io.BytesIO(archive.content)) as package:
            assert data in package.read('site/index.html').decode()
            runtime=package.read('server.py').decode()
            assert "img-src 'self' data: blob:;" in runtime
        assert len(calls)==count
        client.app.state.engine.settings=replace(settings,privacy_mode='local')
        response=client.get(preview['url'])
        assert data not in response.text and len(calls)==count
