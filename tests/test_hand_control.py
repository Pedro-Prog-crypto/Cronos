from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from cronos.hand_control import DesktopPointer, install


class FakePointer:
    def __init__(self):
        self.events=[]
    def bounds(self):return (0,0,1920,1080)
    def move(self,x,y):self.events.append(('move',x,y))
    def left(self,down):self.events.append(('left',down))
    def right_click(self):self.events.append(('right',))
    def wheel(self,delta):self.events.append(('wheel',delta))
    def zoom(self,delta):self.events.append(('zoom',delta))
    def release(self):self.events.append(('release',))


def test_desktop_pointer_maps_and_releases_mouse():
    class User32:
        def __init__(self):self.calls=[]
        def GetSystemMetrics(self,index):return {76:-1920,77:0,78:3840,79:1080}[index]
        def SetCursorPos(self,x,y):self.calls.append(('move',x,y));return True
        def mouse_event(self,*args):self.calls.append(('mouse',*args))
        def keybd_event(self,*args):self.calls.append(('key',*args))
    user=User32();pointer=DesktopPointer(user)
    pointer.move(0,1);pointer.left(True);pointer.release();pointer.right_click();pointer.wheel(-120);pointer.zoom(120)
    assert user.calls[0]==('move',-1920,1079)
    assert user.calls[1][1]==0x0002 and user.calls[2][1]==0x0004
    assert [call[1] for call in user.calls if call[0]=='mouse'][-4:]==[0x0008,0x0010,0x0800,0x0800]
    assert user.calls[5][4]==(2**32-120)
    assert user.calls[-3]==('key',0x11,0,0,0)
    assert user.calls[-2][4]==120
    assert user.calls[-1]==('key',0x11,0,0x0002,0)


def test_authenticated_local_websocket_controls_pointer_and_releases_on_stop():
    app=FastAPI();pointer=FakePointer();settings=SimpleNamespace(token='test-token')
    install(app,settings,pointer_factory=lambda:pointer)
    with TestClient(app) as client:
        with client.websocket_connect('/gestures/control',subprotocols=['cronos-auth','test-token'],headers={'origin':'http://testserver'}) as socket:
            assert socket.receive_json()=={'type':'ready','width':1920,'height':1080}
            socket.send_json({'action':'move','x':.25,'y':.75})
            socket.send_json({'action':'down'})
            socket.send_json({'action':'up'})
            socket.send_json({'action':'right_click'})
            socket.send_json({'action':'wheel','delta':120})
            socket.send_json({'action':'zoom','delta':-120})
            socket.send_json({'action':'stop'})
    assert ('move',.25,.75) in pointer.events
    assert ('left',True) in pointer.events and ('left',False) in pointer.events
    assert ('right',) in pointer.events and ('wheel',120) in pointer.events and ('zoom',-120) in pointer.events
    assert pointer.events[-1]==('release',)


def test_websocket_rejects_wrong_token_or_origin():
    app=FastAPI();install(app,SimpleNamespace(token='test-token'),pointer_factory=FakePointer)
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/gestures/control',subprotocols=['cronos-auth','wrong'],headers={'origin':'http://testserver'}):pass
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/gestures/control',subprotocols=['cronos-auth','test-token'],headers={'origin':'https://evil.example'}):pass
