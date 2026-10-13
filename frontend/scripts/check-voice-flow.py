"""Optional browser integration test; simulated providers and a synthetic test tone only."""
import asyncio,http.server,threading,json,time,io,math,struct,wave,os
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
def test_audio():
 buffer=io.BytesIO()
 with wave.open(buffer,'wb') as writer:
  writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(24000)
  writer.writeframes(b''.join(struct.pack('<h',int(4000*math.sin(2*math.pi*220*i/24000))) for i in range(23280)))
 return buffer.getvalue()
AUDIO=test_audio()
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def end_headers(self):
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
  super().end_headers()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')));threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path=os.getenv('CRONOS_TEST_CHROMIUM') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None),headless=True,args=['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required']);page=await b.new_page(viewport={'width':1366,'height':768},permissions=['microphone'])
  c=await page.context.new_cdp_session(page);await c.send('Performance.enable');await c.send('Emulation.setCPUThrottlingRate',{'rate':4})
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'test'})}};window.playTimes=[];const originalPlay=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){this.addEventListener('playing',()=>window.playTimes.push(performance.now()),{once:true});return originalPlay.call(this)}")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':True,'fish_speech_configured':True,'transcription_provider':'vosk'}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/sync',lambda r:r.fulfill(json={}))
  await page.route('**/memory/graph?*',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  asr=[];transcript=['Fale sobre Sócrates.'];chats=[]
  async def transcribe(route):
   body=route.request.post_data_buffer
   with wave.open(io.BytesIO(body),'rb') as reader:assert (reader.getframerate(),reader.getnchannels(),reader.getsampwidth())==(16000,1,2)
   asr.append(body);await route.fulfill(json={'text':transcript[0]})
  await page.route('**/voice/transcribe',transcribe)
  reply='Sócrates foi um filósofo ateniense conhecido por suas perguntas. '+'Seu método questionava definições e procurava contradições. '*14
  async def chat(route):
   chats.append(route.request.post_data);await route.fulfill(json={'reply':reply,'session_id':'latency-session','tool_results':[]})
  await page.route('**/chat',chat)
  parts=[];completed=[]
  async def speech(route):
   text=json.loads(route.request.post_data)['text'];parts.append(text);index=len(parts)
   await asyncio.sleep(.05 if index!=2 else 1.8)
   completed.append(index);await route.fulfill(body=AUDIO,content_type='audio/wav')
  await page.route('**/voice/speech',speech)
  await page.add_init_script("""window.micOpens=0;navigator.mediaDevices.getUserMedia=async()=>{window.micOpens++;await new Promise(r=>setTimeout(r,300));const ctx=new AudioContext(),osc=ctx.createOscillator(),gain=ctx.createGain(),dest=ctx.createMediaStreamDestination();osc.connect(gain);gain.connect(dest);gain.gain.value=0;osc.start();window.micGain=gain;window.micStream=dest.stream;return dest.stream;};""")
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true',timeout=7000)
  assert await page.locator('canvas[data-render-thread=worker]').count()==2
  before=await page.locator('canvas').first.evaluate('c=>c.toDataURL()');await page.wait_for_timeout(150);assert before!=await page.locator('canvas').first.evaluate('c=>c.toDataURL()')
  async def say():
   await page.evaluate('()=>{micGain.gain.value=.15;setTimeout(()=>micGain.gain.value=0,650)}')
  await say();await page.wait_for_function('()=>window.playTimes.length===1',timeout=20000)
  assert 2 not in completed
  # Simulate the assistant's sound reaching the input while it is speaking.
  await page.evaluate('()=>{micGain.gain.value=.15;setTimeout(()=>micGain.gain.value=0,700)}')
  assert await page.locator('.spoken-question,.answer-card-deck,.conversation-drawer,.card-composer').count()==0
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title==="Microfone ligado"',timeout=20000)
  assert ''.join(parts)==reply
  assert len(await page.evaluate('window.playTimes'))==len(parts)
  count=len(parts);played=len(await page.evaluate('window.playTimes'))
  await page.wait_for_timeout(9000)
  assert await page.evaluate('micStream.getAudioTracks()[0].readyState')=='live'
  assert await page.evaluate('micOpens')==1 and len(parts)==count
  await say();await page.wait_for_function('(n)=>window.playTimes.length>n',arg=played,timeout=20000)
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title==="Microfone ligado"',timeout=20000)
  assert await page.evaluate('micOpens')==1 and len(asr)==2
  # A spoken UI command must bypass Gemini and load the actual map engine on demand.
  assert await page.locator('.world-map-frame').count()==0
  world_policy="default-src 'self'; script-src 'self' blob: 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob: https://server.arcgisonline.com; media-src 'none'; connect-src 'self' https://server.arcgisonline.com; worker-src 'self' blob:; object-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'"
  await page.route('**/world/view',lambda r:r.fulfill(body=(ROOT/'cronos/ui/world.html').read_bytes(),content_type='text/html',headers={'Content-Security-Policy':world_policy}))
  await page.route('https://server.arcgisonline.com/**',lambda r:r.fulfill(status=204,headers={'Access-Control-Allow-Origin':'*'}))
  transcript[0]='Kronos, você pode abrir o olho de Deus, por favor?'
  speech_before_eye=len(parts);playing_before_eye=len(await page.evaluate('window.playTimes'))
  await say()
  await expect(page.locator('.eye-slot.expanded')).to_be_visible(timeout=20000)
  await expect(page.frame_locator('.world-map-frame').locator('.cesium-widget canvas')).to_be_visible(timeout=20000)
  await page.wait_for_function('(n)=>window.playTimes.length>n',arg=playing_before_eye,timeout=20000)
  assert len(parts)>speech_before_eye and 'Olho de Deus aberto' in parts[-1]
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title==="Microfone ligado"',timeout=20000)
  assert len(chats)==2 and len(asr)==3
  transcript[0]='Kronos, feche o olho de Deus'
  await page.wait_for_timeout(900)  # allow the deliberately short post-speech echo guard
  await say();await expect(page.locator('.world-map-frame')).to_have_count(0,timeout=20000)
  assert len(chats)==2
  print('PASS: spoken natural eye command opens real Cesium canvas without Gemini; closing unmounts it. External imagery not validated.',flush=True)
  await page.get_by_role('button',name='Desligar microfone').click()
  await expect(page.get_by_role('button',name='Ligar microfone')).to_have_attribute('aria-pressed','false')
  assert await page.evaluate('micStream.getAudioTracks()[0].readyState')=='ended'
  await page.get_by_role('button',name='Ligar microfone').click()
  await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
  assert await page.evaluate('micOpens')==2
  print('PASS: automatic persistent microphone, silence does not disable it, two turns reuse one stream, manual off/on, no voice boxes, early full ordered speech, active workers.',flush=True)
  await page.get_by_role('button',name='Desligar microfone').click()
  await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('#chat-input').fill('mostrar resposta');await page.get_by_role('button',name='Enviar mensagem').click()
  await expect(page.locator('.answer-card-deck')).to_contain_text('Sócrates')
  # The same drawing code must remain functional on older WebView2 without workers/offscreen.
  fallback=await b.new_page(viewport={'width':1366,'height':768})
  await fallback.add_init_script('window.Worker=undefined;window.OffscreenCanvas=undefined')
  await fallback.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html');await fallback.wait_for_timeout(500)
  assert await fallback.locator('canvas[data-render-thread=worker]').count()==0
  image=await fallback.locator('canvas').first.evaluate('c=>c.toDataURL()');await fallback.wait_for_timeout(180)
  assert image!=await fallback.locator('canvas').first.evaluate('c=>c.toDataURL()')
  print('PASS: explicit show-text command and older-WebView fallback drawing.',flush=True)
  transferred=await b.new_page(viewport={'width':1366,'height':768})
  await transferred.add_init_script("Worker.prototype.postMessage=function(){throw new Error('simulated transfer failure')}")
  await transferred.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html');await transferred.wait_for_timeout(500)
  assert await transferred.locator('canvas[data-render-thread=worker]').count()==0
  image=await transferred.locator('canvas').first.evaluate('c=>c.toDataURL()');await transferred.wait_for_timeout(180)
  assert image!=await transferred.locator('canvas').first.evaluate('c=>c.toDataURL()')
  print('PASS: a failure after canvas transfer recreates a usable fallback canvas.',flush=True)
  await b.close()
try:asyncio.run(main())
finally:server.shutdown()
