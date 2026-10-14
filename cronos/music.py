"""Public music catalog and an internal, official YouTube player."""
import json
import asyncio
import threading
import time
import os
import re
from urllib.parse import parse_qs, urlparse, urlencode

import httpx
from fastapi import Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path

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
            lockup=item.get('lockupViewModel')
            if isinstance(lockup,dict) and lockup.get('contentType')=='LOCKUP_CONTENT_TYPE_VIDEO':
                ident=lockup.get('contentId','')
                title=lockup.get('metadata',{}).get('lockupMetadataViewModel',{}).get('title',{}).get('content','')
                if isinstance(ident,str) and VIDEO.fullmatch(ident) and ident not in seen and isinstance(title,str):
                    seen.add(ident);results.append({'id':ident,'title':title[:250] or 'Vídeo do YouTube'})
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


CATALOG_LOCK=threading.BoundedSemaphore(1)


def catalog_fallback(query):
    if not CATALOG_LOCK.acquire(blocking=False):return []
    try:
        from ddgs import DDGS
        results=DDGS(timeout=6).videos(query+' site:youtube.com/watch',region='br-pt',safesearch='moderate',max_results=8)
        tracks=[];seen=set()
        for item in results:
            ident=video_id(item.get('content') or item.get('url') or '')
            if ident and ident not in seen:
                seen.add(ident);tracks.append({'id':ident,'title':str(item.get('title') or 'Vídeo do YouTube')[:250]})
        return tracks
    except Exception:return []
    finally:CATALOG_LOCK.release()


