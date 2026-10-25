"""Real browser capture/playback; keyword server events are controlled fixtures."""
import asyncio,http.server,threading,json,io,wave,math,struct
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
buffer=io.BytesIO()
with wave.open(buffer,'wb') as writer:
 writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(8000)
 writer.writeframes(b''.join(struct.pack('<h',int(2000*math.sin(i*.12))) for i in range(40000)))
WAV=buffer.getvalue()
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def end_headers(self):
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'")
  super().end_headers()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'],headless=True)
  page=await browser.new_page(viewport={'width':1366,'height':900})
  await page.add_init_script("""window.pywebview={api:{connection:async()=>({token:'test'})}};window.micOpens=0;window.playCount=0;const originalPlay=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){window.playCount++;return originalPlay.call(this)};navigator.mediaDevices.getUserMedia=async()=>{window.micOpens++;const ctx=new AudioContext(),osc=ctx.createOscillator(),gain=ctx.createGain(),dest=ctx.createMediaStreamDestination();osc.connect(gain);gain.connect(dest);gain.gain.value=.01;osc.start();window.micGain=gain;window.micStream=dest.stream;return dest.stream;};""")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':True,'fish_speech_configured':True,'transcription_provider':'vosk','local_voice_interrupt':True}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':True,'called_only':True}}))
  await page.route('**/panels/latency',lambda r:r.fulfill(json={}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  chats=[];transcriptions=[]
  async def transcribe(r):transcriptions.append(True);await r.fulfill(json={'text':'Não deveria transcrever durante a fala'})
  await page.route('**/voice/transcribe',transcribe)
  async def chat(r):
   chats.append(True);reply='Uma explicação que deve parar quando você disser a palavra de interrupção. '+'Mais detalhes sobre o assunto. '*12
   await r.fulfill(body='\n'.join(json.dumps(e) for e in [{'type':'reply','reply':reply},{'type':'result','result':{'reply':reply,'session_id':'test','tool_results':[]}}])+'\n',content_type='application/x-ndjson')
  await page.route('**/chat/stream',chat)
  await page.route('**/voice/speech',lambda r:r.fulfill(body=WAV,content_type='audio/wav'))
  sockets=[];pcm=[]
  async def keyword(socket):
   sockets.append(socket)
   def receive(message):
    if isinstance(message,str):
     assert json.loads(message)=={'token':'test'};socket.send(json.dumps({'type':'ready'}))
    else:pcm.append(message)
   socket.on_message(receive)
  await page.route_web_socket('**/voice/interrupt',keyword)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
  async def ask():
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('Explique filosofia');await page.get_by_role('button',name='Enviar mensagem').click()
  await ask();await page.wait_for_function('()=>window.playCount>0')
  assert not transcriptions
  await expect(page.locator('.reference-mic.speaking')).to_have_count(1,timeout=2500)
  count=await page.evaluate('playCount');pcm_count=len(pcm)
  await page.wait_for_timeout(900)
  assert await page.evaluate('playCount')==count and await page.locator('.reference-mic.speaking').count()==1
  assert len(chats)==1 and len(pcm)==pcm_count, 'assistant playback must not arm keyword barge-in and cancel its own narration'
  assert await page.evaluate('micOpens===1&&micStream.getAudioTracks()[0].readyState==="live"')
  await page.keyboard.press('Escape')
  if await page.locator('.study-cinema-close').count():await page.locator('.study-cinema-close').click()
  await page.get_by_role('button',name='Desligar microfone').click()
  assert await page.evaluate('micStream.getAudioTracks()[0].readyState')=='ended'
  print('PASS: narration remains active during playback; Escape stops it explicitly; the microphone lifecycle remains stable.')
  await browser.close()
try:asyncio.run(main())
finally:server.shutdown()
