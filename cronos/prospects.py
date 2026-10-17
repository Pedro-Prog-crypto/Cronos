"""Bounded Brazilian business discovery. Absence of evidence is never a guarantee."""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlencode
from uuid import uuid4

import httpx
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal

CATEGORIES = {
    'restaurante': ('restaurant', None, 'restaurantes'),
    'pizzaria': ('restaurant|fast_food', 'pizza', 'pizzarias'),
    'lanchonete': ('fast_food', None, 'lanchonetes'),
    'cafeteria': ('cafe', None, 'cafeterias'),
    'japones': ('restaurant', 'japanese|sushi', 'restaurantes japoneses'),
    'todos': ('restaurant|fast_food|cafe', None, 'restaurantes, lanchonetes e cafeterias'),
    'hotel': ('hotel|guest_house|hostel|motel', None, 'hotéis e pousadas'),
    'lava_jato': ('car_wash', None, 'lava-jatos e estética automotiva'),
    'loja': ('.+', None, 'lojas'),
    'clinica': ('clinic|dentist|doctors', None, 'clínicas e consultórios'),
    'barbearia': ('hairdresser|beauty', None, 'barbearias e salões'),
    'academia': ('fitness_centre|sports_centre', None, 'academias e centros esportivos'),
    'imobiliaria': ('estate_agent|architect', None, 'imobiliárias e arquitetura'),
    'educacao': ('school|college|language_school|music_school', None, 'escolas e cursos'),
    'eventos': ('events_venue|conference_centre', None, 'espaços de eventos'),
    'servicos': ('lawyer|accountant|insurance|consulting', None, 'serviços profissionais'),
}
DIRECTORIES = {'google.com', 'google.com.br', 'maps.google.com', 'instagram.com', 'facebook.com', 'tiktok.com', 'ifood.com.br', 'tripadvisor.com', 'tripadvisor.com.br', 'restaurantguru.com', 'restaurantguru.com.br', 'linktr.ee', 'wa.me', 'whatsapp.com', 'youtube.com', 'waze.com', 'foursquare.com', 'apontador.com.br', 'solutudo.com.br', 'econodata.com.br', 'cnpj.biz', '99food.com.br', 'yelp.com', 'reclameaqui.com.br'}


class ProspectSearch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    city: str = Field(min_length=2, max_length=140)
    category: str = 'restaurante'
    @field_validator('category')
    @classmethod
    def known_category(cls, value):
        if value not in CATEGORIES: raise ValueError('Categoria desconhecida.')
        return value
    limit: int = Field(default=20, ge=1, le=40)
    source: Literal['osm', 'google'] = 'osm'


class VerifyInput(BaseModel):
    report_id: str = Field(max_length=40)
    lead_id: str = Field(max_length=200)


def website(value):
    if not isinstance(value, str) or len(value)>1000:return None
    value=value.strip()
    if re.match(r'^[a-zA-Z][\w+.-]*:',value) and not value.lower().startswith(('https://','http://')):return None
    if value and '://' not in value:value='https://'+value
    try:
        parsed=urlsplit(value)
        if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password or parsed.port not in {None,80,443} or '.' not in parsed.hostname or re.search(r'\s',value):return None
        import ipaddress
        try:
            if not ipaddress.ip_address(parsed.hostname).is_global:return None
        except ValueError:pass
        if parsed.hostname.lower().endswith(('.local','.localhost','.internal')):return None
        return value
    except ValueError:return None


def hostname(url):
    return (urlsplit(url).hostname or '').lower().removeprefix('www.')


def directory(url):
    host=hostname(url)
    return any(host==base or host.endswith('.'+base) for base in DIRECTORIES)


