"""Stremio panel/command regression with metadata and Windows launch simulated."""
import asyncio,http.server,threading
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':900})
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'test'})}}")
  errors=[];opened=[];searches=[];chats=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  async def backend(route):
   from urllib.parse import urlsplit
   path=urlsplit(route.request.url).path
   if path.startswith(('/ui/','/static/')):await route.continue_();return
   if path=='/status':data={'fish_configured':False,'fish_speech_configured':False,'privacy_mode':'online'}
   elif path=='/panels':data={'preferences':{'device_auto_connect':False}}
   elif path=='/monitor':data={'cursor':0,'alerts':[],'events':[]}
   elif path=='/updates':data={'state':{},'release':{},'suggestions':[]}
   elif path.startswith('/memory/'):data={'nodes':[],'edges':[],'total':0,'next_offset':None}
   elif path=='/stremio/status':data={'protocol_registered':True,'internal_player':False}
   elif path=='/stremio/search':
    body=route.request.post_data_json;searches.append(body)
    data={**body,'items':[{'id':'tt0944947','name':body['query'],'kind':body['kind'],'year':'2011'}]}
   elif path=='/stremio/open':opened.append(route.request.post_data_json);data={'launch_requested':True,'played':False,'message':'Solicitação enviada ao Stremio instalado.'}
   else:
    if path.startswith('/chat'):chats.append(path)
    await route.fulfill(status=404,json={'detail':'Not mocked'});return
   await route.fulfill(json=data)
  await page.route('**/*',backend)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
  await page.locator('#chat-input').fill('Cronos, abrir a série Game of Thrones temporada 2 episódio 3')
  await page.get_by_role('button',name='Enviar mensagem').click()
  await expect(page.get_by_role('dialog',name='Filmes e séries no Stremio')).to_be_visible()
  await expect(page.get_by_role('status')).to_contain_text('Solicitação enviada ao Stremio instalado.')
  assert searches==[{'query':'Game of Thrones','kind':'series','season':2,'episode':3}]
  assert opened==[{'id':'tt0944947','kind':'series','season':2,'episode':3}]
  await page.get_by_label('Episódio',exact=True).fill('4')
  await page.get_by_role('button',name='Abrir no Stremio',exact=True).click()
  assert opened[-1]['episode']==4
  await page.get_by_role('button',name='Fechar Stremio').click()
  assert not errors and not chats and len(page.context.pages)==1,(errors,chats)
  print('PASS: local title/episode command, metadata result selection, exact-title opening and episode change; no Gemini call or external web tab. Windows/Stremio launch simulated.')
  await browser.close()
try:asyncio.run(main())
finally:server.shutdown()
