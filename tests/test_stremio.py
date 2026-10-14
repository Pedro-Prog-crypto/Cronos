import asyncio
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from test_backend import settings, AUTH
from cronos.app import create_app
from cronos import stremio


def test_stremio_links_are_narrow_and_use_empty_hostname():
    from urllib.parse import urlsplit,unquote
    movie=stremio.deeplink(stremio.Selection(id='tt0133093'))
    assert movie=='stremio:///detail/movie/tt0133093/tt0133093'
    episode=stremio.deeplink(stremio.Selection(id='tt0944947',kind='series',season=2,episode=3))
    assert not urlsplit(episode).netloc
    assert unquote(urlsplit(episode).path)=='/detail/series/tt0944947/tt0944947:2:3'
    with pytest.raises(ValueError):stremio.Selection(id='file:///etc/passwd')
    with pytest.raises(ValueError):stremio.deeplink(stremio.Selection(id='tt0133093',season=1,episode=1))
    with pytest.raises(ValueError):stremio.deeplink(stremio.Selection(id='tt0944947',kind='series',season=1))


def test_episode_metadata_checked_before_windows_launch(monkeypatch):
    calls=[]
    async def catalog(path):
        calls.append(path)
        return {'meta':{'videos':[{'season':2,'episode':3}]}}
    monkeypatch.setattr(stremio,'get_json',catalog)
    opened=[]
    result=asyncio.run(stremio.open_item(stremio.Selection(id='tt0944947',kind='series',season=2,episode=3),'win32',opened.append))
    assert len(opened)==1 and opened[0].endswith('tt0944947%3A2%3A3')
    assert result['launch_requested'] and not result['played']
    with pytest.raises(ValueError,match='não confirmou'):
        asyncio.run(stremio.open_item(stremio.Selection(id='tt0944947',kind='series',season=2,episode=99),'win32',opened.append))
    assert len(opened)==1
    with pytest.raises(ValueError,match='Windows'):
        asyncio.run(stremio.open_item(stremio.Selection(id='tt0133093'),'linux',opened.append))


def test_search_returns_metadata_only_and_keeps_episode(monkeypatch):
    stremio.CACHE.clear();paths=[]
    async def catalog(path):
        paths.append(path)
        return {'metas':[{'id':'tt0944947','name':'Game of Thrones','releaseInfo':'2011–2019'},{'id':'javascript:bad','name':'Invalid'}]}
    monkeypatch.setattr(stremio,'get_json',catalog)
    result=asyncio.run(stremio.search(stremio.Search(query='Game of Thrones',kind='series',season=2,episode=3)))
    assert len(result['items'])==1 and result['episode']==3 and not result['played']
    assert paths==['/catalog/series/top/search=Game%20of%20Thrones.json']
    asyncio.run(stremio.search(stremio.Search(query='Game of Thrones',kind='series')))
    assert len(paths)==1


def test_routes_auth_permissions_and_windows_mock(settings,monkeypatch):
    opened=[]
    async def search(body):return {'items':[],'query':body.query}
    monkeypatch.setattr(stremio,'search',search)
    monkeypatch.setattr(stremio.os,'startfile',opened.append,raising=False)
    with TestClient(create_app(settings,windows_platform='win32')) as client:
        assert client.post('/stremio/open',json={'id':'tt0133093'}).status_code==401
        assert client.post('/stremio/open',headers=AUTH,json={'id':'https://evil.invalid'}).status_code==422
        assert client.post('/stremio/search',headers=AUTH,json={'query':'Matrix'}).json()['query']=='Matrix'
        response=client.post('/stremio/open',headers=AUTH,json={'id':'tt0133093'})
        assert response.status_code==200,response.text
        assert opened==['stremio:///detail/movie/tt0133093/tt0133093']
        client.app.state.panels.preferences.apps_enabled=False
        assert client.post('/stremio/open',headers=AUTH,json={'id':'tt0133093'}).status_code==403
    with TestClient(create_app(replace(settings,privacy_mode='local'))) as client:
        assert client.post('/stremio/search',headers=AUTH,json={'query':'Matrix'}).status_code==403
