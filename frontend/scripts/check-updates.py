"""Browser authorization/progress flow, with no network providers, installations or keys."""
import asyncio,http.server,json,threading
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
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'browser-test-only'})}}")
  page.on('dialog',lambda d:asyncio.create_task(d.accept()))
  report={'state':{'phase':'idle','message':'Em espera','progress':0},'release':{'available':True,'revision':'a'*40,'summary':'Atualização de teste'},'managed':True,'suggestions':[]}
  installs=[];requests=[];errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  async def backend(route):
   path=__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(route.request.url).path
   if path.startswith(('/ui/','/static/')):await route.continue_();return
   requests.append(path)
   if path=='/status':await route.fulfill(json={'fish_configured':False,'fish_speech_configured':False,'privacy_mode':'online'});return
   if path=='/panels':await route.fulfill(json={'preferences':{'called_only':True,'auto_index':False}});return
   if path=='/memory/graph':await route.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None});return
   if path=='/memory/sync':await route.fulfill(json={'synced':True});return
   if path=='/monitor':await route.fulfill(json={'cursor':0,'alerts':[],'events':[]});return
   if path=='/updates':await route.fulfill(json=report);return
   if path=='/updates/prepare':
    report['state']={'phase':'ready','id':'b'*32,'message':'Cópia preparada','progress':45,'origin':'ai'}
    await route.fulfill(json={'id':'b'*32,'installed':False});return
   if path.startswith('/updates/proposal/'):
    await route.fulfill(json={'id':'b'*32,'summary':'Melhoria de teste','test_plan':'Exercitar a função alterada','diffs':[{'path':'cronos/engine.py','diff':'-old\n+new'}],'functional_tests_run':False});return
   if path=='/updates/install':
    installs.append(route.request.post_data_json)
    report['state']={'phase':'queued','id':'b'*32,'message':'Backup concluído','progress':50}
    await route.fulfill(json={'queued':True});return
   if path=='/updates/dismiss':await route.fulfill(json={'dismissed':True});return
   await route.fulfill(status=404,json={'detail':'fixture unavailable'})
  await page.route('**/*',backend)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.get_by_role('button',name='Preparar cópia')).to_be_visible()
  assert not installs
  await page.get_by_role('button',name='Preparar cópia').click()
  await expect(page.get_by_role('button',name='Revisar alterações')).to_be_visible()
  assert not installs
  # AI proposal cannot be applied without opening the concrete diff.
  await page.get_by_role('button',name='Autorizar backup e instalar').click()
  await expect(page.get_by_text('Exercitar a função alterada',exact=False)).to_be_visible()
  assert not installs
  await page.get_by_role('button',name='Autorizar backup e instalar').click()
  await expect(page.get_by_role('progressbar',name='Progresso da atualização')).to_be_visible()
  assert installs==[{'id':'b'*32}]
  report['state']={'phase':'completed','id':'b'*32,'message':'Atualização instalada. Recarregue a página.','progress':100}
  report['release']['available']=False
  await expect(page.get_by_role('button',name='Recarregar página')).to_be_visible(timeout=8000)
  assert not any(p.startswith('/chat') or p.startswith('/voice/speech') for p in requests)
  assert len(page.context.pages)==1 and not errors,errors
  print('PASS: no install before human authorization; AI diff review required; backup/install request, real state progress, and reload control; no provider calls or external page.')
  await browser.close()
try:asyncio.run(main())
finally:server.shutdown()
