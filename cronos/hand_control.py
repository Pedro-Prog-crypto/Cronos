"""Authenticated, local-only mouse input for the opt-in webcam gesture mode."""
import math
import json
import secrets
import sys
import time
from ipaddress import ip_address
from urllib.parse import urlsplit


class DesktopPointer:
    """Small Windows mouse adapter. No shell, subprocess, or administrator rights."""
    def __init__(self, user32=None):
        if sys.platform != 'win32' and user32 is None:
            raise RuntimeError('O controle global por gestos está disponível no Windows.')
        if user32 is None:
            import ctypes
            user32 = ctypes.windll.user32
            user32.GetSystemMetrics.argtypes = [ctypes.c_int]
            user32.GetSystemMetrics.restype = ctypes.c_int
            user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            user32.SetCursorPos.restype = ctypes.c_bool
            user32.mouse_event.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_size_t]
            user32.mouse_event.restype = None
        self.user32 = user32
        self.pressed = False

    def bounds(self):
        # Virtual-screen coordinates include monitors placed left/above the main one.
        x = self.user32.GetSystemMetrics(76)
        y = self.user32.GetSystemMetrics(77)
        width = self.user32.GetSystemMetrics(78)
        height = self.user32.GetSystemMetrics(79)
        return (x, y, max(width, 1), max(height, 1))

    def move(self, x, y):
        left, top, width, height = self.bounds()
        px = left + round(min(max(x, 0.0), 1.0) * max(width - 1, 0))
        py = top + round(min(max(y, 0.0), 1.0) * max(height - 1, 0))
        if not self.user32.SetCursorPos(px, py):
            raise OSError('O Windows não aceitou o movimento do ponteiro.')

    def left(self, down):
        if bool(down) == self.pressed:
            return
        self.user32.mouse_event(0x0002 if down else 0x0004, 0, 0, 0, 0)
        self.pressed = bool(down)

    def right_click(self):
        self.user32.mouse_event(0x0008, 0, 0, 0, 0)
        self.user32.mouse_event(0x0010, 0, 0, 0, 0)

    def wheel(self, delta):
        value = max(-480, min(480, int(delta)))
        if value:
            self.user32.mouse_event(0x0800, 0, 0, value & 0xffffffff, 0)

    def release(self):
        self.left(False)


def install(app, settings, pointer_factory=DesktopPointer):
    from fastapi import WebSocket, WebSocketDisconnect

    @app.websocket('/gestures/control')
    async def gestures(websocket: WebSocket):
        client = websocket.client
        try:
            local = bool(client) and ip_address(client.host).is_loopback
            host = websocket.headers.get('host', '')
            origin = urlsplit(websocket.headers.get('origin', ''))
            allowed_origin = origin.scheme == 'http' and origin.netloc == host
        except (ValueError, AttributeError):
            local = allowed_origin = False
        if not local or not allowed_origin:
            await websocket.close(code=1008)
            return

        # The browser sends its short-lived token as a WebSocket subprotocol,
        # never in the URL where it could be recorded in history or server logs.
        protocols = websocket.scope.get('subprotocols', [])
        if (len(protocols) != 2 or protocols[0] != 'cronos-auth' or not settings.token
                or not secrets.compare_digest(protocols[1].encode(), settings.token.encode())):
            await websocket.close(code=1008)
            return
        await websocket.accept(subprotocol='cronos-auth')
        if sys.platform != 'win32' and pointer_factory is DesktopPointer:
            await websocket.send_json({'type':'unavailable','message':'O controle global por gestos está disponível no Windows.'})
            await websocket.close(code=1000)
            return
        try:
            pointer = pointer_factory()
            bounds = pointer.bounds()
        except (OSError, RuntimeError, AttributeError):
            await websocket.send_json({'type':'unavailable','message':'O controle de mouse do Windows não está disponível.'})
            await websocket.close(code=1011)
            return

        await websocket.send_json({'type': 'ready', 'width': bounds[2], 'height': bounds[3]})
        last_event = 0.0
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw) > 256:
                    await websocket.close(code=1009)
                    return
                event = json.loads(raw)
                if not isinstance(event, dict):
                    continue
                now = time.monotonic()
                action = event.get('action')
                if action == 'move':
                    if now - last_event < 1 / 30:
                        continue
                    last_event = now
                    x, y = event.get('x'), event.get('y')
                    if (isinstance(x, (int, float)) and not isinstance(x, bool)
                            and isinstance(y, (int, float)) and not isinstance(y, bool)
                            and math.isfinite(x) and math.isfinite(y)):
                        pointer.move(min(max(float(x), 0), 1), min(max(float(y), 0), 1))
                elif action in {'down', 'up'}:
                    pointer.left(action == 'down')
                elif action == 'right_click':
                    pointer.right_click()
                elif action == 'wheel':
                    delta = event.get('delta')
                    if isinstance(delta, int) and not isinstance(delta, bool):
                        pointer.wheel(delta)
                elif action == 'stop':
                    await websocket.close(code=1000)
                    return
        except (WebSocketDisconnect, ValueError, TypeError):
            pass
        finally:
            pointer.release()
