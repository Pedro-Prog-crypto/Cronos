import json
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from cronos.app import create_app
from cronos.recognition import KeywordListener,LocalRecognizer
from test_backend import settings


class Recognizer:
    def __init__(self):self.data={};self.final=False
    def AcceptWaveform(self,frames):return self.final
    def PartialResult(self):return json.dumps(self.data)
    def Result(self):return json.dumps(self.data)


def test_keyword_is_exact_stable_and_other_conversations_do_not_interrupt():
    rec=Recognizer();listener=KeywordListener(rec)
    for phrase in ['discord','discordo','vamos conversar','cronometrar','sincronos']:
        rec.data={'partial':phrase}
        for _ in range(4):assert not listener.feed(b'00')
    rec.data={'partial':'cronos'}
    assert not listener.feed(b'00')
    assert listener.feed(b'00')
    rec.final=True;rec.data={'text':'cronos','result':[{'word':'cronos','conf':.4}]}
    assert not listener.feed(b'00')
    rec.data['result'][0]['conf']=.95
    assert listener.feed(b'00')


def test_partial_keyword_requires_acoustic_confirmation():
    rec=Recognizer();rec.data={'partial':'cromos'}
    checked=[]
    listener=KeywordListener(rec,['cromos'],lambda frames:checked.append(frames) or False)
    for _ in range(12):assert not listener.feed(bytes(3200))
    assert checked and all(len(frames)<=64000 for frames in checked)


def test_interrupt_socket_auth_origin_pcm_and_no_ai_generation(settings,monkeypatch):
    class Listener:
        calls=0
        def feed(self,frames):self.calls+=1;return self.calls==2
    listener=Listener()
    monkeypatch.setattr(LocalRecognizer,'keyword_listener',lambda self:listener)
    class Provider:
        async def reply(self,*args):raise AssertionError('Keyword recognition cannot call Gemini')
    with TestClient(create_app(settings,provider=Provider())) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('ws://127.0.0.1/voice/interrupt',headers={'Origin':'https://evil.invalid'}):pass
        headers={'Origin':'http://127.0.0.1'}
        with client.websocket_connect('ws://127.0.0.1/voice/interrupt',headers=headers) as socket:
            socket.send_json({'token':'wrong'})
            with pytest.raises(WebSocketDisconnect):socket.receive_json()
        with client.websocket_connect('ws://127.0.0.1/voice/interrupt',headers=headers) as socket:
            socket.send_json({'token':'test-token'});assert socket.receive_json()=={'type':'ready'}
            socket.send_bytes(bytes(3200));socket.send_bytes(bytes(3200))
            assert socket.receive_json()=={'type':'keyword','word':'Cronos'}
        assert listener.calls==2
        with client.websocket_connect('ws://127.0.0.1/voice/interrupt',headers=headers) as socket:
            socket.send_json({'token':'test-token'});assert socket.receive_json()['type']=='ready'
            socket.send_bytes(b'odd')
            with pytest.raises(WebSocketDisconnect):socket.receive_json()


def test_missing_local_model_is_reported_without_remote_fallback(settings,monkeypatch):
    def missing(self):raise ValueError('missing')
    monkeypatch.setattr(LocalRecognizer,'keyword_listener',missing)
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect('ws://127.0.0.1/voice/interrupt',headers={'Origin':'http://127.0.0.1'}) as socket:
            socket.send_json({'token':'test-token'})
            assert socket.receive_json()['type']=='unavailable'
