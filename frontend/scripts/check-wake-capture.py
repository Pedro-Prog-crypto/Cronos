"""Actual WebRTC/worklet capture; controlled keyword and cloud-provider fixtures."""
import asyncio,base64,http.server,threading,json,io,wave
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
SPEECH=base64.b64encode((ROOT/'frontend/scripts/fixtures/speech-16k.pcm').read_bytes()).decode()
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def end_headers(self):
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'")
  super().end_headers()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'],headless=True)
  page=await browser.new_page(viewport={'width':1366,'height':900})
  await page.add_init_script("window.testSpeech='"+SPEECH+"';"+"""window.pywebview={api:{connection:async()=>({token:'test'})}};window.micOpens=0;navigator.mediaDevices.getUserMedia=async()=>{micOpens++;const ctx=new AudioContext(),dest=ctx.createMediaStreamDestination(),voice=ctx.createBufferSource(),gain=ctx.createGain(),noise=ctx.createBufferSource(),ng=ctx.createGain();const pcm=new Int16Array(Uint8Array.from(atob(testSpeech),c=>c.charCodeAt(0)).buffer);voice.buffer=ctx.createBuffer(1,pcm.length,16000);voice.buffer.copyToChannel(Float32Array.from(pcm,v=>v/32768),0);voice.loop=true;voice.connect(gain);gain.connect(dest);gain.gain.value=0;noise.buffer=ctx.createBuffer(1,16000,16000);let seed=17;const data=noise.buffer.getChannelData(0);for(let i=0;i<data.length;i++){seed=(Math.imul(seed,1664525)+1013904223)|0;data[i]=seed/2147483648;}noise.loop=true;noise.connect(ng);ng.connect(dest);ng.gain.value=0;voice.start();noise.start();window.micGain=gain;window.noiseGain=ng;window.micStream=dest.stream;return dest.stream;};""")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':False,'fish_speech_configured':False,'transcription_provider':'vosk','direct_audio_chat':True,'local_voice_interrupt':True}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':True,'called_only':True}}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  await page.route('**/panels/latency',lambda r:r.fulfill(json={}))
  calls=[];recognition=[]
  async def chat(r):
   frames=r.request.post_data_buffer
   with wave.open(io.BytesIO(frames),'rb') as wav:assert (wav.getframerate(),wav.getnchannels())==(16000,1)
   calls.append(await page.evaluate('performance.now()'))
   events=[{'type':'transcript','text':'Cronos, explique filosofia'},{'type':'result','result':{'reply':'Explicação recebida.','recognized_text':'Cronos, explique filosofia','session_id':'wake-fixture','tool_results':[]}}]
   await r.fulfill(body='\n'.join(json.dumps(e) for e in events)+'\n',content_type='application/x-ndjson')
  await page.route('**/chat/audio/stream*',chat)
  async def asr(r):recognition.append(True);await r.fulfill(json={'text':'Ambiente'})
  await page.route('**/voice/transcribe',asr)
  sockets=[];pcm=[]
  async def keyword(socket):
   sockets.append(socket)
   def receive(message):
    if isinstance(message,str):assert json.loads(message)=={'token':'test'};socket.send(json.dumps({'type':'ready'}))
    else:pcm.append(message)
   socket.on_message(receive)
  await page.route_web_socket('**/voice/interrupt',keyword)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
  await page.wait_for_timeout(500)
  # Real speech alone must not reach either cloud conversation or ASR.
  await page.evaluate('()=>{micGain.gain.value=.25;setTimeout(()=>micGain.gain.value=0,850)}')
  await page.wait_for_timeout(2300)
  assert not calls and not recognition and pcm
  assert await page.locator('.reference-mic.recording').count()==1
  # Keyword is recognized while the utterance is already being buffered.
  start=await page.evaluate('()=>{noiseGain.gain.value=.004;micGain.gain.value=.25;setTimeout(()=>micGain.gain.value=0,850);return performance.now()}')
  await page.wait_for_timeout(250);sockets[-1].send(json.dumps({'type':'keyword','word':'Cronos'}))
  for _ in range(50):
   if calls:break
   await page.wait_for_timeout(100)
  assert len(calls)==1 and calls[0]-start-850<3000, ('voice must close despite the continuing fan-like noise',len(calls),await page.locator('.reference-mic').get_attribute('title'),await page.locator('.reference-mic').get_attribute('class'))
  await page.wait_for_timeout(1200)
  assert len(calls)==1 and await page.evaluate('micOpens===1&&micStream.getAudioTracks()[0].readyState==="live"')
  # An additional spoken phrase still requires a fresh Cronos activation.
  await page.evaluate('()=>{micGain.gain.value=.25;setTimeout(()=>micGain.gain.value=0,850)}')
  await page.wait_for_timeout(2300);assert len(calls)==1
  if await page.locator('.study-cinema-close').count():await page.locator('.study-cinema-close').click()
  await page.get_by_role('button',name='Desligar microfone').click()
  assert await page.evaluate('micStream.getAudioTracks()[0].readyState')=='ended'
  print('PASS: actual voice without a wake word sends no cloud/ASR request; a woken question closes with continuous noise in '+str(round(calls[0]-start-850))+' ms after speech stops; exactly one request, microphone stays open, and a fresh phrase needs a new wake word. Keyword/provider responses mocked.')
  await browser.close()
try:asyncio.run(main())
finally:server.shutdown()
