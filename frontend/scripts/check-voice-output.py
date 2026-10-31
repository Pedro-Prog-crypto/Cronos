"""Real Web Audio playback with stale output preferences; Fish responses are fixtures."""
import asyncio,http.server,threading,io,wave,math,struct
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
PCM=b''.join(struct.pack('<h',int(2500*math.sin(2*math.pi*220*i/24000))) for i in range(12000))
output=io.BytesIO()
with wave.open(output,'wb') as writer:
 writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(24000);writer.writeframes(PCM)
WAV=output.getvalue()
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
  for streaming,volume,unsupported in [(False,.8,True),(True,.8,False),(False,0,False)]:
   page=await browser.new_page(viewport={'width':1366,'height':768})
   await page.add_init_script("""window.pywebview={api:{connection:async()=>({token:'test'})}};window.audioStarts=0;window.pcmStarts=0;window.sinks=[];
const nativePlay=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){window.audioStarts++;return nativePlay.call(this)};
const nativeStart=AudioBufferSourceNode.prototype.start;AudioBufferSourceNode.prototype.start=function(...args){window.pcmStarts++;return nativeStart.apply(this,args)};
navigator.mediaDevices.enumerateDevices=async()=>[];
"""+("AudioContext.prototype.setSinkId=undefined;" if unsupported else "AudioContext.prototype.setSinkId=async function(id){window.sinks.push(id)};"))
   calls=[];errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':True,'fish_speech_configured':True,'fish_pcm_streaming':streaming,'privacy_mode':'online'}))
   await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':False,'voice_volume':volume,'output_label':'Saída salva que não existe'}}))
   await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
   await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
   await page.route('**/updates',lambda r:r.fulfill(json={'state':{'phase':'idle'},'release':{},'suggestions':[]}))
   async def speech(route):
    calls.append(route.request.post_data_json)
    if streaming:await route.fulfill(body=PCM,content_type='audio/x-pcm',headers={'X-PCM-Sample-Rate':'24000'})
    else:await route.fulfill(body=WAV,content_type='audio/wav')
   await page.route('**/voice/speech',speech);await page.route('**/voice/pcm',speech)
   await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('Cronos, na escuta?');await page.get_by_role('button',name='Enviar mensagem').click()
   if volume:
    await page.wait_for_function('()=>window.audioStarts+window.pcmStarts>0')
    await expect(page.locator('.scene-notice')).to_contain_text('Usando a saída padrão')
    assert calls==[{'text':'Estou na escuta.','speed':1} ] or calls==[{'text':'Estou na escuta.'}],calls
    if streaming:assert await page.evaluate('sinks.length===0'),'A new default context must not require optional sink APIs'
   else:
    await expect(page.locator('.scene-notice')).to_contain_text('volume da voz está em zero')
    assert not calls and await page.evaluate('audioStarts+pcmStarts')==0
   assert not errors,errors
   await page.close()
  await browser.close()
  print('PASS: stale device/unsupported output API uses default output and real WAV/PCM fixtures play; muted volume is explained without synthesis; no provider calls or alternate voice.')
try:asyncio.run(main())
finally:server.shutdown()
