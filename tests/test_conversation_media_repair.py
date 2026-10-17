import asyncio
import base64
import io
import json
import time
import wave
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cronos.app import create_app
from cronos.spoken_text import conversation_text,speech_text
from cronos.recognition import check_signal
from cronos import media_streams,stremio
from test_backend import settings,AUTH


def picture():
    output=io.BytesIO();Image.new('RGB',(60,40),'blue').save(output,'PNG')
    return base64.b64encode(output.getvalue()).decode()


def test_internal_suffix_and_path_prefix_never_enter_answer_but_notes_are_preserved(settings):
    class Provider:
        async def reply(self,system,messages):
            assert 'não comprovam o que o senhor disse' in system
            return {'reply':'C:\\Users\\Pedro\\vault\\Temas\\mentalista.md\nPatrick Jane observa detalhes.\n\nResumo para memória: O usuário gosta de O Mentalista.',
                    'topics':[{'title':'O Mentalista','summary':'O senhor mencionou a série.'}],'tool_calls':[]}
    with TestClient(create_app(settings,Provider())) as client:
        result=client.post('/chat',headers=AUTH,json={'message':'Gosto de O Mentalista.'}).json()
        assert result['reply']=='Patrick Jane observa detalhes.'
        assert len(result['notes'])==1
        assert 'O senhor mencionou a série.' in (settings.vault/result['notes'][0]).read_text()
        assert client.get('/conversations/'+result['session_id'],headers=AUTH).json()['messages'][-1]['content']==result['reply']


def test_speech_preserves_explanation_and_summary_requests_but_not_code_links_or_footer():
    text='## Exemplo\nVeja [a documentação](https://example.com).\n```python\nprint("oi")\n```\n\nO usuário falou que gosta da série.'
    assert speech_text(text)=='Exemplo Veja a documentação. O código está disponível na tela.'
    assert conversation_text('Resumo da conversa:\nFalamos de filosofia.').startswith('Resumo da conversa:')
    assert 'print("oi")' in conversation_text(text)
    assert conversation_text(json.dumps({'reply':'Olá, senhor.','topics':[]}))=='Olá, senhor.'
    assert speech_text('O usuário é uma entidade do sistema. Banco e espanhol são os assuntos desta explicação.')=='O usuário é uma entidade do sistema. Banco e espanhol são os assuntos desta explicação.'


def test_early_speech_never_splits_a_code_fence_or_internal_path():
    from cronos.reply_stream import ready_intro
    for text in ('```python\nprint("oi"); '+('private_code '*20), 'C:\\Users\\Pedro\\vault\\Temas\\nota.md\nUma explicação. Outra frase.'):
        raw=json.dumps({'tool_calls':[],'reply':text,'topics':[]})
        assert ready_intro(raw) is None


@pytest.mark.parametrize('endpoint',['/voice/speech','/voice/stream','/voice/pcm'])
def test_voice_request_validates_and_cleans_before_provider(settings,endpoint):
    from cronos.app import SpeechInput
    assert SpeechInput(text='Olá.\n\nResumo para memória: falou da série').text=='Olá.'
    with TestClient(create_app(settings)) as client:
        assert client.post(endpoint,headers=AUTH,json={'text':'C:\\Users\\Pedro\\vault\\Temas\\teste.md'}).status_code==422


def test_digital_silence_is_not_sent_to_ai_or_stored(settings):
    class Provider:
        async def reply(self,*args):raise AssertionError('Silence must not reach a model')
    output=io.BytesIO()
    with wave.open(output,'wb') as file:
        file.setnchannels(1);file.setsampwidth(2);file.setframerate(16000);file.writeframes(bytes(32000))
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        result=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav'},content=output.getvalue())
        assert result.status_code==422 and 'Nada foi enviado' in result.text
        assert client.app.state.memory.stats()['messages']==0
    check_signal(b'\x40\x00'*1600)  # Quiet input is not equated with silence.


def test_screen_observation_is_bound_to_actual_session_and_expires(settings):
    class Vision:
        async def reply(self,system,messages):
            assert messages[0]['image']['mime_type']=='image/jpeg'
            return {'reply':'A captura mostra um formulário com campos sobrepostos.','tool_calls':[]}
    class Chat:
        systems=[]
        async def reply(self,system,messages):
            self.systems.append(system)
            return {'reply':'Vamos conferir os campos, senhor.','topics':[]}
    chat=Chat()
    with TestClient(create_app(settings,chat,vision_provider=Vision())) as client:
        result=client.post('/vision/analyze',headers=AUTH,json={'source':'screen','image_base64':picture(),'consent':True}).json()
        session=result['session_id']
        assert result['stored_image'] is False
        observed=client.app.state.engine.screen_observations[session]
        assert 'data' not in observed and 'image' not in observed
        client.post('/chat',headers=AUTH,json={'message':'O que está errado na captura?','session_id':session})
        assert 'campos sobrepostos' in chat.systems[-1] and 'não vídeo ao vivo' in chat.systems[-1]
        client.post('/chat',headers=AUTH,json={'message':'O que está errado na captura?','session_id':str(uuid4())})
        assert 'campos sobrepostos' not in chat.systems[-1]
        observed['received']=time.monotonic()-601
        client.post('/chat',headers=AUTH,json={'message':'Olhe novamente','session_id':session})
        assert 'CAPTURA COMPARTILHADA' not in chat.systems[-1]
        assert client.post('/vision/analyze',headers=AUTH,json={'source':'screen','image_base64':picture(),'consent':False}).status_code==422


