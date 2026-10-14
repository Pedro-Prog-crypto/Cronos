"""Browser flow through real prospect API, with deterministic external source fixtures."""
import asyncio,http.server,threading,tempfile,json
from pathlib import Path
from functools import partial
from urllib.parse import urlsplit
import httpx
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright,expect
from cronos.app import create_app
from cronos.config import Settings
from cronos.providers import ProviderError
ROOT=Path(__file__).resolve().parents[2]
TOKEN='prospects-browser-test'
PLACE={'display_name':'Manaus, Amazonas, Brasil','osm_type':'relation','osm_id':123,'address':{'country_code':'br','city':'Manaus'},'boundingbox':['-3.2','-2.9','-60.2','-59.8']}
ITEMS=[{'type':'node','id':1,'tags':{'name':'Cantina Aurora','amenity':'restaurant','capacity:seats':'30'}},{'type':'node','id':2,'tags':{'name':'Grande Rede','amenity':'restaurant','capacity:seats':'180','brand':'Rede','website':'https://grandeficticia.example'}}]
original=httpx.AsyncClient
async def handle(r):
 if r.url.host=='nominatim.openstreetmap.org':return httpx.Response(200,json=[PLACE])
 if r.url.host=='overpass-api.de':return httpx.Response(200,json={'elements':ITEMS})
 raise AssertionError('Unexpected external destination')
httpx.AsyncClient=lambda **kw:original(transport=httpx.MockTransport(handle),trust_env=False,**kw)
class Provider:
 async def reply(self,system,messages):return {'reply':'Minha sugestão é começar com HTML e CSS, cardápio e contato.','topics':[],'tool_calls':[]}
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main(client):
 async def websearch(args):return [{'title':'Cantina Aurora','href':'https://instagram.com/cantina','body':'Perfil de Manaus'}]
 client.app.state.registry.tools['web_search'].handler=websearch
 client.app.state.panels.preferences.device_auto_connect=False
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':900})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'"+TOKEN+"'})}}")
  async def backend(route):
   url=urlsplit(route.request.url)
   if url.path.startswith('/ui/'):await route.continue_();return
   response=client.request(route.request.method,url.path+('?' +url.query if url.query else ''),content=route.request.post_data_buffer,headers={'Authorization':'Bearer '+TOKEN,**({'Content-Type':route.request.headers['content-type']} if 'content-type' in route.request.headers else {})})
   await route.fulfill(status=response.status_code,body=response.content,content_type=response.headers.get('content-type','application/json'))
  await page.route('**/*',backend)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await page.get_by_role('button',name='INTERNET',exact=True).click()
  await page.get_by_role('button',name='PROSPECÇÃO DE CLIENTES · BRASIL').click()
  panel=page.get_by_role('dialog',name='Prospecção de clientes');await expect(panel).to_be_visible()
  await page.get_by_label('Cidade e estado',exact=True).fill('Manaus, AM')
  await page.get_by_role('button',name='Buscar oportunidades').click()
  await expect(page.locator('.prospect-results article')).to_have_count(2)
  await page.get_by_label('Porte do negócio').select_option('pequeno')
  await expect(page.locator('.prospect-results article')).to_have_count(1)
  await expect(page.get_by_role('heading',name='Cantina Aurora')).to_be_visible()
  await page.get_by_role('button',name='Cruzar fontes sobre o site').click()
  await expect(page.get_by_role('heading',name='Nenhum site próprio encontrado — confirmar')).to_be_visible()
  await page.get_by_label('Presença de site').select_option('no_site_found')
  await expect(page.locator('.prospect-results article')).to_have_count(1)
  async with page.expect_download() as download:
   await page.get_by_role('button',name='Exportar resultados filtrados').click()
  data=json.loads(Path(await (await download.value).path()).read_text())
  assert len(data['leads'])==1 and data['leads'][0]['name']=='Cantina Aurora'
  await page.get_by_role('button',name='Pensar neste projeto com o Kronos').click()
  await expect(panel).to_have_count(0)
  await expect(page.get_by_text('Minha sugestão é começar com HTML e CSS, cardápio e contato.',exact=True)).to_be_visible()
  assert not errors,errors
  print('PASS: real API-backed panel, city search, size/site filters, multi-query verification, filtered export and programming conversation. External feeds mocked.')
  await browser.close()
try:
 with tempfile.TemporaryDirectory() as directory:
  path=Path(directory);personality=path/'persona.md';personality.write_text('Ajude a programar com evidências.')
  settings=Settings(path/'vault',personality,TOKEN,'gemini','','test','','','s1','http://127.0.0.1:11434','none',gemini_transport='rest')
  with TestClient(create_app(settings,provider=Provider()),base_url='http://127.0.0.1',client=('127.0.0.1',50000)) as client:asyncio.run(main(client))
finally:server.shutdown();httpx.AsyncClient=original
