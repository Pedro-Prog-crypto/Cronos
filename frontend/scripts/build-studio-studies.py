"""Render actual local study pages into the gallery; no remote images or AI calls."""
import asyncio
import base64
import sys
import shutil
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cronos.studio.designs import COPY,site

async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1280,'height':920},device_scale_factor=.5)
  for category in COPY:
   assets=['f'*32+'.jpg'] if category=='restaurante' else []
   f=site(category,{'restaurante':'BAIXO FOGO','hotel':'CASA DO VENTO','loja':'MATÉRIA','lava_jato':'LÂMINA','portfolio':'INTERVALO'}.get(category,COPY[category][3]),assets=assets)
   html=f['index.html'].replace('<link rel="stylesheet" href="styles.css">','<style>'+f['styles.css']+'</style>').replace('<script src="app.js" defer></script>','')
   if assets:html=html.replace('assets/'+assets[0],'data:image/jpeg;base64,'+base64.b64encode((ROOT/'cronos/studio/media/restaurant-fire.jpg').read_bytes()).decode())
   await page.set_content(html,wait_until='load')
   output=ROOT/'frontend/public/assets'/('studio-'+category+'-preview.jpg');output.parent.mkdir(parents=True,exist_ok=True)
   await page.screenshot(path=str(output),type='jpeg',quality=86)
   shutil.copyfile(output,ROOT/'cronos/ui/assets'/output.name)
   if category=='restaurante':
    await page.screenshot(path='/tmp/cronos-restaurant-study-desktop.png',full_page=True)
    await page.set_viewport_size({'width':390,'height':844})
    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    await page.screenshot(path='/tmp/cronos-restaurant-study-mobile.png',full_page=True)
    await page.set_viewport_size({'width':1280,'height':920})
  await browser.close()
 print('PASS: rendered 13 real local gallery previews; restaurant desktop and mobile have no horizontal overflow.')

asyncio.run(main())
