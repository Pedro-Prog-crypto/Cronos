"""Original Eye UI in real Cronos, on-demand Node service and keyboard lifecycle.
External imagery/feeds are unavailable fixtures, not claimed live verification.
"""
import asyncio,threading,tempfile,socket,json
from pathlib import Path
import uvicorn
from playwright.async_api import async_playwright,expect
from cronos.app import create_app
from cronos.config import Settings
ROOT=Path(__file__).resolve().parents[2]
async def main():
 with tempfile.TemporaryDirectory() as directory:
  folder=Path(directory);personality=folder/'personality.md';personality.write_text('Assistente de teste.')
  settings=Settings(folder/'vault',personality,'eye-browser-test','gemini','','test','','','s1','http://127.0.0.1:11434','none',gemini_transport='rest')
  app=create_app(settings)
  listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
  server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
  thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
  while not server.started:await asyncio.sleep(.05)
  try:
   async with async_playwright() as p:
    browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
    page=await browser.new_page(viewport={'width':1366,'height':768})
    await page.add_init_script("navigator.mediaDevices.getUserMedia=async()=>{const ctx=new AudioContext(),dest=ctx.createMediaStreamDestination();return dest.stream;};")
    errors=[];failed=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:failed.append((r.status,r.url)) if r.status>=400 and f'127.0.0.1:{port}' in r.url else None)
    async def route(r):
     url=r.request.url
     if url.startswith(f'http://127.0.0.1:{port}/'):
      if '/api/' in url and '/api/cronos/' not in url and '/api/setup/' not in url:
       await r.fulfill(status=503,json={'error':'External feed fixture unavailable'});return
      await r.continue_();return
     await r.fulfill(status=503,body='External imagery unavailable in browser fixture')
    await page.route('**/*',route)
    await page.goto(f'http://127.0.0.1:{port}/#cronos-session=eye-browser-test')
    await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
    await page.keyboard.press('F4')
    await expect(page.get_by_role('button',name='Ligar microfone')).to_have_attribute('aria-pressed','false')
    await page.locator('.eye-slot').click()
    frame=page.frame_locator('.world-map-frame')
    await expect(frame.locator('.cesium-widget>canvas')).to_be_visible(timeout=45000)
    await expect(frame.locator('#loading-screen')).to_be_hidden(timeout=45000)
    assert await frame.locator('body').evaluate('async()=> (await document.fonts.load(\'24px "Material Symbols Outlined"\')).length')>0
    assert 'Material Symbols Outlined' in await frame.locator('.material-symbols-outlined').first.evaluate('e=>getComputedStyle(e).fontFamily')
    box=await page.locator('.eye-slot.expanded').bounding_box()
    assert box=={'x':0,'y':0,'width':1366,'height':768},box
    await expect(page.get_by_role('button',name='Fechar Olho de Deus')).to_be_visible()
    assert app.state.eye.process is not None and app.state.eye.process.poll() is None
    await frame.locator('[data-first-run-suppress]').check()
    await frame.locator('[data-first-run-choice=explore]').click()
    await frame.locator('.cesium-widget>canvas').click(position={'x':650,'y':450})
    await page.keyboard.press('F4')
    await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
    await page.keyboard.press('F4')
    await expect(page.get_by_role('button',name='Ligar microfone')).to_have_attribute('aria-pressed','false')
    await frame.locator('#gev-voice-button').click()
    await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
    await page.keyboard.press('F4')
    await expect(page.get_by_role('button',name='Ligar microfone')).to_have_attribute('aria-pressed','false')
    await page.screenshot(path='/tmp/cronos-eye-original-fullscreen.png')
    await page.get_by_role('button',name='Fechar Olho de Deus').click()
    await expect(page.locator('.world-map-frame')).to_have_count(0)
    for _ in range(60):
     if app.state.eye.process is None:break
     await asyncio.sleep(.1)
    assert app.state.eye.process is None,'Closing must stop the data-service child'
    await page.locator('.eye-slot').click()
    await expect(page.frame_locator('.world-map-frame').locator('.cesium-widget>canvas')).to_be_visible(timeout=45000)
    await expect(page.frame_locator('.world-map-frame').locator('#loading-screen')).to_be_hidden(timeout=45000)
    await page.keyboard.press('Escape')
    await expect(page.locator('.world-map-frame')).to_have_count(0)
    assert not errors,(errors,failed[:15])
    assert not [item for item in failed if '/eye/' in item[1] or item[1].endswith('.svg')],failed[:15]
    print('PASS: original UI initializes with actual Cesium canvas and Node providers; full viewport, X, F4 inside/outside iframe, close stops child, reopen/ESC work. External feeds and imagery unavailable fixtures.')
    await browser.close()
  finally:
   server.should_exit=True;await asyncio.to_thread(thread.join,10);listener.close()
asyncio.run(main())
