"""Opt-in screen session: latest frame in RAM, no background AI narration.

Local Windows capture runs at one frame/second. Browser sharing can feed the
same buffer. A connected UI renews the lease; closing it cannot leave an orphan
screen recorder running forever. No screenshots are written to disk.
"""
import asyncio
import base64
import time
from datetime import datetime, timezone
from uuid import uuid4

from cronos.vision import capture_screen, normalize_image


class LiveScreen:
    def __init__(self, capture=None):
        self.capture=capture or capture_screen
        self.session=None; self.source=None; self.frame=None; self.at=None
        self.received=0; self.touched=0; self.version=0; self.generation=0
        self.task=None; self.lock=asyncio.Lock(); self.error=None

    def active(self,session):
        return self.session==str(session) and time.monotonic()-self.touched<120

    def info(self,session):
        active=self.active(session)
        return {'active':active,'source':self.source if active else None,'captured_at':self.at if active else None,
                'version':self.version if active else 0,'error':self.error if active else None,
                'session_id':str(session),'stored_image':False,'background_ai':False}

    async def start(self,session=None,source='local'):
        session=str(session or uuid4())
        if self.session and self.active(self.session):
            if self.session!=session:raise ValueError('Há uma tela acompanhada em outra conversa. Pare o acompanhamento nela antes de iniciar aqui.')
            self.touched=time.monotonic();return self.info(session)
        await self.stop(self.session)
        self.session=session;self.source=source;self.touched=time.monotonic();self.error=None
        if source=='local':
            try:await self.refresh(session)
            except (ValueError,OSError):
                await self.stop(session)
                raise ValueError('A captura local não está disponível neste computador. No Windows, abra o Cronos localmente; pelo navegador remoto, use Compartilhar tela inteira.') from None
        self.task=asyncio.create_task(self.maintain())
        return self.info(session)

    async def stop(self,session):
        if self.session and str(session)!=self.session:raise ValueError('O acompanhamento pertence a outra conversa.')
        self.generation+=1;self.session=None;self.frame=None;self.at=None;self.source=None;self.error=None;self.received=0;self.version=0
        task=self.task;self.task=None
        if task and task is not asyncio.current_task():
            task.cancel();await asyncio.gather(task,return_exceptions=True)

    def touch(self,session):
        if not self.active(session):raise ValueError('O acompanhamento terminou. Peça para ver a tela novamente.')
        self.touched=time.monotonic();return self.info(session)

    async def refresh(self,session):
        async with self.lock:
            if not self.active(session):return None
            if self.source!='local' or time.monotonic()-self.received<.8:return self.frame
            generation=self.generation
            raw=await asyncio.to_thread(self.capture)
            image=await asyncio.to_thread(normalize_image,raw)
            if self.generation!=generation or not self.active(session):return None
            self.save(image);return self.frame

    def save(self,image):
        self.frame=image;self.received=time.monotonic();self.at=datetime.now(timezone.utc).isoformat();self.version+=1;self.error=None

    async def feed(self,session,raw):
        if not self.active(session) or self.source!='browser':raise ValueError('Inicie o compartilhamento do navegador antes de enviar uma captura.')
        async with self.lock:
            if time.monotonic()-self.received<.8:return self.info(session)
            generation=self.generation
            image=await asyncio.to_thread(normalize_image,raw)
            if self.generation==generation and self.active(session):self.save(image)
        return self.info(session)

    async def snapshot(self,session):
        if not self.active(session):return None
        try:
            if self.source=='local':await self.refresh(session)
        except (ValueError,OSError):self.error='Captura temporariamente indisponível.';return None
        if not self.frame or time.monotonic()-self.received>5:return None
        return dict(self.frame)

    async def maintain(self):
        try:
            while self.session:
                if not self.active(self.session):
                    await self.stop(self.session);return
                if self.source=='local':
                    try:await self.refresh(self.session)
                    except (OSError,ValueError):self.error='Captura temporariamente indisponível. O acompanhamento continua aguardando a tela.'
                await asyncio.sleep(1)
        except asyncio.CancelledError:raise

    async def close(self):await self.stop(self.session)


def install(app,authenticate):
    import sys
    from ipaddress import ip_address
    from uuid import UUID
    from typing import Literal
    from fastapi import Depends, HTTPException, Request, Response
    from pydantic import BaseModel, ConfigDict
    class Start(BaseModel):
        model_config=ConfigDict(extra='forbid')
        consent:Literal[True]
        session_id:UUID|None=None
        source:Literal['local','browser']='local'
    class Session(BaseModel):
        model_config=ConfigDict(extra='forbid')
        session_id:UUID
    auth=[Depends(authenticate)]
    def manager():return app.state.live_screen
    def local(request):
        try:return ip_address(request.client.host).is_loopback
        except (ValueError,AttributeError):return False
    @app.post('/vision/live/start',dependencies=auth)
    async def start(body:Start,request:Request):
        if body.source=='local' and not local(request):raise HTTPException(403,'A tela do computador só pode ser iniciada por uma conexão local. Use Compartilhar tela inteira para compartilhar a tela deste navegador.')
        try:
            result=await manager().start(body.session_id,body.source)
            app.state.engine.screen_observations.pop(result['session_id'],None)
            return result
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
    @app.get('/vision/live/status',dependencies=auth)
    async def status(session_id:UUID,request:Request):
        return {**manager().info(session_id),'local_available':sys.platform=='win32' and local(request)}
    @app.post('/vision/live/keepalive',dependencies=auth)
    async def keepalive(body:Session):
        try:return manager().touch(body.session_id)
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
    @app.post('/vision/live/stop',dependencies=auth)
    async def stop(body:Session):
        try:await manager().stop(body.session_id)
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
        app.state.engine.screen_observations.pop(str(body.session_id),None)
        return {'active':False,'stored_image':False}
    @app.get('/vision/live/frame',dependencies=auth)
    async def frame(session_id:UUID):
        image=await manager().snapshot(session_id)
        if not image:raise HTTPException(409,'A captura atual não está disponível.')
        return Response(base64.b64decode(image['data']),media_type='image/jpeg',headers={'Cache-Control':'no-store'})
    @app.post('/vision/live/frame',dependencies=auth)
    async def feed(session_id:UUID,request:Request):
        from cronos.upload_limits import MAX_UPLOAD_BYTES
        try:
            raw=bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw)>MAX_UPLOAD_BYTES:raise ValueError('Captura acima do limite de 30 MiB.')
            return await manager().feed(session_id,bytes(raw))
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
