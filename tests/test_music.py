import json
from dataclasses import replace
import httpx
from fastapi.testclient import TestClient
from test_backend import settings, AUTH
from cronos.app import create_app
from cronos.music import video_id, public_results


def test_video_url_validation():
    assert video_id('https://youtu.be/abcdefghijk') == 'abcdefghijk'
    assert video_id('https://www.youtube.com/watch?v=abcdefghijk') == 'abcdefghijk'
    assert video_id('https://youtube.com.evil.invalid/watch?v=abcdefghijk') is None
    assert video_id('http://127.0.0.1/secret') is None
    assert video_id('https://youtube.com/watch?v=../passwd') is None


def test_public_search_metadata_not_other_video_ids():
    data = {'contents': [{'videoRenderer': {'videoId': 'abcdefghijk', 'title': {'runs': [{'text': 'Música & cantor'}]}}},
                         {'adRenderer': {'videoId': '12345678901'}},
                         {'videoRenderer': {'videoId': 'abcdefghijk', 'title': {'simpleText': 'repetido'}}}]}
    assert public_results('var ytInitialData = '+json.dumps(data)+';') == [{'id': 'abcdefghijk', 'title': 'Música & cantor'}]
    assert public_results('consent form') == []


def test_music_auth_local_mode_and_no_network_for_url(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/music/search', params={'query': 'uma música'}).status_code == 401
        result = client.get('/music/search', headers=AUTH, params={'query': 'https://youtu.be/abcdefghijk'})
        assert result.status_code == 200
        assert result.json()['tracks'][0]['id'] == 'abcdefghijk'
        assert 'https://www.youtube-nocookie.com' in client.get('/').headers['content-security-policy']
    with TestClient(create_app(replace(settings, privacy_mode='local'))) as client:
        assert client.get('/music/search', headers=AUTH, params={'query': 'https://youtu.be/abcdefghijk'}).status_code == 403


def test_music_search_and_graceful_provider_failure(settings, monkeypatch):
    monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)
    monkeypatch.setattr('cronos.music.metadata_search',lambda query:[])
    from cronos.music import CACHE
    CACHE.clear()
    original = httpx.AsyncClient
    requests=[]
    def handle(request):
        requests.append(request)
        if 'mix' in request.url.params.get('search_query',''):
            return httpx.Response(403, text='blocked')
        body='var ytInitialData = '+json.dumps({'videoRenderer':{'videoId':'abcdefghijk','title':{'simpleText':'Song'}}})+';'
        return httpx.Response(200,text=body)
    monkeypatch.setattr('cronos.music.httpx.AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handle),trust_env=False,**kwargs))
    with TestClient(create_app(settings)) as client:
        result=client.get('/music/search',headers=AUTH,params={'query':'Song'})
        assert result.json()['tracks']==[{'id':'abcdefghijk','title':'Song'}]
        result=client.get('/music/search',headers=AUTH,params={'query':'Cantor','similar':True})
        assert result.json()['tracks']==[]
        assert 'cole o link' in result.json()['message']
        assert requests[-1].url.host=='www.youtube.com'
        assert requests[-1].url.params['search_query']=='Cantor mix músicas parecidas'


def test_playback_commands_are_not_knowledge_notes():
    from cronos.memory_policy import knowledge_topics
    topics=[{'title':'Música','content':'Comando de tocar.'}]
    assert knowledge_topics('Kronos, colocar música Evidências',topics)==[]
    assert knowledge_topics('Kronos, pausar música',topics)==[]
    assert knowledge_topics('O que é uma frequência de 432 Hz?',topics)==topics


def test_metadata_fallback_when_public_page_changes(monkeypatch):
    import asyncio
    from cronos.music import search_music, CACHE
    CACHE.clear()
    monkeypatch.delenv('YOUTUBE_API_KEY',raising=False)
    original=httpx.AsyncClient
    monkeypatch.setattr('cronos.music.httpx.AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='no initial data')),trust_env=False,**kw))
    calls=[]
    def fallback(query):
        calls.append(query)
        return [{'id':'abcdefghijk','title':'Nada pra Fazer · clipe'}]
    monkeypatch.setattr('cronos.music.metadata_search',fallback)
    result=asyncio.run(search_music('Nada pra Fazer',video=True))
    assert result['tracks'][0]['id']=='abcdefghijk'
    assert calls==['Nada pra Fazer clipe oficial']
    assert result['message'] is None


def test_native_stream_selection_original_audio_and_light_video():
    from cronos.music import select_media, allowed_stream
    info={'title':'Clipe','formats':[
        {'url':'https://rr1.googlevideo.com/video480','protocol':'https','vcodec':'avc1','acodec':'none','height':480,'fps':30,'ext':'mp4'},
        {'url':'https://rr1.googlevideo.com/video1080','protocol':'https','vcodec':'av01','acodec':'none','height':1080,'fps':60,'ext':'mp4'},
        {'url':'https://rr1.googlevideo.com/original','protocol':'https','vcodec':'none','acodec':'mp4a','abr':128,'ext':'m4a','language_preference':10},
        {'url':'https://rr1.googlevideo.com/dub','protocol':'https','vcodec':'none','acodec':'mp4a','abr':160,'ext':'m4a','language_preference':-1}]}
    result=select_media(info,True)
    assert result['video_url'].endswith('video480') and result['audio_url'].endswith('original')
    assert select_media(info,False)['video_url'] is None
    assert not allowed_stream('https://googlevideo.com.evil.invalid/audio')
    assert not allowed_stream('http://127.0.0.1/private')
    assert not allowed_stream('https://user:password@rr1.googlevideo.com/audio')
    import pytest
    with pytest.raises(ValueError):select_media({**info,'availability':'private'},True)


def test_native_resolver_auth_validation_and_no_external_redirect(settings,monkeypatch):
    from cronos.music import MEDIA_CACHE
    MEDIA_CACHE.clear();calls=[]
    def resolve(ident,clip):
        calls.append((ident,clip));return {'audio_url':'https://rr1.googlevideo.com/original','video_url':None,'title':'Nada pra Fazer'}
    monkeypatch.setattr('cronos.music.resolve_native',resolve)
    with TestClient(create_app(settings)) as client:
        assert client.get('/music/resolve?id=abcdefghijk').status_code==401
        assert client.get('/music/resolve?id=../private',headers=AUTH).status_code==422
        result=client.get('/music/resolve?id=abcdefghijk&native=true',headers=AUTH)
        assert result.status_code==200 and 'location' not in result.headers
        assert result.json()['title']=='Nada pra Fazer'
        client.get('/music/resolve?id=abcdefghijk&native=true',headers=AUTH)
        assert len(calls)==1
        assert 'https://*.googlevideo.com' in client.get('/').headers['content-security-policy']


def test_official_internal_player_does_not_wait_for_extraction(settings,monkeypatch):
    def forbidden(*args):raise AssertionError('Default player must not extract a temporary CDN URL')
    monkeypatch.setattr('cronos.music.resolve_native',forbidden)
    with TestClient(create_app(settings)) as client:
        result=client.get('/music/resolve?id=abcdefghijk&video=true',headers=AUTH)
        assert result.json()=={'player':'official','id':'abcdefghijk','video':True}
        frame=client.get('/music/player?id=abcdefghijk')
        assert frame.status_code==200 and 'music-player.js' in frame.text
        assert 'x-frame-options' not in frame.headers
        assert 'frame-ancestors http://127.0.0.1 http://localhost' in frame.headers['content-security-policy']
        assert frame.headers['referrer-policy']=='strict-origin-when-cross-origin'
        assert 'https://www.youtube.com' in frame.headers['content-security-policy']
        assert "script-src 'self' 'wasm-unsafe-eval';" in client.get('/').headers['content-security-policy']
    with TestClient(create_app(replace(settings,privacy_mode='local'))) as client:
        assert client.get('/music/player?id=abcdefghijk').status_code==403


def test_music_request_cannot_be_redirected_to_external_browser(settings):
    class Provider:
        calls=0
        async def reply(self,system,messages):
            self.calls+=1
            if self.calls==1:return {'reply':'','topics':[],'tool_calls':[{'name':'browser_search','arguments':{'query':'Nada pra Fazer'}}]}
            return {'reply':'Vou usar o player interno.','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,provider=Provider())) as client:
        async def forbidden(*args):raise AssertionError('External browser tool must not execute')
        client.app.state.registry.execute=forbidden
        result=client.post('/chat',headers=AUTH,json={'message':'Chronos, abre a música Nada pra Fazer'})
        assert result.status_code==200,result.text
        action=result.json()['tool_results'][0]
        assert action['status']=='failed' and 'Nenhuma aba externa' in action['error']
