import base64
import io
import json
import zipfile
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from cronos.app import create_app
from cronos.municipalities import lookup,entries
from cronos.documents import inspect_document
from cronos.vision import normalize_image
from cronos.upload_limits import MAX_UPLOAD_BYTES,MAX_BASE64_CHARS
from cronos.studio.service import prepare_asset
from cronos.studio.designs import site,COPY,family
from cronos.studio.validation import validate,Document
from test_backend import settings,AUTH
from test_studio import Builder,new
from test_prospects import ITEMS

CLIENT=httpx.AsyncClient

@pytest.mark.parametrize('query,uf',[('Brasília, DF','DF'),('Manaus AM','AM'),('Rio de Janeiro/RJ','RJ'),('São Paulo - SP','SP'),('Abadia de Goiás, GO','GO'),('Parintins, AM','AM')])
def test_local_city_centres_are_real_and_cover_brazil(query,uf):
 assert len(entries())>5500
 place=lookup(query)
 assert place and ', '+uf in place['display_name'] and -74<float(place['lon'])< -33 and -34<float(place['lat'])<6


def test_search_survives_geocoder_failure_and_post_blocking(settings,monkeypatch):
 seen=[]
 def respond(r):
  seen.append((r.url.host,r.method))
  if r.url.host=='nominatim.openstreetmap.org':return httpx.Response(503)
  if r.method=='POST':return httpx.Response(405)
  assert 'around:15000' in r.url.params['data']
  return httpx.Response(200,json={'elements':ITEMS})
 monkeypatch.setattr('cronos.prospects.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(respond),trust_env=False,**kw))
 with TestClient(create_app(settings,Builder())) as c:
  for city in ['Brasília, DF','Manaus, AM','Rio de Janeiro, RJ','Parintins, AM']:
   r=c.post('/prospects/search',headers=AUTH,json={'city':city})
   assert r.status_code==200,r.text
   assert len(r.json()['leads'])==3 and r.json()['location_note'] and '15 km' in r.json()['coverage']
  assert ('overpass-api.de','GET') in seen


def test_unknown_and_ambiguous_municipality_are_not_invented():
 assert lookup('Cidade que não existe, SP') is None
 assert lookup('Manaus, ZZ') is None
 from fastapi import HTTPException
 with pytest.raises(HTTPException):lookup('Bom Jesus')


@pytest.mark.parametrize('category',list(COPY))
def test_default_studies_have_valid_forms_and_no_repeated_benefits_grid(category):
 for template in ('basic','standard','premium'):
  result=site(category,'Estudo de teste',template=template)
  assert validate(result)['passed']
  assert 'three' not in result['app.js'].lower()
  assert 'data-filter' in result['app.js'] and 'data-studio-form="booking"' in result['index.html']
  assert 'ESTUDO FICTÍCIO' in result['index.html'] and 'Serviço de qualidade para seu negócio.' not in result['index.html']
 assert len({family('restaurante',x) for x in ('basic','standard','premium')})==3
 assert len({family(x) for x in COPY})>=4


def test_curated_restaurant_and_originals_remain_separate(settings):
 with TestClient(create_app(settings,Builder())) as c:
  a=new(c,category='restaurante',create_from_template=True)
  assert 'class="poster"' in a['current']['files']['index.html'] and a['assets'][0]['source']['kind']=='demo'
  assert validate(a['current']['files'],[a['assets'][0]['name']])['passed']
  b=new(c,category='restaurante',create_from_template=True,design='supplied')
  assert a['current']['files']!=b['current']['files'] and not b['assets']


def test_thirty_mib_image_is_accepted_and_normalized_and_oversize_is_rejected(settings):
 data=io.BytesIO();Image.new('RGB',(60,40),'blue').save(data,'JPEG')
 raw=data.getvalue()+b'\0'*(MAX_UPLOAD_BYTES-len(data.getvalue()))
 normalized=normalize_image(raw)
 assert len(base64.b64decode(normalized['data']))<2048
 prepared,ext,mime=prepare_asset(raw,'image','foto.jpg')
 assert ext=='jpg' and mime=='image/jpeg' and len(prepared)<2048
 with pytest.raises(ValueError):normalize_image(raw+b'x')
 with pytest.raises(ValueError):prepare_asset(raw+b'x','image','foto.jpg')
 with TestClient(create_app(settings,Builder())) as c:
  response=c.post('/vision/preview',headers=AUTH,content=raw)
  assert response.status_code==200,response.text
  assert c.post('/vision/preview',headers={**AUTH,'Content-Length':str(MAX_UPLOAD_BYTES+1)},content=b'x').status_code==413


def test_thirty_mib_text_is_bounded_in_ai_context_and_zip_expansion_is_checked():
 raw=b'a'*MAX_UPLOAD_BYTES
 text=inspect_document('main.txt',raw)
 assert text['characters']==24000 and text['truncated']
 data=io.BytesIO()
 with zipfile.ZipFile(data,'w',zipfile.ZIP_STORED) as z:z.writestr('main.txt',raw[:MAX_UPLOAD_BYTES-1024])
 assert len(data.getvalue())<MAX_UPLOAD_BYTES
 assert inspect_document('project.zip',data.getvalue())['truncated']
 with pytest.raises(ValueError):inspect_document('main.txt',raw+b'a')
 # Metadata exceeds the expansion budget; no potentially huge entry is read.
 data=io.BytesIO()
 with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
  for i in range(4):z.writestr(str(i)+'.txt',b'a'*(24*1024*1024))
 with pytest.raises(ValueError):inspect_document('bomb.zip',data.getvalue())


def test_bounded_public_search_is_a_real_reserve_when_map_servers_fail(settings,monkeypatch):
 calls=[]
 def respond(r):
  calls.append((r.url.host,r.method,dict(r.url.params)))
  if r.url.host=='nominatim.openstreetmap.org' and r.url.params.get('extratags')=='1':
   assert r.url.params['bounded']=='1' and int(r.url.params['limit'])<=20
   return httpx.Response(200,json=[{'osm_type':'node','osm_id':999,'category':'amenity','type':'restaurant','name':'Cantina pública de teste','address':{'country_code':'br','road':'Rua de teste'},'extratags':{'website':'https://example.org'}}])
  if r.url.host=='nominatim.openstreetmap.org':
   return httpx.Response(200,json=[{**lookup('Brasília, DF'),'osm_type':'node','addresstype':'city'}])
  return httpx.Response(503)
 monkeypatch.setattr('cronos.prospects.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(respond),trust_env=False,**kw))
 with TestClient(create_app(settings,Builder())) as c:
  response=c.post('/prospects/search',headers=AUTH,json={'city':'Brasília, DF'})
  assert response.status_code==200,response.text
  report=response.json()
  assert report['discovery_source']=='nominatim' and report['leads'][0]['name']=='Cantina pública de teste'
  assert report['leads'][0]['site_status']=='listed' and report['leads'][0]['website']=='https://example.org'
  n=len(calls)
  assert c.post('/prospects/search',headers=AUTH,json={'city':'Brasília, DF'}).json()['cached']
  assert len(calls)==n
