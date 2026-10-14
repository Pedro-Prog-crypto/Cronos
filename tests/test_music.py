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