def recommendation(lead):
    seats=lead.get('seats')
    chain=bool(lead.get('brand'))
    size='pequeno' if isinstance(seats,int) and seats<=50 else 'medio' if isinstance(seats,int) and seats<=120 else 'grande' if isinstance(seats,int) else 'desconhecido'
    lead['size']=size
    difficulty='alta' if chain or size=='grande' else 'media' if size=='medio' else 'baixa'
    reasons=[]
    if chain:reasons.append('Há uma marca/rede registrada; pode existir aprovação central, padrões e integrações.')
    if size=='grande':reasons.append('A capacidade registrada ultrapassa 120 lugares; confirme unidades, reservas e operação antes de estimar.')
    if size=='desconhecido':reasons.append('O porte não foi informado. Um site básico pode ser simples; o negócio ainda precisa ser qualificado.')
    if lead['site_status'] in {'listed','candidate','found'}:reasons.append('Há um site informado ou candidato. Avalie melhorias antes de oferecer um site novo.')
    reasons.append('Pedidos pagos, estoque, contas de clientes e integração ao caixa aumentam muito o escopo.')
    lead['project']={
        'difficulty':difficulty,'opinion':('Eu começaria por outro cliente menor, ou faria apenas uma página piloto.' if difficulty=='alta' else 'Eu começaria com uma página simples e um cardápio editável, após confirmar o interesse do responsável.'),
        'scope':['Página de apresentação adaptada ao celular','Cardápio com preços e atualização simples','Horário, endereço e link para rotas','Contato por WhatsApp e acessibilidade básica'],
        'avoid_initially':['Pagamento online','Integração com caixa/estoque','Aplicativo próprio e múltiplas unidades'],
        'reasons':reasons,'steps':['Confirmar interesse e necessidades com o responsável','Definir conteúdo, orçamento e o que fica fora do escopo','Criar um protótipo em HTML/CSS antes de escolher frameworks','Testar celular, teclado, links e atualização do cardápio','Publicar com HTTPS e documentar a manutenção'],
    }
    from cronos.studio.catalog import quote
    category=lead.get('category','')
    if category not in {'restaurant','restaurante','fast_food','cafe','pizzaria','lanchonete','cafeteria','japones','todos'}:
        lead['project']['scope']=['Apresentação e catálogo de serviços adaptados ao celular','Contato comercial confirmado, horários e endereço','Solicitação de horário, com confirmação manual da equipe']
        lead['project']['opinion']='Senhor, eu começaria por um protótipo com os serviços confirmados e validaria o interesse do responsável antes de ampliar o escopo.'
    lead['project']['quote']=quote(category, '')
    lead['project']['financial_status']='Não informado; aparência e avaliações não comprovam orçamento.'
    return lead


def osm_lead(item,city):
    tags=item.get('tags',{});name=tags.get('name')
    if not name:return None
    capacity=str(tags.get('capacity:seats',tags.get('capacity','') if tags.get('amenity') in {'restaurant','fast_food','cafe'} else ''))
    seats=int(capacity) if capacity.isdigit() and 0<int(capacity)<=10000 else None
    url=website(tags.get('website') or tags.get('contact:website'))
    official=url if url and not directory(url) else None
    ident=f"osm:{item['type']}:{item['id']}"
    source=f"https://www.openstreetmap.org/{item['type']}/{item['id']}"
    address=', '.join(v for v in [tags.get('addr:street'),tags.get('addr:housenumber'),tags.get('addr:suburb'),city] if v)
    return recommendation({'id':ident,'name':name[:200],'city':city,'address':address,'category':tags.get('amenity') or tags.get('tourism') or tags.get('shop') or tags.get('office') or tags.get('leisure'),'cuisine':tags.get('cuisine'),'brand':tags.get('brand'),'seats':seats,
      'phone':tags.get('contact:phone') or tags.get('phone'),'rating':None,'rating_count':None,'website':official,'site_status':'listed' if official else 'unverified','evidence':[{'source':'OpenStreetMap','url':source,'note':'Site informado no cadastro público.' if official else 'O campo de site próprio não está preenchido; isso não comprova ausência de site.'}], 'social_or_directory':url if url and not official else None,'checked_at':None})


