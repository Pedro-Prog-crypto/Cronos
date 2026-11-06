"""Local, incremental speech recognition for the open Cronos microphone."""
import asyncio
import json
import secrets
import time

from fastapi import WebSocket, WebSocketDisconnect

from cronos.voice_interrupt import local_socket


def install(app, settings, recognizer):
    active = False

    @app.websocket('/voice/live-transcript')
    async def live_transcript(socket: WebSocket):
        nonlocal active
        if not local_socket(socket, settings):
            await socket.close(code=1008)
            return
        await socket.accept()
        acquired = False
        try:
            raw = await asyncio.wait_for(socket.receive_text(), 5)
            if len(raw) > 1024:
                await socket.close(code=1009)
                return
            data = json.loads(raw)
            token = data.get('token', '') if isinstance(data, dict) else ''
            if not isinstance(token, str) or not settings.token or not secrets.compare_digest(token.encode(), settings.token.encode()):
                await socket.close(code=1008)
                return
            if active:
                await socket.close(code=1013)
                return
            active = True
            acquired = True
            try:
                listener = await asyncio.to_thread(recognizer.live_listener)
            except ValueError:
                await socket.send_json({'type': 'unavailable', 'message': 'Reconhecimento local não preparado.'})
                return
            await socket.send_json({'type': 'ready'})
            last_text = ''
            last_time = time.monotonic()
            # The recognizer also serves long dictation. A 65-second socket
            # deadline silently removed progressive captions mid-sentence.
            deadline = last_time + 190
            # Allow pre-roll and a short backlog while the model opens, then
            # replenish at the actual 16 kHz PCM rate (32 kB/s).
            credit = 256000
            while time.monotonic() < deadline:
                message = await asyncio.wait_for(socket.receive(), 15)
                if message.get('type') == 'websocket.disconnect':
                    return
                frames = message.get('bytes')
                control = message.get('text')
                if frames is not None:
                    now = time.monotonic()
                    credit = min(256000, credit + (now-last_time)*32000)
                    last_time = now
                    if not frames or len(frames) > 16000 or len(frames) % 2 or len(frames) > credit:
                        await socket.close(code=1009)
                        return
                    credit -= len(frames)
                    text = await asyncio.to_thread(listener.feed, frames)
                    if text != last_text:
                        last_text = text
                        await socket.send_json({'type': 'partial', 'text': text})
                    continue
                if control is not None and len(control) <= 64 and json.loads(control) == {'type': 'finish'}:
                    text = await asyncio.to_thread(listener.finish)
                    await socket.send_json({'type': 'final', 'text': text})
                    return
                await socket.close(code=1008)
                return
        except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, RuntimeError, KeyError, json.JSONDecodeError):
            pass
        finally:
            if acquired:
                active = False
            try:
                await socket.close()
            except RuntimeError:
                pass
