"""Loopback-only keyword recognition over the existing microphone stream."""
import asyncio
import ipaddress
import secrets
import time
import json
from urllib.parse import urlsplit
from fastapi import WebSocket, WebSocketDisconnect


def local_socket(socket,settings):
    try:
        if not socket.client or not ipaddress.ip_address(socket.client.host).is_loopback:return False
        host=socket.headers.get('host','');parsed=urlsplit('http://'+host)
        if parsed.hostname not in {'localhost','127.0.0.1','::1'} or parsed.username or parsed.password:return False
        parsed.port
        origin=socket.headers.get('origin')
        scheme='https' if socket.url.scheme=='wss' else 'http'
        return bool(origin) and origin in {scheme+'://'+host,*settings.origins}
    except (ValueError,TypeError):return False


def install_interrupt(app,settings,recognizer):
    active=False
    @app.websocket('/voice/interrupt')
    async def listen(socket:WebSocket):
        nonlocal active
        if not local_socket(socket,settings):
            await socket.close(code=1008);return
        await socket.accept()
        acquired=False
        try:
            raw=await asyncio.wait_for(socket.receive_text(),5)
            if len(raw)>1024:
                await socket.close(code=1009);return
            data=json.loads(raw)
            token=data.get('token','') if isinstance(data,dict) else ''
            if not isinstance(token,str) or not settings.token or not secrets.compare_digest(token.encode(),settings.token.encode()):
                await socket.close(code=1008);return
            if active:
                await socket.close(code=1013);return
            active=True;acquired=True
            try:listener=await asyncio.to_thread(recognizer.keyword_listener)
            except ValueError:
                await socket.send_json({'type':'unavailable','message':'Reconhecimento local de Cronos indisponível. Execute Instalar-Cronos.bat para preparar o modelo português. O modo de chamada pelo nome precisa desse modelo; ESC continua funcionando.'});return
            await socket.send_json({'type':'ready'})
            # Keyword PCM is processed locally for activation/interruption, never
            # stored or sent to Gemini/Fish. A bounded burst permits pre-roll.
            credit=64000;last=time.monotonic() # one second of microphone pre-roll may arrive at once
            while True:
                frames=await asyncio.wait_for(socket.receive_bytes(),15)
                now=time.monotonic();credit=min(64000,credit+(now-last)*64000);last=now
                if not frames or len(frames)>6400 or len(frames)%2 or len(frames)>credit:
                    await socket.close(code=1009);return
                credit-=len(frames)
                if await asyncio.to_thread(listener.feed,frames):
                    await socket.send_json({'type':'keyword','word':'Cronos'});return
        except (WebSocketDisconnect,asyncio.TimeoutError,ValueError,RuntimeError,KeyError):pass
        finally:
            if acquired:active=False
            try:await socket.close()
            except RuntimeError:pass
