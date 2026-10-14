"""Real streaming HTTP plus browser Web Audio; no external API or hardware audio."""
import asyncio,http.server,threading,json,math,struct,os,time
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
PCM=b''.join(struct.pack('<h',int(4000*math.sin(2*math.pi*220*i/24000))) for i in range(4800))
release=threading.Event();requests=[];finished=[]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  if self.path!='/voice/pcm':self.send_error(404);return
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(body['text']);index=len(requests)
  self.send_response(200);self.send_header('Content-Type','audio/x-pcm');self.send_header('X-PCM-Sample-Rate','24000');self.end_headers()
  try:
   # Split an odd-sized network block to exercise PCM byte carry.
   self.wfile.write(PCM[:3]);self.wfile.flush();self.wfile.write(PCM[3:]);self.wfile.flush()
   release.wait(5)
   self.wfile.write(PCM);self.wfile.flush()
  except (BrokenPipeError,ConnectionResetError):pass
  finally:finished.append(index)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=os.getenv('CRONOS_TEST_CHROMIUM') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required','--use-fake-ui-for-media-stream'])
  page=await browser.new_page(viewport={'width':1366,'height':768},permissions=['microphone'])
  await page.add_init_script("""window.pywebview={api:{connection:async()=>({token:'test'})}};window.starts=0;const start=AudioBufferSourceNode.prototype.start;AudioBufferSourceNode.prototype.start=function(...a){window.starts++;return start.apply(this,a)};navigator.mediaDevices.getUserMedia=async()=>{const ctx=new AudioContext(),dest=ctx.createMediaStreamDestination();return dest.stream;};""")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':True,'fish_speech_configured':True,'fish_pcm_streaming':True,'transcription_provider':'vosk'}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/graph?*',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  await page.route('**/memory/sync',lambda r:r.fulfill(json={}))
  await page.route('**/panels/latency',lambda r:r.fulfill(json={'recorded':True}))
  reply='Sócrates foi um filósofo grego conhecido por suas perguntas. '+'Seu método questionava definições e examinava argumentos. '*5
  await page.route('**/chat/stream',lambda r:r.fulfill(body=json.dumps({'type':'result','result':{'reply':reply,'session_id':'test','tool_results':[]}})+'\n',content_type='application/x-ndjson'))
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  async def ask():
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('Quem foi Sócrates?');await page.get_by_role('button',name='Enviar mensagem').click()
  await ask()
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title.startsWith("Falando")',timeout=10000)
  assert not finished,'playback must start before the provider finishes the response'
  assert await page.evaluate('window.starts')>0
  await page.keyboard.press('Escape');stopped=await page.evaluate('window.starts');release.set()
  await page.wait_for_timeout(800);assert await page.evaluate('window.starts')==stopped,'ESC must stop queued PCM and late packets'
  requests.clear();finished.clear()
  await ask();await page.wait_for_function('(n)=>window.starts>n',arg=stopped,timeout=10000)
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title==="Microfone ligado"',timeout=10000)
  assert ''.join(requests)==reply,'streaming must preserve the full reply without duplicating words'
  print('PASS: PCM starts before complete synthesis; odd network byte boundaries decode, ESC stops queued/late audio, and the next complete reply plays in order.')
  await browser.close()
try:asyncio.run(main())
finally:release.set();server.shutdown()
