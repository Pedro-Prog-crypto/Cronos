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
  await page.route('**/voice/transcribe',lambda r:r.fulfill(json={'text':'Fale sobre Sócrates.'}))
  reply='Sócrates foi um filósofo ateniense conhecido por suas perguntas. '+'Seu método questionava definições e procurava contradições. '*14
  await page.route('**/chat',lambda r:r.fulfill(json={'reply':reply,'session_id':'latency-session','tool_results':[]}))
  parts=[];completed=[]
  async def speech(route):
   text=json.loads(route.request.post_data)['text'];parts.append(text);index=len(parts)
   await asyncio.sleep(.05 if index!=2 else 1.8)
   completed.append(index);await route.fulfill(body=AUDIO,content_type='audio/wav')
  await page.route('**/voice/speech',speech)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html');await page.wait_for_timeout(1800)
  assert await page.locator('canvas[data-render-thread=worker]').count()==2
  before=await page.locator('canvas').first.evaluate('c=>c.toDataURL()');await page.wait_for_timeout(150);assert before!=await page.locator('canvas').first.evaluate('c=>c.toDataURL()')
  start={m['name']:m['value'] for m in (await c.send('Performance.getMetrics'))['metrics']};await page.wait_for_timeout(3000);end={m['name']:m['value'] for m in (await c.send('Performance.getMetrics'))['metrics']}
  print('Main-thread task seconds / 3 seconds at 4x:',round(end['TaskDuration']-start['TaskDuration'],3),flush=True)
  await page.evaluate('''()=>{navigator.mediaDevices.getUserMedia=async()=>{await new Promise(r=>setTimeout(r,500));const ctx=new AudioContext(),osc=ctx.createOscillator(),gain=ctx.createGain(),dest=ctx.createMediaStreamDestination();osc.connect(gain);gain.connect(dest);gain.gain.value=.1;osc.start();setTimeout(()=>gain.gain.value=0,700);return dest.stream;};}''')
  await page.get_by_role('button',name='Gravar pelo microfone').click();await expect(page.locator('.reference-mic')).to_have_attribute('title','Abrindo microfone',timeout=400)
  await expect(page.locator('.reference-mic')).to_have_attribute('title','Microfone ligado',timeout=3000)
  await page.wait_for_function('()=>window.playTimes.length===1',timeout=20000)
  assert 2 not in completed,'first audio waited for second chunk'
  assert len(parts[0])<len(reply)
  assert await page.locator('.spoken-question,.answer-card-deck,.conversation-drawer,.card-composer').count()==0
  await page.wait_for_function('()=>document.querySelector(".reference-mic").title==="Microfone desligado"',timeout=20000)
  assert ''.join(parts)==reply
  assert len(await page.evaluate('window.playTimes'))==len(parts)
  print('PASS: two active workers, visible animation, starting/recording feedback, no automatic boxes during speech, early playback before delayed next chunk, ordered full speech.',flush=True)
  # Ask explicitly for the written response; the same saved turn is displayed.
  await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('#chat-input').fill('mostrar resposta');await page.get_by_role('button',name='Enviar mensagem').click()
  await expect(page.locator('.answer-card-deck')).to_contain_text('Sócrates')
  # A buffered next chunk must not resume after Stop.
  await page.evaluate('window.playTimes=[]')
  await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('#chat-input').fill('Outra pergunta');await page.get_by_role('button',name='Enviar mensagem').click()
  await page.wait_for_function('()=>window.playTimes.length===1',timeout=10000)
  await page.get_by_role('button',name='Gravar pelo microfone').click();await page.wait_for_timeout(1500)
  assert len(await page.evaluate('window.playTimes'))==1
  assert await page.locator('.reference-mic').get_attribute('title')=='Microfone desligado'
  # Starting a fresh recording immediately hides cards from the previous typed turn.
  await page.get_by_role('button',name='Gravar pelo microfone').click()
  await expect(page.locator('.reference-mic')).to_have_attribute('title','Abrindo microfone',timeout=400)
  assert await page.locator('.spoken-question,.answer-card-deck,.card-composer').count()==0
  print('PASS: stopping cancels the queued continuation; previous cards hide at microphone activation.',flush=True)
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