async def fetch_json(client,method,url,**kwargs):
    async with client.stream(method,url,**kwargs) as response:
        if not response.is_success:raise HTTPException(502,f'A fonte pública recusou a consulta (HTTP {response.status_code}). Tente mais tarde ou escolha outra fonte disponível.')
        chunks=[];size=0
        async for chunk in response.aiter_bytes():
            size+=len(chunk)
            if size>2*1024*1024:raise HTTPException(502,'A fonte retornou mais dados que o limite seguro da pesquisa.')
            chunks.append(chunk)
        try:return json.loads(b''.join(chunks))
        except ValueError:raise HTTPException(502,'A fonte retornou um formato inesperado.') from None


class Prospector:
    def __init__(self):
        self.reports={};self.cache={};self.lock=asyncio.Lock();self.verify_lock=asyncio.Lock();self.last_geocode=0

    async def search(self,args):
        if args.source=='google' and not os.getenv('GOOGLE_PLACES_API_KEY','').strip():
            raise HTTPException(503,'Configure GOOGLE_PLACES_API_KEY no .env para usar avaliações do Google Places. A API pode consumir cota ou gerar cobrança.')
        cache_key=(args.city.casefold(),args.category,args.limit,args.source)
        cached=self.cache.get(cache_key)
        if cached and time.monotonic()-cached[0]<1800:
            return {**self.reports[cached[1]],'cached':True}
        if self.lock.locked():raise HTTPException(409,'Uma pesquisa já está em andamento. Aguarde o resultado.')
        async with self.lock:
            try:
                async with httpx.AsyncClient(timeout=28,follow_redirects=False,headers={'User-Agent':'Cronos/0.5 (https://github.com/Pedro-Prog-crypto/Cronos)'}) as client:
                    await asyncio.sleep(max(0,1.1-(time.monotonic()-self.last_geocode)))
                    self.last_geocode=time.monotonic()
                    from cronos.municipalities import lookup
                    local=lookup(args.city)
                    location_note=None
                    try:
                        async with asyncio.timeout(8):
                            locations=await fetch_json(client,'GET','https://nominatim.openstreetmap.org/search',params={'q':args.city+', Brasil','countrycodes':'br','format':'jsonv2','addressdetails':1,'limit':5,'featureType':'city'})
                        if not isinstance(locations,list):raise ValueError('Location format')
                        locations=[p for p in locations if isinstance(p,dict) and isinstance(p.get('address'),dict) and p['address'].get('country_code')=='br' and (p.get('addresstype') in {'city','town','municipality','village'} or any(p.get('address',{}).get(k) for k in ('city','town','municipality','village')))]
                        if not locations and local:locations=[local]
                    except (httpx.HTTPError,HTTPException,TimeoutError,ValueError,KeyError,TypeError,AttributeError):
                        if not local:raise HTTPException(502,'O serviço de localização não respondeu e esse nome não correspondeu à base local de municípios. Confira cidade e UF.') from None
                        locations=[local]
                    if locations and locations[0].get('local_fallback'):
                        location_note='Localização pela base local de municípios; busca de negócios em um raio de 15 km do centro. Não cobre todo o território municipal.'
                    if not locations:raise HTTPException(404,'Não encontrei essa cidade no Brasil. Informe cidade e estado, por exemplo: Manaus, AM.')
                    # Multiple municipalities must be disambiguated instead of silently selecting one.
                    names={p.get('display_name','') for p in locations}
                    if len(names)>1:raise HTTPException(409,{'message':'Há mais de uma localização. Informe também o estado.', 'locations':list(names)[:5]})
                    place=locations[0];city=place['display_name'];amenity,cuisine,label=CATEGORIES[args.category]
                    if args.source=='google':
                        key=os.getenv('GOOGLE_PLACES_API_KEY','').strip()
                        if not key:raise HTTPException(503,'Configure GOOGLE_PLACES_API_KEY no .env para usar avaliações do Google Places. A API pode consumir cota ou gerar cobrança.')
                        south,north,west,east=map(float,place['boundingbox'])
                        raw=await fetch_json(client,'POST','https://places.googleapis.com/v1/places:searchText',headers={'X-Goog-Api-Key':key,'X-Goog-FieldMask':'places.id,places.displayName,places.formattedAddress,places.websiteUri,places.rating,places.userRatingCount,places.nationalPhoneNumber,places.googleMapsUri,places.businessStatus'},json={'textQuery':label+' em '+args.city+', Brasil','pageSize':min(args.limit,20),'regionCode':'BR','locationRestriction':{'rectangle':{'low':{'latitude':south,'longitude':west},'high':{'latitude':north,'longitude':east}}}})
                        leads=[]
                        for p in raw.get('places',[]):
                            if p.get('businessStatus')=='CLOSED_PERMANENTLY':continue
                            url=website(p.get('websiteUri'));official=url if url and not directory(url) else None
                            leads.append(recommendation({'id':'google:'+p['id'],'name':p.get('displayName',{}).get('text','Sem nome'),'city':city,'address':p.get('formattedAddress'),'category':args.category,'cuisine':None,'brand':None,'seats':None,'phone':p.get('nationalPhoneNumber'),'rating':p.get('rating'),'rating_count':p.get('userRatingCount'),'website':official,'site_status':'listed' if official else 'unverified','evidence':[{'source':'Google Maps / Places','url':p.get('googleMapsUri','https://maps.google.com/'),'note':'Site informado no cadastro.' if official else 'Site não informado neste cadastro; verificar outras fontes.'}],'checked_at':None}))
                        attribution='Dados do Google Maps / Places. Avaliações são opiniões dos usuários, não uma certificação de qualidade.'
                    else:
                        osm_type=place.get('osm_type');osm_id=int(place.get('osm_id',0))
                        if osm_type=='relation':region=f'area({3600000000+osm_id})->.city;';area='(area.city)'
                        elif osm_type=='way':region=f'area({2400000000+osm_id})->.city;';area='(area.city)'
                        else:
                            region='';area=f'(around:15000,{float(place["lat"])},{float(place["lon"])})'
                        tag={'hotel':'tourism','loja':'shop','barbearia':'shop','academia':'leisure','imobiliaria':'office','servicos':'office'}.get(args.category,'amenity')
                        cuisine_filter=f'["cuisine"~"{cuisine}"]' if cuisine else ''
                        query=f'[out:json][timeout:8];{region}nwr["{tag}"~"^({amenity})$"]["name"]{cuisine_filter}{area};out tags center 100;'
                        raw=None
                        source_errors=[]
                        source_deadline=time.monotonic()+32
                        for endpoint in ('https://overpass-api.de/api/interpreter',):
                            for method in ('POST','GET'):
                                if time.monotonic()>=source_deadline:break
                                try:
                                    async with asyncio.timeout(min(10,max(.1,source_deadline-time.monotonic()))):
                                        data=await fetch_json(client,method,endpoint,**({'data':{'data':query}} if method=='POST' else {'params':{'data':query}}))
                                    if not isinstance(data,dict) or data.get('remark') or not isinstance(data.get('elements'),list):raise ValueError('Map format')
                                    raw=data;break
                                except (httpx.HTTPError,HTTPException,TimeoutError,ValueError):
                                    source_errors.append(urlsplit(endpoint).hostname+' '+method)
                            if raw is not None:break
                        discovery_source='overpass';poi_responded=False
                        if raw is None:
                            # A bounded, user-triggered amenity search, not an exhaustive
                            # download, grid scan or background municipality sweep.
                            try:
                                await asyncio.sleep(max(0,1.1-(time.monotonic()-self.last_geocode)))
                                self.last_geocode=time.monotonic()
                                south,north,west,east=map(float,place['boundingbox'])
                                term=amenity.split('|')[0]
                                async with asyncio.timeout(10):
                                    points=await fetch_json(client,'GET','https://nominatim.openstreetmap.org/search',params={
                                        'q':'['+term+'] '+args.city+', Brasil','countrycodes':'br','format':'jsonv2','addressdetails':1,'extratags':1,
                                        'limit':min(args.limit,20),'bounded':1,'viewbox':f'{west},{north},{east},{south}'})
                                if not isinstance(points,list):raise ValueError('Business search format')
                                elements=[];valid_business_seen=False
                                for point in points:
                                    if not isinstance(point,dict) or point.get('address',{}).get('country_code')!='br':continue
                                    if point.get('class',point.get('category'))!=tag or not re.fullmatch(amenity,point.get('type','')):continue
                                    if point.get('osm_type') not in {'node','way','relation'} or not str(point.get('osm_id','')).isdigit():continue
                                    valid_business_seen=True
                                    extra=point.get('extratags') or {};address=point.get('address') or {}
                                    tags={**extra,tag:point['type'],'name':point.get('name') or point.get('display_name','').split(',')[0],
                                          'addr:street':address.get('road',''),'addr:housenumber':address.get('house_number',''),'addr:suburb':address.get('suburb','')}
                                    if cuisine and not re.search(cuisine,tags.get('cuisine','')):continue
                                    elements.append({'type':point['osm_type'],'id':point['osm_id'],'tags':tags})
                                poi_responded=not points or valid_business_seen
                                if elements:raw={'elements':elements};discovery_source='nominatim'
                            except (httpx.HTTPError,HTTPException,TimeoutError,ValueError,KeyError,TypeError,AttributeError):pass
                        if raw is None:
                            for endpoint in ('https://overpass.kumi.systems/api/interpreter','https://overpass.private.coffee/api/interpreter'):
                                for method in ('POST','GET'):
                                    if time.monotonic()>=source_deadline:break
                                    try:
                                        async with asyncio.timeout(min(10,max(.1,source_deadline-time.monotonic()))):
                                            data=await fetch_json(client,method,endpoint,**({'data':{'data':query}} if method=='POST' else {'params':{'data':query}}))
                                        if not isinstance(data,dict) or data.get('remark') or not isinstance(data.get('elements'),list):raise ValueError('Map format')
                                        raw=data;break
                                    except (httpx.HTTPError,HTTPException,TimeoutError,ValueError):continue
                                if raw is not None:break
                        if raw is None and poi_responded:raw={'elements':[]};discovery_source='nominatim'
                        if raw is None:raise HTTPException(502,'As fontes de negócios não responderam. A cidade foi localizada, mas os servidores de mapas falharam em POST/GET. Use Tentar pesquisa novamente ou Google Places se estiver configurado. Nenhum resultado foi inventado.')
                        if raw.get('remark'):raise HTTPException(502,'A pesquisa do mapa foi interrompida. Tente uma categoria mais específica.')
                        leads=[lead for item in raw.get('elements',[]) if item.get('type') in {'node','way','relation'} and (lead:=osm_lead(item,city))]
                        attribution='© colaboradores do OpenStreetMap (ODbL). '+('Consulta pontual pelo Nominatim, até 20 resultados.' if discovery_source=='nominatim' else 'Consulta pelo Overpass.')+' A cobertura varia por cidade; não é uma lista de todos os negócios.'
                    unique={}
                    for lead in leads:
                        key=(lead['name'].casefold(),lead.get('address'));unique.setdefault(key,lead)
                    report={'id':str(uuid4()),'city':city,'category':args.category,'source':args.source,'discovery_source':discovery_source if args.source=='osm' else 'google','created_at':datetime.now(timezone.utc).isoformat(),'cached':False,'leads':list(unique.values())[:args.limit],'attribution':attribution,'location_note':location_note,'coverage':('Pesquisa em um raio de 15 km do centro informado; ' if args.source=='osm' and place.get('osm_type')=='node' else '')+'Amostra de até 100 registros no mapa ou 20 no Google Places. Não realiza varredura nacional nem confirma interesse em contratar.','warnings':['Porte desconhecido não significa pequeno. Site não informado não significa inexistente.']}
                    if len(self.reports)>=8:
                        oldest=next(iter(self.reports));self.reports.pop(oldest)
                        self.cache={k:v for k,v in self.cache.items() if v[1]!=oldest}
                    self.reports[report['id']]=report;self.cache[cache_key]=(time.monotonic(),report['id'])
                    return report
            except httpx.HTTPError:raise HTTPException(502,'Não consegui acessar a fonte de negócios. Confira a conexão ou tente mais tarde; nenhum resultado foi inventado.') from None

    async def verify(self,args,registry):
        report=self.reports.get(args.report_id)
        lead=next((l for l in (report or {}).get('leads',[]) if l['id']==args.lead_id),None)
        if not lead:raise HTTPException(404,'Resultado não encontrado. Faça a pesquisa novamente.')
        if self.verify_lock.locked():raise HTTPException(409,'Outra verificação está em andamento.')
        async with self.verify_lock:
            results=[];queries=[]
            for suffix in ('site oficial','website contato'):
                query=f'"{lead["name"]}" "{report["city"].split(",")[0]}" {suffix}'
                result=await registry.execute('web_search',{'query':query,'limit':5},uuid4())
                if result['status']!='completed':
                    lead['verification_error']=result.get('error','Busca externa indisponível.');return recommendation(lead)
                queries.append(query);results.extend(result.get('result') or [])
            evidence=list(lead['evidence'][:1]);candidates=[]
            name_words=set(re.findall(r'\w+',lead['name'].casefold()))-{'restaurante','pizzaria','cafe','bar','da','do','de','e'}
            for item in results:
                url=website(item.get('href') or item.get('url'))
                if not url:continue
                title=str(item.get('title',''))[:250];snippet=str(item.get('body',''))[:500]
                evidence.append({'source':'Busca web','url':url,'note':title+' — '+snippet})
                words=set(re.findall(r'\w+',(title+' '+snippet).casefold()))
                if not directory(url) and name_words and name_words.intersection(words):candidates.append(url)
            prior=lead.get('website')
            if prior and candidates and any(hostname(prior)==hostname(url) for url in candidates):lead['site_status']='found'
            elif prior:lead['site_status']='listed'
            elif candidates:lead['website']=candidates[0];lead['site_status']='candidate'
            else:lead['site_status']='no_site_found'
            lead['evidence']=evidence[:11];lead['queries']=queries;lead['checked_at']=datetime.now(timezone.utc).isoformat();lead.pop('verification_error',None)
            lead['verification_note']='Nenhum processo de busca prova inexistência de site ou intenção de contratar. Confirme com o responsável; candidatos podem ser homônimos.'
            return recommendation(lead)


def install_prospects(app,authenticate):
    app.state.prospects=Prospector()
    def allowed():
        if app.state.engine.settings.privacy_mode!='online' or not app.state.panels.preferences.web_enabled:
            raise HTTPException(403,'Prospecção online desativada pelo modo local ou pela permissão de busca.')
    @app.get('/prospects/config',dependencies=[Depends(authenticate)])
    async def config():return {'google_configured':bool(os.getenv('GOOGLE_PLACES_API_KEY','').strip()),'categories':list(CATEGORIES),'country':'BR'}
    @app.post('/prospects/search',dependencies=[Depends(authenticate)])
    async def search(args:ProspectSearch):allowed();return await app.state.prospects.search(args)
    @app.post('/prospects/verify',dependencies=[Depends(authenticate)])
    async def verify(args:VerifyInput):allowed();return await app.state.prospects.verify(args,app.state.registry)
