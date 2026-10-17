"""Short-lived, opaque media tickets and bounded same-origin playback.

No arbitrary URL query/proxy: only authenticated resolution can mint a ticket.
Each connection (including redirects) is pinned to a validated public address.
"""
import asyncio
import http.client
import re
import secrets
import time
from urllib.parse import urljoin

from fastapi import HTTPException,Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from cronos.studio.network import public_target,PinnedHTTPS


def open_media(url,byte_range=None):
    headers={'User-Agent':'Mozilla/5.0 Cronos-Media/1.0','Accept':'video/*,audio/*,application/octet-stream','Accept-Encoding':'identity'}
    if byte_range:
        if not re.fullmatch(r'bytes=(?:\d+-\d*|-\d+)',byte_range):raise ValueError('Intervalo de mídia inválido.')
        headers['Range']=byte_range
    for _ in range(4):
        p,host,port,ip=public_target(url,max_length=16000)
        if p.scheme!='https':raise ValueError('A fonte de mídia precisa usar HTTPS.')
        conn=PinnedHTTPS(host,ip,port)
        try:
            conn.request('GET',(p.path or '/')+('?' + p.query if p.query else ''),headers={**headers,'Host':host})
            response=conn.getresponse()
            if response.status in {301,302,303,307,308}:
                url=urljoin(url,response.getheader('Location',''));conn.close();continue
            if response.status not in {200,206}:raise ValueError('A fonte recusou o fluxo. Prepare a mídia novamente.')
            mime=response.getheader('Content-Type','').split(';')[0].lower()
            if not (mime.startswith(('audio/','video/')) or mime in {'application/octet-stream','binary/octet-stream'}):
                raise ValueError('A fonte não entregou áudio ou vídeo direto compatível. Escolha outra fonte ou abra o aplicativo Stremio.')
            if response.getheader('Content-Encoding','identity')!='identity':raise ValueError('Fluxo comprimido incompatível.')
            return conn,response,mime
        except BaseException:
            conn.close();raise
    raise ValueError('A fonte redirecionou vezes demais.')


class MediaTickets:
    def __init__(self):self.items={};self.active=0

    def issue(self,url):
        now=time.monotonic()
        self.items={key:value for key,value in self.items.items() if now-value[0]<3600}
        while len(self.items)>=64:self.items.pop(next(iter(self.items)))
        token=secrets.token_urlsafe(24);self.items[token]=(now,url)
        return '/media/stream/'+token

    def install(self,app):
        @app.get('/media/stream/{ticket}',include_in_schema=False)
        async def stream(ticket:str,request:Request):
            item=self.items.get(ticket)
            if not item or time.monotonic()-item[0]>3600:raise HTTPException(410,'A mídia expirou. Prepare-a novamente no player.')
            if app.state.engine.settings.privacy_mode=='local':raise HTTPException(403,'Mídia online desativada.')
            if self.active>=4:raise HTTPException(409,'Há muitos fluxos abertos. Pause outro player e tente novamente.')
            self.active+=1
            try:conn,response,mime=await asyncio.to_thread(open_media,item[1],request.headers.get('range'))
            except (ValueError,OSError,http.client.HTTPException):
                self.active-=1
                raise HTTPException(502,'A fonte não entregou mídia reproduzível. Tente outra fonte ou prepare novamente.') from None
            headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'}
            for name in ('Content-Length','Content-Range','Accept-Ranges'):
                value=response.getheader(name)
                if value:headers[name]=value
            closed=False
            def close():
                nonlocal closed
                if closed:return
                closed=True;conn.close();self.active-=1
            def chunks():
                try:
                    while part:=response.read1(65536):yield part
                finally:
                    close()
            return StreamingResponse(chunks(),status_code=response.status,media_type=mime,headers=headers,background=BackgroundTask(close))
