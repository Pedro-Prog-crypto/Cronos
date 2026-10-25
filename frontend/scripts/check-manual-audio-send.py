"""Browser integration check for the microphone's explicit Send Now fallback."""
import asyncio,http.server,json,threading
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect

ROOT=Path(__file__).resolve().parents[2]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def end_headers(self):
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'")
  super().end_headers()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'],headless=True)
  page=await browser.new_page(viewport={'width':1366,'height':900})
  await page.add_init_script("""window.pywebview={api:{connection:async()=>({token:'test'})}};navigator.mediaDevices.getUserMedia=async()=>{const c=new AudioContext(),o=c.createOscillator(),g=c.createGain(),d=c.createMediaStreamDestination();o.connect(g);g.connect(d);g.gain.value=.002;o.start();window.micStream=d.stream;return d.stream};""")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':False,'fish_speech_configured':False,'transcription_provider':'vosk'}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':True}}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  await page.route('**/panels/latency',lambda r:r.fulfill(json={}))
  uploads=[];chats=[]
  async def transcribe(route):
   uploads.append(route.request.post_data_buffer)
   await route.fulfill(json={'text':'Cronos, explique uma pergunta enviada manualmente'})
  async def chat(route):
   chats.append(True);reply='Resposta de teste.'
   await route.fulfill(body='\n'.join(json.dumps(e) for e in [{'type':'reply','reply':reply},{'type':'result','result':{'reply':reply,'session_id':'manual-send','tool_results':[]}}])+'\n',content_type='application/x-ndjson')
  await page.route('**/voice/transcribe',transcribe);await page.route('**/chat/stream',chat)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
  await expect(page.get_by_role('button',name='Enviar fala agora')).to_be_enabled()
  await page.wait_for_timeout(650)
  await page.get_by_role('button',name='Enviar fala agora').click()
  for _ in range(40):
   if uploads:break
   await page.wait_for_timeout(100)
  assert len(uploads)==1 and len(uploads[0])>6400,('manual send should transcribe the buffered voice immediately',len(uploads),len(uploads[0]) if uploads else 0)
  for _ in range(30):
   if chats:break
   await page.wait_for_timeout(100)
  assert len(chats)==1
  assert await page.evaluate('micStream.getAudioTracks()[0].readyState')=='live'
  print('PASS: Send Now submits buffered audio before silence detection; the microphone remains open.')
  await browser.close()
try:asyncio.run(main())
finally:server.shutdown()