def test_media_ticket_can_play_without_bearer_and_range_survives(settings,monkeypatch):
    calls=[];closed=[]
    class Conn:
        def close(self):closed.append(True)
    class Response:
        status=206
        def __init__(self):self.file=io.BytesIO(b'media-fragment')
        def getheader(self,name,default=None):return {'Content-Length':'14','Content-Range':'bytes 2-15/40','Accept-Ranges':'bytes'}.get(name,default)
        def read1(self,size):return self.file.read(size)
    def open_media(url,requested):
        calls.append((url,requested));return Conn(),Response(),'video/mp4'
    monkeypatch.setattr(media_streams,'open_media',open_media)
    with TestClient(create_app(settings)) as client:
        path=client.app.state.media_tickets.issue('https://media.example.com/movie.mp4')
        response=client.get(path,headers={'Range':'bytes=2-15'})
        assert response.status_code==206 and response.content==b'media-fragment'
        assert response.headers['content-range']=='bytes 2-15/40'
        assert calls==[('https://media.example.com/movie.mp4','bytes=2-15')]
        assert len(closed)==1 and client.app.state.media_tickets.active==0
        assert client.get('/media/stream/'+'x'*32).status_code==410
        assert client.get(path,headers={'Origin':'https://evil.example'}).status_code==403
        assert client.get('/music/resolve?id=abcdefghijk').status_code==401


def test_media_redirect_cannot_access_private_network(monkeypatch):
    from cronos.studio.network import PublicFetchError
    addresses=[]
    def public(url,**kw):
        from urllib.parse import urlsplit
        addresses.append(url)
        if '127.0.0.1' in url:raise PublicFetchError('private')
        return urlsplit(url),'media.example',443,'93.184.215.14'
    class Conn:
        def __init__(self,*args):pass
        def request(self,*args,**kw):pass
        def close(self):pass
        def getresponse(self):
            class Response:
                status=302
                def getheader(self,*args):return 'https://127.0.0.1/secret'
            return Response()
    monkeypatch.setattr(media_streams,'public_target',public);monkeypatch.setattr(media_streams,'PinnedHTTPS',Conn)
    with pytest.raises(ValueError):media_streams.open_media('https://media.example/movie')
    assert addresses[-1]=='https://127.0.0.1/secret'


def test_background_music_catalog_does_not_lock_playback_resolution(monkeypatch):
    import sys
    from types import SimpleNamespace
    class Downloader:
        def __init__(self,*args):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,*args,**kwargs):return {'formats':[{'url':'https://rr1.googlevideo.com/audio','protocol':'https','acodec':'mp4a','vcodec':'none','ext':'m4a'}]}
    monkeypatch.setitem(sys.modules,'yt_dlp',SimpleNamespace(YoutubeDL=Downloader))
    monkeypatch.setattr('cronos.media_runtime.node_executable',lambda:'node')
    from cronos import music
    with music.SEARCH_LOCK:
        assert music.resolve_native('abcdefghijk',False)['audio_url'].endswith('/audio')


def test_stremio_direct_addon_streams_and_incompatible_sources(settings,monkeypatch):
    calls=[]
    def public(url,**kw):
        from urllib.parse import urlsplit
        if 'localhost' in url:raise ValueError('private')
        return urlsplit(url),'cdn.example',443,'93.184.215.14'
    def fetch(url,**kw):
        calls.append(url)
        return {'status':200,'body':json.dumps({'streams':[{'url':'https://cdn.example/legal.mp4','name':'Fonte autorizada'}, {'infoHash':'torrent'}, {'externalUrl':'https://example.com'}, {'url':'https://localhost/private'}]}).encode()}
    monkeypatch.setattr('cronos.studio.network.public_target',public);monkeypatch.setattr('cronos.studio.network.public_fetch',fetch)
    with TestClient(create_app(settings)) as client:
        body={'id':'tt1196946','kind':'series','season':1,'episode':2,'addon':'https://addon.example/manifest.json'}
        assert client.post('/stremio/streams',json=body).status_code==401
        data=client.post('/stremio/streams',headers=AUTH,json=body).json()
        assert len(data['streams'])==1 and data['streams'][0]['url'].startswith('/media/stream/')
        assert calls==['https://addon.example/stream/series/tt1196946%3A1%3A2.json']
        assert client.post('/stremio/streams',headers=AUTH,json={**body,'addon':'https://localhost/manifest.json'}).status_code==502
