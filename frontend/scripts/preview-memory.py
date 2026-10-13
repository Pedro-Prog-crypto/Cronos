"""Render preview using synthetic notes; never writes to the real vault or calls AI APIs."""
import asyncio,http.server,threading,os
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
root=ROOT/'cronos'
output=ROOT/'.cronos-local'/'visual-preview'
output.mkdir(parents=True,exist_ok=True)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
  page=await b.new_page(viewport={'width':1902,'height':827},device_scale_factor=1,permissions=['microphone'])
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'preview'})}}")
  await page.route('**/status',lambda r:r.fulfill(json={'transcription_provider':'none'}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/sync',lambda r:r.fulfill(json={}))
  nodes=[{'path':f'Temas/Exemplo-{i:04d}.md','title':f'Nota de demonstração {i}'} for i in range(850)]
  edges=[{'source':nodes[i]['path'],'target':nodes[i+5]['path']} for i in range(0,800,11)]
  await page.route('**/memory/graph?*',lambda r:r.fulfill(json={'nodes':nodes,'edges':edges,'total':len(nodes),'next_offset':None}))
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await page.wait_for_selector('.memory-light-trails');await page.wait_for_timeout(1000)
  assert await page.locator('.memory-node').count()==850
  assert await page.locator('.memory-light-trails > g').count()==5
  await page.screenshot(path=str(output/'espiral-demonstracao-850-notas.png'))
  await page.unroute('**/memory/graph?*')
  await page.route('**/memory/graph?*',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  await page.reload();await page.wait_for_timeout(700)
  assert await page.locator('.memory-spiral').count()==0
  await page.screenshot(path=str(output/'cena-sem-memorias.png'))
  await b.close()
asyncio.run(main());server.shutdown()
