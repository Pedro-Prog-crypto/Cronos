"""Native HTML audio/video playback with generated media; external catalogs mocked."""
import asyncio,http.server,threading,json,math,struct,wave,io,tempfile,subprocess
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
buffer=io.BytesIO()
with wave.open(buffer,'wb') as out:
 out.setnchannels(1);out.setsampwidth(2);out.setframerate(8000)
 out.writeframes(b''.join(struct.pack('<h',int(2000*math.sin(2*math.pi*220*i/8000))) for i in range(160000)))
WAV=buffer.getvalue()
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main(mp4):
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'],headless=True)
  page=await browser.new_page(viewport={'width':1366,'height':900})
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'test'})}}")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':False,'fish_speech_configured':False}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':False}}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  release=asyncio.Event();calls=[]
  async def search(r):
   calls.append(r.request.url)
   if 'Slow' in r.request.url:await release.wait()
   await r.fulfill(json={'tracks':[{'id':'abcdefghijk','title':'Nada pra Fazer'},{'id':'12345678901','title':'Outra música'}]})
  await page.route('**/music/search?*',search)
  async def resolve(r):
   clip='video=true' in r.request.url
   await r.fulfill(json={'audio_url':'https://rr1.googlevideo.com/audio','video_url':'https://rr1.googlevideo.com/video' if clip else None,'title':'Nada pra Fazer'})
  await page.route('**/music/resolve?*',resolve)
  async def stream(r,content,mime):
   import re
   requested=r.request.headers.get('range','');match=re.match(r'bytes=(\d+)-(\d*)',requested)
   if match:
    start=int(match[1]);end=min(len(content)-1,int(match[2]) if match[2] else len(content)-1)
    await r.fulfill(status=206,body=content[start:end+1],content_type=mime,headers={'Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(content)}'})
   else:await r.fulfill(body=content,content_type=mime,headers={'Accept-Ranges':'bytes'})
  await page.route('https://rr1.googlevideo.com/audio',lambda r:stream(r,WAV,'audio/wav'))
  await page.route('https://rr1.googlevideo.com/video',lambda r:stream(r,mp4,'video/mp4'))
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  async def command(text):
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill(text);await page.get_by_role('button',name='Enviar mensagem').click()
  await command('Chronos, abre a música Nada pra Fazer')
  await page.wait_for_function('()=>document.querySelector(".music-player audio")?.currentTime>.1')
  assert await page.locator('.music-player iframe').count()==0
  assert 'Nada+pra+Fazer' in calls[0]
  await page.get_by_role('button',name='Pausar',exact=True).click()
  assert await page.locator('.music-player audio').evaluate('a=>a.paused')
  await page.get_by_label('Posição da música',exact=True).fill('3')
  await page.wait_for_timeout(200)
  assert await page.locator('.music-player audio').evaluate('a=>Math.abs(a.currentTime-3)<.2')
  await page.get_by_label('Volume da música',exact=True).fill('35')
  assert await page.locator('.music-player audio').evaluate('a=>Math.abs(a.volume-.35)<.01')
  await page.get_by_role('button',name='Continuar',exact=True).click()
  await page.wait_for_function('()=>document.querySelector(".music-player audio").currentTime>3.1')
  await command('Chronos, abre o clipe Nada pra Fazer')
  await page.wait_for_function('()=>document.querySelector(".music-player video")?.videoWidth===160&&document.querySelector(".music-player audio")?.currentTime>.2')
  await page.wait_for_timeout(900)
  assert await page.evaluate('Math.abs(document.querySelector(".music-player video").currentTime-document.querySelector(".music-player audio").currentTime)<.6')
  await page.get_by_role('button',name='Pausar',exact=True).click()
  assert await page.evaluate('document.querySelector(".music-player audio").paused&&document.querySelector(".music-player video").paused')
  await page.keyboard.press('Escape')
  assert await page.locator('.music-player audio,.music-player video,.music-player iframe').count()==0
  await command('tocar música Slow');await page.locator('.music-player').wait_for();await page.keyboard.press('Escape');release.set()
  await page.wait_for_timeout(500);assert await page.locator('.music-player').count()==0
  assert len(page.context.pages)==1 and not errors,errors
  print('PASS: native audio plays, pauses, seeks and changes volume; separate real MP4 video decodes and synchronizes; ESC removes players and cancels pending searches; no iframe or external tab. Catalog/stream addresses mocked.')
  await browser.close()
try:
 with tempfile.TemporaryDirectory() as directory:
  video=Path(directory)/'fixture.mp4'
  subprocess.run(['ffmpeg','-loglevel','error','-f','lavfi','-i','color=c=blue:s=160x90:r=10','-t','20','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
  asyncio.run(main(video.read_bytes()))
finally:server.shutdown()