async def fallback_catalogs(term):
    tasks=[asyncio.create_task(asyncio.to_thread(fn,term)) for fn in (metadata_search,catalog_fallback)]
    try:
        pending=set(tasks);deadline=time.monotonic()+10
        while pending and time.monotonic()<deadline:
            done,pending=await asyncio.wait(pending,timeout=max(.01,deadline-time.monotonic()),return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    result=task.result()
                    if result:return result
                except Exception:pass
        return []
    finally:
        for task in tasks:
            if not task.done():task.cancel()


async def search_music(query,similar=False,video=False):
    cache_key=(query.casefold().strip(),similar,video)
    cached=CACHE.get(cache_key)
    if cached and time.monotonic()-cached[0]<600:return cached[1]
    ident=video_id(query)
    if ident:return {'tracks':[{'id':ident,'title':'Vídeo solicitado'}],'video':video,'search_url':'https://www.youtube.com/watch?v='+ident}
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
        try:tracks=await fallback_catalogs(term)
        except Exception:pass
    result={'query':query,'tracks':tracks,'video':video,'search_url':link,'message':None if tracks else 'Não consegui consultar o catálogo de vídeos. Nenhuma música começou. Tente outra busca ou cole o link do vídeo para reproduzir aqui; não vou abrir uma janela externa.'}
    if tracks:
        if len(CACHE)>=16:CACHE.pop(next(iter(CACHE)))
        CACHE[cache_key]=(time.monotonic(),result)
    return result


def install_music(app,authenticate):
    install_native_music(app,authenticate)
    @app.get('/music/search',dependencies=[Depends(authenticate)])
    async def search(query:str=Query(min_length=1,max_length=240),similar:bool=False,video:bool=False):
        if app.state.engine.settings.privacy_mode=='local':raise HTTPException(403,'Música online está desativada no modo local.')
        return await search_music(query,similar,video)


MEDIA_CACHE={}


def allowed_stream(url):
    try:
        parsed=urlparse(url)
        return parsed.scheme=='https' and bool(parsed.hostname) and parsed.hostname.endswith('.googlevideo.com') and not parsed.username and not parsed.password and parsed.port in {None,443} and len(url)<=16000
    except (ValueError,TypeError):return False


def select_media(info,clip):
    if info.get('availability') in {'private','premium_only','subscriber_only','needs_auth'}:
        raise ValueError('Este conteúdo exige acesso próprio e não será reproduzido por este player.')
    formats=[f for f in info.get('formats',[]) if str(f.get('protocol','')).startswith('http') and allowed_stream(f.get('url',''))]
    def has(f,key):return f.get(key) not in {None,'none'}
    audios=[f for f in formats if has(f,'acodec') and not has(f,'vcodec')]
    audios.sort(key=lambda f:(f.get('language_preference') or 0,f.get('ext')=='m4a',0<(f.get('abr') or 0)<=160,f.get('abr') or 0),reverse=True)
    combined=[f for f in formats if has(f,'acodec') and has(f,'vcodec') and 0<(f.get('height') or 0)<=480 and (f.get('fps') or 30)<=30]
    combined.sort(key=lambda f:(f.get('language_preference') or 0,f.get('ext')=='mp4',str(f.get('vcodec','')).startswith('avc'),f.get('height') or 0),reverse=True)
    videos=[f for f in formats if has(f,'vcodec') and not has(f,'acodec') and 0<(f.get('height') or 0)<=480 and (f.get('fps') or 30)<=30 and not str(f.get('vcodec','')).startswith('av01')]
    videos.sort(key=lambda f:(f.get('ext')=='mp4',str(f.get('vcodec','')).startswith('avc'),f.get('height') or 0),reverse=True)
    if not clip and (audios or combined):
        return {'audio_url':(audios or combined)[0]['url'],'video_url':None,'title':str(info.get('title') or 'Música')[:250]}
    if combined:return {'video_url':combined[0]['url'],'audio_url':None,'title':str(info.get('title') or 'Clipe')[:250]}
    if videos and audios:return {'video_url':videos[0]['url'],'audio_url':audios[0]['url'],'title':str(info.get('title') or 'Clipe')[:250]}
    raise ValueError('A fonte não forneceu um formato de áudio/vídeo compatível com o player interno.')


def resolve_native(ident,clip):
    if not METADATA_LOCK.acquire(blocking=False):raise RuntimeError('Outra música está sendo preparada. Tente novamente em alguns segundos.')
    try:
        import yt_dlp
        from cronos.media_runtime import node_executable
        node=node_executable()
        options={'js_runtimes':{'node':{'path':node}},'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True,'socket_timeout':7,'retries':0,'extractor_retries':0,'logger':QuietLogger()}
        with yt_dlp.YoutubeDL(options) as client:
            info=client.extract_info('https://www.youtube.com/watch?v='+ident,download=False)
        return select_media(info or {},clip)
    finally:METADATA_LOCK.release()


def install_native_music(app,authenticate):
    @app.get('/music/player',include_in_schema=False)
    async def player():
        if app.state.engine.settings.privacy_mode=='local':raise HTTPException(403,'Música online está desativada no modo local.')
        return FileResponse(Path(__file__).parent/'static'/'music-player.html')

    @app.get('/music/resolve',dependencies=[Depends(authenticate)])
    async def resolve(id:str=Query(pattern=r'^[A-Za-z0-9_-]{11}$'),video:bool=False,native:bool=False):
        if app.state.engine.settings.privacy_mode=='local':raise HTTPException(403,'Música online está desativada no modo local.')
        # Signed CDN URLs can require extractor-specific headers and expire.
        # The official embedded player negotiates playback itself, inside
        # Kronos, without a subprocess, a new tab, or a 25-second extraction.
        if not native:return {'player':'official','id':id,'video':video}
        key=(id,video);cached=MEDIA_CACHE.get(key)
        if cached and time.monotonic()-cached[0]<240:return cached[1]
        try:result=await asyncio.wait_for(asyncio.to_thread(resolve_native,id,video),25)
        except RuntimeError as exc:raise HTTPException(409,str(exc)) from None
        except ValueError as exc:raise HTTPException(502,str(exc)) from None
        except Exception:raise HTTPException(502,'Não consegui preparar o fluxo de mídia. Confira a instalação de yt-dlp, a conexão e a disponibilidade do vídeo. Nenhuma aba externa foi aberta.') from None
        if len(MEDIA_CACHE)>=8:MEDIA_CACHE.pop(next(iter(MEDIA_CACHE)))
        MEDIA_CACHE[key]=(time.monotonic(),result)
        return result
