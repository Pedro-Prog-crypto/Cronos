"""Search public video metadata; playback stays in YouTube's official player."""
import json
import os
import re
from urllib.parse import parse_qs, urlparse, urlencode

import httpx
from fastapi import Depends, HTTPException, Query

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


def install_music(app, authenticate):
    @app.get('/music/search', dependencies=[Depends(authenticate)])
    async def search(query: str = Query(min_length=1, max_length=240), similar: bool = False):
        if app.state.engine.settings.privacy_mode == 'local':
            raise HTTPException(403, 'Música online está desativada no modo local.')
        ident = video_id(query)
        if ident:
            return {'tracks': [{'id': ident, 'title': 'Vídeo solicitado'}], 'search_url': 'https://www.youtube.com/watch?v=' + ident}
        term = (query + ' mix músicas parecidas') if similar else query
        link = 'https://www.youtube.com/results?' + urlencode({'search_query': term})
        tracks = []
        key = os.getenv('YOUTUBE_API_KEY', '').strip()
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                if key:
                    response = await client.get('https://www.googleapis.com/youtube/v3/search', params={
                        'key': key, 'part': 'snippet', 'type': 'video', 'videoEmbeddable': 'true',
                        'q': term, 'maxResults': 8})
                    if response.is_success:
                        for item in response.json().get('items', []):
                            ident = item.get('id', {}).get('videoId', '')
                            if VIDEO.fullmatch(ident):
                                tracks.append({'id': ident, 'title': item.get('snippet', {}).get('title', '')[:250]})
                else:
                    async with client.stream('GET', 'https://www.youtube.com/results', params={'search_query': term, 'hl': 'pt'}) as response:
                        if response.is_success:
                            chunks, size = [], 0
                            async for chunk in response.aiter_bytes():
                                size += len(chunk)
                                if size > 4 * 1024 * 1024:
                                    break
                                chunks.append(chunk)
                            tracks = public_results(b''.join(chunks).decode('utf-8', errors='replace'))
        except (httpx.HTTPError, ValueError, RecursionError):
            pass
        return {'tracks': tracks, 'search_url': link, 'message': None if tracks else
                'A busca automática não está disponível. Abra a busca no YouTube e cole o link do vídeo aqui para tocar no Kronos.'}
