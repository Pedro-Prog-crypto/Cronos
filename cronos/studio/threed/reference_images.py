"""Embed only the literal supplied photographs; generated scripts keep no network access."""
import asyncio
import base64
from collections import OrderedDict
from html import escape
from html.parser import HTMLParser
import io
import time

import httpx
from PIL import Image, ImageOps

from ..validation import reference_images


def placeholder(message='Imagem de exemplo indisponível'):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="800" height="600" fill="#18323b"/><text x="400" y="300" text-anchor="middle" fill="white" font-size="24">'+escape(message)+'</text></svg>'
    return 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()


async def download(url):
    # Exact constant URLs only; refuse redirects and never attach user credentials.
    if url not in reference_images(): raise ValueError('Fotografia fora do banco de referências.')
    async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
        async with client.stream('GET', url, headers={'Accept':'image/jpeg,image/png'}) as response:
            response.raise_for_status()
            if response.status_code != 200: raise ValueError('Fotografia indisponível.')
            if response.headers.get('content-type','').split(';')[0] not in {'image/jpeg','image/png','image/webp'}: raise ValueError('Formato inválido.')
            chunks=[];size=0
            async for chunk in response.aiter_bytes():
                size+=len(chunk)
                if size>2_000_000: raise ValueError('Fotografia acima do limite.')
                chunks.append(chunk)
    with Image.open(io.BytesIO(b''.join(chunks))) as picture:
        if picture.width*picture.height>12_000_000: raise ValueError('Fotografia acima do limite de pixels.')
        picture=ImageOps.exif_transpose(picture).convert('RGB')
        picture.thumbnail((1600,1600))
        output=io.BytesIO();picture.save(output,'JPEG',quality=85)
    return 'data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()


class Photos(HTMLParser):
    def __init__(self, replacements=None):
        super().__init__(convert_charrefs=False)
        self.replacements=replacements;self.urls=set();self.parts=[]
    def handle_starttag(self,tag,attrs):
        rendered=[]
        for key,value in attrs:
            if tag=='img' and key=='src' and value in reference_images():
                self.urls.add(value)
                if self.replacements is not None: value=self.replacements.get(value,placeholder())
            rendered.append(key if value is None else key+'="'+escape(value,quote=True)+'"')
        self.parts.append('<'+tag+(' '+' '.join(rendered) if rendered else '')+'>')
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs);self.parts[-1]=self.parts[-1][:-1]+'/>'
    def handle_endtag(self,tag):self.parts.append('</'+tag+'>')
    def handle_decl(self,decl):self.parts.append('<!'+decl+'>')
    def handle_data(self,data):self.parts.append(data)
    def handle_entityref(self,name):self.parts.append('&'+name+';')
    def handle_charref(self,name):self.parts.append('&#'+name+';')
    def handle_comment(self,data):self.parts.append('<!--'+data+'-->')


class ReferencePhotos:
    def __init__(self):
        self.cache=OrderedDict();self.lock=asyncio.Lock()
    async def prepare(self,markup):
        parser=Photos();parser.feed(markup)
        if not parser.urls:return
        # The request parser already limits markup; no more than three photo downloads at once.
        async with self.lock:
            semaphore=asyncio.Semaphore(3)
            async def one(url):
                cached=self.cache.get(url)
                if cached and cached[0]>time.monotonic():return
                async with semaphore:
                    try:
                        value=await asyncio.wait_for(download(url),timeout=6)
                        ttl=3600
                    except (httpx.HTTPError,ValueError,OSError,asyncio.TimeoutError,Image.DecompressionBombError):
                        value=placeholder();ttl=60
                    self.cache[url]=(time.monotonic()+ttl,value)
                    self.cache.move_to_end(url)
                    while len(self.cache)>24:self.cache.popitem(last=False)
            await asyncio.gather(*(one(url) for url in sorted(parser.urls)))
    def embed(self,markup,*,online):
        replacements={url:value for url,(expires,value) in self.cache.items() if expires>time.monotonic()} if online else {url:placeholder('Imagem externa desativada') for url in reference_images()}
        parser=Photos(replacements);parser.feed(markup);parser.close()
        return ''.join(parser.parts)
