"""Cinemeta metadata and a narrow, validated link to the user's installed Stremio."""
import json
import os
import re
import sys
import time
from urllib.parse import quote

import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

IMDB=re.compile(r'^tt[0-9]{5,12}$')
BASE='https://v3-cinemeta.strem.io'
CACHE={}


class Search(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=1,max_length=200)
    kind:Literal['movie','series']='movie'
    season:int|None=Field(default=None,ge=0,le=200)
    episode:int|None=Field(default=None,ge=1,le=20000)


class Selection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^tt[0-9]{5,12}$')
    kind:Literal['movie','series']='movie'
    season:int|None=Field(default=None,ge=0,le=200)
    episode:int|None=Field(default=None,ge=1,le=20000)


def protocol_registered(platform=None):
    if (platform or sys.platform)!='win32':return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,r'stremio\shell\open\command'):return True
    except (ImportError,OSError):return False


def deeplink(selection):
    if not IMDB.fullmatch(selection.id):raise ValueError('Identificador de título inválido.')
    if (selection.season is None)!=(selection.episode is None):raise ValueError('Informe temporada e episódio juntos.')
    if selection.kind=='movie' and selection.season is not None:raise ValueError('Filmes não usam temporada/episódio.')
    video=selection.id if selection.kind=='movie' else f'{selection.id}:{selection.season}:{selection.episode}' if selection.season is not None else None
    return f'stremio:///detail/{selection.kind}/{selection.id}'+('/'+quote(video,safe='') if video else '')


async def get_json(path):
    async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
        async with client.stream('GET',BASE+path) as response:
            response.raise_for_status();parts=[];size=0
            async for part in response.aiter_bytes():
                size+=len(part)
                if size>2*1024*1024:raise ValueError('Catálogo excede o tamanho aceito.')
                parts.append(part)
            data=json.loads(b''.join(parts))
            if not isinstance(data,dict):raise ValueError('Resposta inválida do catálogo.')
            return data


async def search(body):
    query=body.query.strip()
    if not query:raise ValueError('Informe o nome do filme ou série; ator não é obrigatório.')
    if body.kind=='movie' and (body.season is not None or body.episode is not None):raise ValueError('Temporada e episódio são para séries.')
    key=(query.casefold(),body.kind)
    cached=CACHE.get(key)
    if cached and time.monotonic()-cached[0]<600:items=cached[1]
    else:
        data=await get_json(f'/catalog/{body.kind}/top/search={quote(query,safe="")}.json')
        items=[]
        for item in data.get('metas',[]):
            if not isinstance(item,dict) or not IMDB.fullmatch(str(item.get('id',''))):continue
            items.append({'id':item['id'],'name':str(item.get('name','Título'))[:200],
                          'year':str(item.get('releaseInfo',''))[:40],'kind':body.kind})
            if len(items)>=12:break
        if len(CACHE)>=16:CACHE.pop(next(iter(CACHE)))
        CACHE[key]=(time.monotonic(),items)
    return {'query':query,'kind':body.kind,'season':body.season,'episode':body.episode,'items':items,
            'message':'Escolha o título para abrir no Stremio instalado. A fonte de reprodução continua sendo escolhida no Stremio.' if items else 'Nenhum título encontrado no Cinemeta. Tente outro nome, inclusive o título original.',
            'source':BASE,'played':False}


async def open_item(body,platform=None,opener=None):
    url=deeplink(body)
    if body.kind=='series' and body.season is not None:
        data=await get_json(f'/meta/series/{body.id}.json')
        videos=data.get('meta',{}).get('videos',[])
        if not any(isinstance(v,dict) and v.get('season')==body.season and v.get('episode')==body.episode for v in videos):
            raise ValueError('O catálogo não confirmou esse episódio. Confira temporada e número antes de abrir.')
    if (platform or sys.platform)!='win32':raise ValueError('A abertura automática deste conector requer o servidor Cronos no Windows com o Stremio instalado.')
    launch=opener or getattr(os,'startfile',None)
    if not launch:raise ValueError('Não foi possível acessar o iniciador de aplicativos do Windows.')
    try:launch(url)
    except OSError:raise ValueError('O Windows não encontrou o protocolo do Stremio. Abra o Stremio uma vez ou repare a instalação dele.') from None
    return {'launch_requested':True,'played':False,'id':body.id,'kind':body.kind,'season':body.season,'episode':body.episode,
            'message':'Solicitação enviada ao Stremio instalado. Escolha uma fonte disponível no aplicativo; isso não comprova que a reprodução começou.'}


def install_stremio(app,authenticate):
    auth=[Depends(authenticate)]
    @app.get('/stremio/status',dependencies=auth)
    async def status():
        return {'protocol_registered':protocol_registered(app.state.windows.platform),'internal_player':False,
                'scope':'Abre títulos e episódios no Stremio instalado, sem ler conta, senha ou lista de complementos.'}
    @app.post('/stremio/search',dependencies=auth)
    async def catalog(body:Search):
        if app.state.engine.settings.privacy_mode!='online':raise HTTPException(403,'Catálogo online desativado no modo local.')
        if not app.state.panels.preferences.web_enabled:raise HTTPException(403,'Busca na web desativada nas permissões.')
        try:return await search(body)
        except (ValueError,httpx.HTTPError):raise HTTPException(502,'Não foi possível consultar o catálogo do Stremio. Tente novamente ou use outro título.') from None
    @app.post('/stremio/open',dependencies=auth)
    async def launch(body:Selection):
        if not app.state.panels.preferences.apps_enabled:raise HTTPException(403,'Abertura de aplicativos desativada nas permissões.')
        if app.state.engine.settings.privacy_mode!='online':raise HTTPException(403,'Integração online desativada no modo local.')
        try:return await open_item(body,app.state.windows.platform)
        except (ValueError,httpx.HTTPError) as exc:
            raise HTTPException(409,str(exc) if isinstance(exc,ValueError) else 'Não foi possível confirmar o episódio no catálogo.') from None
