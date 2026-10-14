"""Actual streamed response: cards appear before the remaining answer arrives."""
import asyncio,http.server,threading,json
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2];release=threading.Event();finished=threading.Event();calls=[]
INTRO='## Contexto\nTomás de Aquino viveu no século XIII. '
REPLY=INTRO+'\n\n## Exemplo\nCompare a razão que examina argumentos com a fé que parte da revelação.'
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  if self.path!='/chat/stream':self.send_error(404);return
  calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
  self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.end_headers()
  try:
   self.wfile.write((json.dumps({'type':'intro','reply':INTRO})+'\n').encode());self.wfile.flush()
   release.wait(10)
   for data in [{'type':'reply','reply':REPLY},{'type':'result','result':{'reply':REPLY,'session_id':'preview-test','tool_results':[]}}]:self.wfile.write((json.dumps(data)+'\n').encode())
   self.wfile.flush();finished.set()
  except (BrokenPipeError,ConnectionResetError):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':900})
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'test'})}}")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':False,'fish_speech_configured':False}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':False}}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  await page.route('**/panels/latency',lambda r:r.fulfill(json={'recorded':True}))
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  async def ask(text):
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill(text);await page.get_by_role('button',name='Enviar mensagem').click()
  await ask('Explique Tomás de Aquino em cards')
  await expect(page.get_by_role('heading',name='Contexto',exact=True)).to_be_visible()
  assert not finished.is_set(),'the first card must appear before full generation finishes'
  release.set();await expect(page.get_by_role('heading',name='Exemplo',exact=True)).to_be_visible()
  await ask('ocultar os cards');await expect(page.locator('.answer-card-deck')).to_have_count(0)
  await ask('Cronos, abrir texto na tela');await expect(page.get_by_role('heading',name='Exemplo',exact=True)).to_be_visible()
  assert len(calls)==1,'display commands must not regenerate the answer'
  print('PASS: first card appears during real streaming, final sections replace it, and exact open-text command restores the full cached answer without another AI request.')
  await browser.close()
try:asyncio.run(main())
finally:release.set();server.shutdown()
