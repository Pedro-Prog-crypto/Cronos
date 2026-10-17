"""Explicit full-screen sessions never narrate or save raw images in memory notes."""
import asyncio,io,time,json
from uuid import uuid4
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos.live_screen import LiveScreen
from test_backend import settings,AUTH,FakeProvider


def photo(color='red'):
    file=io.BytesIO();Image.new('RGB',(320,240),color).save(file,'PNG');return file.getvalue()


def test_capture_requires_explicit_start_is_session_scoped_and_stops_cleanly():
    calls=[]
    async def run():
        live=LiveScreen(lambda:calls.append(True) or photo())
        sid=uuid4()
        assert await live.snapshot(sid) is None and not calls
        info=await live.start(sid)
        assert info['active'] and not info['stored_image'] and len(calls)==1
        assert await live.snapshot(uuid4()) is None
        assert (await live.snapshot(sid))['mime_type']=='image/jpeg'
        live.received-=2
        await live.snapshot(sid);assert len(calls)==2
        await live.stop(sid)
        assert not live.frame and not live.active(sid)
        assert await live.snapshot(sid) is None
    asyncio.run(run())


def test_disconnect_expires_session_and_browser_frames_do_not_capture_server():
    async def run():
        calls=[];live=LiveScreen(lambda:calls.append(True) or photo());sid=uuid4()
        await live.start(sid,'browser');assert not calls and await live.snapshot(sid) is None
        await live.feed(sid,photo());assert await live.snapshot(sid)
        live.received-=6
        assert await live.snapshot(sid) is None # Never present a stale browser frame as live.
        live.touched-=121
        assert not live.active(sid)
        await asyncio.sleep(1.05)
        assert live.frame is None and live.session is None
        await live.close()
    asyncio.run(run())


def test_another_session_cannot_take_over_or_stop_existing_capture():
    async def run():
        live=LiveScreen(lambda:photo());sid=uuid4()
        await live.start(sid)
        with pytest.raises(ValueError):await live.start(uuid4())
        with pytest.raises(ValueError):await live.stop(uuid4())
        assert live.active(sid)
        await live.close()
    asyncio.run(run())


def test_stop_during_a_capture_cannot_publish_a_late_frame():
    async def run():
        import threading
        entered,release=threading.Event(),threading.Event()
        def grab():entered.set();release.wait(2);return photo()
        live=LiveScreen(grab);sid=uuid4()
        task=asyncio.create_task(live.start(sid))
        await asyncio.to_thread(entered.wait,1)
        await live.stop(sid);release.set();await task
        assert live.frame is None and not live.active(sid)
        await live.close()
    asyncio.run(run())


def test_routes_feed_current_screen_to_chat_without_background_provider_calls_or_saved_image(settings):
    provider=FakeProvider()
    with TestClient(create_app(settings,provider),client=('127.0.0.1',12345)) as client:
        manager=client.app.state.live_screen;manager.capture=lambda:photo()
        assert client.post('/vision/live/start',json={'consent':True}).status_code==401
        assert client.post('/vision/live/start',headers=AUTH,json={'consent':False}).status_code==422
        started=client.post('/vision/live/start',headers=AUTH,json={'consent':True}).json();sid=started['session_id']
        assert started['active'] and not provider.calls
        frame=client.get('/vision/live/frame',params={'session_id':sid},headers=AUTH)
        assert frame.status_code==200 and frame.headers['cache-control']=='no-store'
        result=client.post('/chat',headers=AUTH,json={'session_id':sid,'message':'O que aparece nesta tela?'});assert result.status_code==200
        assert provider.calls[-1][1][-1]['image']['mime_type']=='image/jpeg'
        assert 'Não narre a tela espontaneamente' in provider.calls[-1][0]
        assert client.post('/vision/live/keepalive',headers=AUTH,json={'session_id':sid}).json()['active']
        assert client.post('/vision/live/stop',headers=AUTH,json={'session_id':sid}).status_code==200
        assert client.get('/vision/live/frame',headers=AUTH,params={'session_id':sid}).status_code==409
        client.post('/chat',headers=AUTH,json={'session_id':sid,'message':'Agora responda sem olhar a tela.'})
        assert 'image' not in provider.calls[-1][1][-1]
        history=client.get('/conversations/'+sid,headers=AUTH).text
        assert 'mime_type' not in history and 'data:image' not in history
        assert not list(settings.vault.rglob('*.png')) and not list(settings.vault.rglob('*.jpg'))


def test_remote_requests_are_blocked_and_explicit_browser_sharing_works_locally(settings):
    with TestClient(create_app(settings,FakeProvider()),client=('198.51.100.10',12345)) as client:
        assert client.post('/vision/live/start',headers=AUTH,json={'consent':True,'source':'local'}).status_code==403
        assert client.post('/vision/live/start',headers=AUTH,json={'consent':True,'source':'browser'}).status_code==403
    with TestClient(create_app(settings,FakeProvider()),client=('127.0.0.1',12345)) as client:
        result=client.post('/vision/live/start',headers=AUTH,json={'consent':True,'source':'browser'}).json();sid=result['session_id']
        assert result['active']
        assert client.post('/vision/live/frame',headers=AUTH,params={'session_id':sid},content=photo()).status_code==200
        assert client.get('/vision/live/frame',headers=AUTH,params={'session_id':sid}).status_code==200
        assert client.post('/vision/live/stop',headers=AUTH,json={'session_id':sid}).status_code==200
