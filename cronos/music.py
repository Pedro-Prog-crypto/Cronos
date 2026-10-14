"""Search public video metadata; playback stays in YouTube's official player."""
import json
import asyncio
import threading
import time
import os
import re
from urllib.parse import parse_qs, urlparse, urlencode

import httpx
from fastapi import Depends, HTTPException, Query

METADATA_LOCK=threading.BoundedSemaphore(1)
CACHE={}

VIDEO = re.compile(r'^[A-Za-z0-9_-]{11}$')


def video_id(query):
    parsed = urlparse(query)
    host = (parsed.hostname or '').lower()
    value = None
    if host in {'youtu.be', 'www.youtu.be'}:
        value = parsed.path.strip('/').split('/')[0]
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'}:
        value = parse_qs(parsed.query).get('v', [None])[0]
        parts = parsed.path.strip('/').split('/')
        if not value and len(parts) == 2 and parts[0] in {'embed', 'shorts', 'live'}:
            value = parts[1]
    return value if value and VIDEO.fullmatch(value) else None


def public_results(html):
    match = re.search(r'(?:var\s+ytInitialData\s*=|window\["ytInitialData"\]\s*=)\s*', html)
    if not match:
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(html[match.end():])
    except (ValueError, RecursionError):
        return []
    results, seen = [], set()
    def walk(item):
        if len(results) >= 8:
            return
        if isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, dict):
            video = item.get('videoRenderer')
            if isinstance(video, dict):
                ident = video.get('videoId', '')
                if VIDEO.fullmatch(ident) and ident not in seen:
                    seen.add(ident)
                    title = video.get('title', {})
                    text = title.get('simpleText') or ''.join(x.get('text', '') for x in title.get('runs', []))
                    results.append({'id': ident, 'title': text[:250] or 'Vídeo do YouTube'})
            for child in item.values():
                walk(child)
    walk(data)
    return results


class QuietLogger:
    def debug(self, message):pass
    def warning(self, message):pass
    def error(self, message):pass


def metadata_search(query):
    # Same search library as the original assistant, metadata only: no download,
    # no cookies, no extraction of restricted streams and no browser subprocess.
    if not METADATA_LOCK.acquire(blocking=False):return []
    try:
        import yt_dlp
        options={'quiet':True,'no_warnings':True,'skip_download':True,'extract_flat':True,
                 'socket_timeout':5,'retries':0,'extractor_retries':0,'logger':QuietLogger(),'playlistend':8}
        with yt_dlp.YoutubeDL(options) as client:
            data=client.extract_info('ytsearch8:'+query,download=False)
        tracks=[]
        for item in (data or {}).get('entries') or []:
            ident=(item or {}).get('id','')
            if VIDEO.fullmatch(ident):tracks.append({'id':ident,'title':str(item.get('title') or 'Vídeo do YouTube')[:250]})
            if len(tracks)>=8:break
        return tracks
    finally:METADATA_LOCK.release()


async def search_music(query,similar=False,video=False):
    cache_key=(query.casefold().strip(),similar,video)
    cached=CACHE.get(cache_key)
    if cached and time.monotonic()-cached[0]<600:return cached[1]
    ident=video_id(query)
    if ident:return {'tracks':[{'id':ident,'title':'Vídeo solicitado'}],'search_url':'https://www.youtube.com/watch?v='+ident}
    term=query+(' mix músicas parecidas' if similar else ' clipe oficial' if video else '')
    link='https://www.youtube.com/results?'+urlencode({'search_query':term})
    tracks=[];key=os.getenv('YOUTUBE_API_KEY','').strip()
    try:
        async with httpx.AsyncClient(timeout=8,follow_redirects=False) as client:
            if key:
                response=await client.get('https://www.googleapis.com/youtube/v3/search',params={'key':key,'part':'snippet','type':'video','videoEmbeddable':'true','q':term,'maxResults':8})
                if response.is_success:
                    tracks=[{'id':item['id']['videoId'],'title':item.get('snippet',{}).get('title','')[:250]} for item in response.json().get('items',[]) if VIDEO.fullmatch(item.get('id',{}).get('videoId',''))]
            else:
                async with client.stream('GET','https://www.youtube.com/results',params={'search_query':term,'hl':'pt'}) as response:
                    if response.is_success:
                        chunks=[];size=0
                        async for chunk in response.aiter_bytes():
                            size+=len(chunk)
                            if size>4*1024*1024:break
                            chunks.append(chunk)
                        tracks=public_results(b''.join(chunks).decode('utf-8',errors='replace'))
    except (httpx.HTTPError,ValueError,RecursionError):pass
    if not tracks:
        try:tracks=await asyncio.wait_for(asyncio.to_thread(metadata_search,term),18)
        except Exception:pass
    result={'tracks':tracks,'search_url':link,'message':None if tracks else 'Não consegui consultar o catálogo de vídeos. Nenhuma música começou. Tente outra busca ou cole o link do vídeo para reproduzir aqui; não vou abrir uma janela externa.'}
    if tracks:
        if len(CACHE)>=16:CACHE.pop(next(iter(CACHE)))
        CACHE[cache_key]=(time.monotonic(),result)
    return result


def install_music(app,authenticate):
    @app.get('/music/search',dependencies=[Depends(authenticate)])
    async def search(query:str=Query(min_length=1,max_length=240),similar:bool=False,video:bool=False):
        if app.state.engine.settings.privacy_mode=='local':raise HTTPException(403,'Música online está desativada no modo local.')
        return await search_music(query,similar,video)
