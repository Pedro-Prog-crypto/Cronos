"""Exercise commands, player messages, cancelled searches and actual Web Audio cleanup."""
import asyncio,http.server,threading,json,os
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
s=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=s.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'],headless=True)
  page=await b.new_page(viewport={'width':1366,'height':900})
  await page.add_init_script("""window.pywebview={api:{connection:async()=>({token:'test'})}};window.musicMessages=[];window.tones=[];const create=AudioContext.prototype.createOscillator;AudioContext.prototype.createOscillator=function(){const o=create.call(this);window.tones.push({context:this,oscillator:o});return o;};""")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':False,'fish_speech_configured':False,'transcription_provider':'vosk'}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':False}}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  requests=[];release=asyncio.Event()
  async def search(r):
   requests.append(r.request.url)
   if 'Slow' in r.request.url:await release.wait()
   await r.fulfill(json={'tracks':[{'id':'abcdefghijk','title':'Song'}],'search_url':'https://www.youtube.com/watch?v=abcdefghijk'})
  await page.route('**/music/search?*',search)
  player="""<html><body>Embedded player fixture<script>window.addEventListener('message',e=>{try{const d=JSON.parse(e.data);if(d.event==='command')parent.postMessage(JSON.stringify({event:'fixture',func:d.func}),'*')}catch{}});</script></body></html>"""
  await page.route('https://www.youtube-nocookie.com/embed/**',lambda r:r.fulfill(body=player,content_type='text/html'))
  await page.goto(f'http://127.0.0.1:{s.server_port}/ui/index.html')
  await page.evaluate("window.addEventListener('message',e=>{try{const d=JSON.parse(e.data);if(d.event==='fixture')window.musicMessages.push(d.func)}catch{}})")
  async def command(text):
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
   await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill(text)
   await page.get_by_role('button',name='Enviar mensagem').click()
  assert await page.locator('.music-player').count()==0
  await command('Kronos, colocar música Evidências')
  await page.locator('.music-player iframe').wait_for()
  assert 'abcdefghijk' in await page.locator('.music-player iframe').get_attribute('src')
  await page.get_by_role('button',name='Pausar',exact=True).click()
  await page.wait_for_function("window.musicMessages.includes('pauseVideo')")
  await page.get_by_role('button',name='Continuar',exact=True).click()
  await page.wait_for_function("window.musicMessages.includes('playVideo')")
  await command('Kronos, tocar frequência 528 Hz')
  await page.wait_for_function('window.tones.length===1')
  assert await page.evaluate('window.tones[0].oscillator.frequency.value')==528
  await page.get_by_role('button',name='Pausar',exact=True).click()
  await page.wait_for_function("window.tones[0].context.state==='suspended'")
  await page.get_by_role('button',name='Continuar',exact=True).click()
  await page.wait_for_function("window.tones[0].context.state==='running'")
  await page.keyboard.press('Escape')
  await page.wait_for_function("window.tones[0].context.state==='closed'")
  assert await page.locator('.music-player').count()==0
  await command('tocar música Slow')
  await page.locator('.music-player').wait_for()
  await page.keyboard.press('Escape');release.set()
  await page.wait_for_timeout(500)
  assert await page.locator('.music-player').count()==0
  print('PASS: commands mount official embed, pause/resume messaging, 528Hz real oscillator, ESC closes audio and prevents late search revival. External YouTube playback is mocked, not verified.')
  await b.close()
try:asyncio.run(main())
finally:s.shutdown()
