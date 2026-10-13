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
DIRECT=os.getenv('CRONOS_TEST_DIRECT_AUDIO')=='1'
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
  latencies=[]
  async def latency(route):
   latencies.append(json.loads(route.request.post_data));await route.fulfill(json={'recorded':True})
  await page.route('**/panels/latency',latency)
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':True,'fish_speech_configured':True,'transcription_provider':'vosk','direct_audio_chat':DIRECT}))
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
   chats.append(route.request.post_data);await route.fulfill(body='\n'.join(json.dumps(event) for event in [{'type':'intro','reply':reply[:reply.index('. ')+2]},{'type':'reply','reply':reply},{'type':'result','result':{'reply':reply,'session_id':'latency-session','tool_results':[]}}])+'\n',content_type='application/x-ndjson')
  await page.route('**/chat/stream',chat)
  async def direct_chat(route):
   body=route.request.post_data_buffer
   with wave.open(io.BytesIO(body),'rb') as reader:assert (reader.getframerate(),reader.getnchannels(),reader.getsampwidth())==(16000,1,2)
   asr.append(body);chats.append('native-audio')
   events=[{'type':'transcript','text':transcript[0]},{'type':'intro','reply':reply[:reply.index('. ')+2]},{'type':'reply','reply':reply},{'type':'result','result':{'reply':reply,'recognized_text':transcript[0],'session_id':'latency-session','tool_results':[]}}]
   await route.fulfill(body='\n'.join(json.dumps(event) for event in events)+'\n',content_type='application/x-ndjson')
  await page.route('**/chat/audio/stream*',direct_chat)

  parts=[];completed=[];speech_events=[]
  async def speech(route):
   text=json.loads(route.request.post_data)['text'];parts.append(text);index=len(parts);speech_events.append(('requested',index))
   await asyncio.sleep(.05 if index!=2 else 1.8)
   completed.append(index);speech_events.append(('completed',index));await route.fulfill(body=AUDIO,content_type='audio/wav')
  await page.route('**/voice/speech',speech)
  await page.add_init_script("""window.micOpens=0;navigator.mediaDevices.getUserMedia=async()=>{window.micOpens++;await new Promise(r=>setTimeout(r,300));const ctx=new AudioContext(),osc=ctx.createOscillator(),gain=ctx.createGain(),dest=ctx.createMediaStreamDestination();osc.connect(gain);gain.connect(dest);gain.gain.value=0;osc.start();window.micGain=gain;window.micStream=dest.stream;return dest.stream;};""")
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true',timeout=7000)
  assert await page.locator('canvas[data-render-thread=worker]').count()==1
  assert await page.locator('.function-tree animateMotion').count()==0
  assert await page.locator('.cosmic-star').count()==38
  before=await page.locator('canvas').first.evaluate('c=>c.toDataURL()');await page.wait_for_timeout(150);assert before!=await page.locator('canvas').first.evaluate('c=>c.toDataURL()')
  async def say(gain=.15):
   await page.evaluate('(gain)=>{micGain.gain.value=gain;setTimeout(()=>micGain.gain.value=0,650)}',gain)
  await say(.008);await page.wait_for_function('()=>window.playTimes.length===1',timeout=20000)
  await page.wait_for_timeout(100)
  assert latencies[-1]['source']=='voice' and latencies[-1]['first_audio_ms']>=latencies[-1]['chat_ms']
  assert latencies[-1]['recognition_ms']>=0 and latencies[-1]['speech_request_ms']>0
  assert 'question' not in latencies[-1] and 'text' not in latencies[-1]
  assert 2 not in completed
  assert speech_events.index(('requested',2))<speech_events.index(('completed',1)), 'continuation synthesis must start before the introduction finishes'
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
  assert len(chats)==(len(asr) if DIRECT else 2) and len(asr)==3
  transcript[0]='Kronos, feche o olho de Deus'
  await page.wait_for_timeout(900)  # allow the deliberately short post-speech echo guard
  await say();await expect(page.locator('.world-map-frame')).to_have_count(0,timeout=20000)
  assert len(chats)==(len(asr) if DIRECT else 2)
  print('PASS: spoken natural eye command opens real Cesium canvas and closing unmounts it; text commands stay local, native-audio commands use one recognition turn. External imagery not validated.',flush=True)
  before_map_escape=len(await page.evaluate('window.playTimes'))
  await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
  await page.locator('#chat-input').fill('abrir olho de Deus');await page.get_by_role('button',name='Enviar mensagem').click()
  await expect(page.frame_locator('.world-map-frame').locator('.cesium-widget canvas')).to_be_visible(timeout=20000)
  await page.wait_for_function('(n)=>window.playTimes.length>n',arg=before_map_escape,timeout=20000)
  await page.frame_locator('.world-map-frame').locator('.cesium-widget canvas').click()
  await page.keyboard.press('Escape');await expect(page.locator('.world-map-frame')).to_have_count(0)
  assert len(chats)==(len(asr) if DIRECT else 2)
  print('PASS: ESC with focus inside map reaches parent and stops/closes it.',flush=True)
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title==="Microfone ligado"',timeout=20000)
  await page.wait_for_timeout(900)
  transcript[0]='Cronos, na escuta?';before_presence=len(await page.evaluate('window.playTimes'))
  await say();await page.wait_for_function('(n)=>window.playTimes.length>n',arg=before_presence,timeout=20000)
  assert parts[-1]=='Estou na escuta.' and len(chats)==(len(asr) if DIRECT else 2)
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title==="Microfone ligado"',timeout=20000)
  print('PASS: presence check speaks through configured voice without chat generation or knowledge turn.',flush=True)
  await page.get_by_role('button',name='Desligar microfone').click()
  await expect(page.get_by_role('button',name='Ligar microfone')).to_have_attribute('aria-pressed','false')
  assert await page.evaluate('micStream.getAudioTracks()[0].readyState')=='ended'
  await page.get_by_role('button',name='Ligar microfone').click()
  await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
  assert await page.evaluate('micOpens')==2
  print('PASS: automatic persistent microphone, silence does not disable it, two turns reuse one stream, manual off/on, no voice boxes, early full ordered speech, active workers.',flush=True)
  await page.get_by_role('button',name='Desligar microfone').click()
  await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click();await page.locator('#chat-input').fill('mostrar resposta');await page.get_by_role('button',name='Enviar mensagem').click()
  await expect(page.locator('.answer-card-deck')).to_contain_text('Sócrates')
  # ESC must interrupt current audio and suppress a response that was still pending.
  async def ask(text):
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill(text);await page.get_by_role('button',name='Enviar mensagem').click()
  played=len(await page.evaluate('window.playTimes'))
  await ask('Teste de interrupção da fala')
  await page.wait_for_function('(n)=>window.playTimes.length>n',arg=played,timeout=20000)
  await page.keyboard.press('Escape');stopped=len(await page.evaluate('window.playTimes'))
  await page.wait_for_timeout(2500);assert len(await page.evaluate('window.playTimes'))==stopped
  async def delayed_chat(route):
   await asyncio.sleep(1.5)
   try:await route.fulfill(body=json.dumps({'type':'result','result':{'reply':'Resposta atrasada que não deve tocar.','session_id':'cancelled','tool_results':[]}})+'\n',content_type='application/x-ndjson')
   except Exception:pass  # the client deliberately aborted this request
  await page.route('**/chat/stream',delayed_chat)
  await ask('Cancelar antes da resposta');await page.wait_for_timeout(100);await page.keyboard.press('Escape')
  await page.wait_for_timeout(2000);assert len(await page.evaluate('window.playTimes'))==stopped
  await page.unroute('**/chat/stream',delayed_chat)
  await ask('Nova pergunta após cancelar')
  await page.wait_for_function('(n)=>window.playTimes.length>n',arg=stopped,timeout=20000)
  await page.keyboard.press('Escape')
  print('PASS: ESC stops audio, pending chunks and late chat response; a new question works afterwards.',flush=True)
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
