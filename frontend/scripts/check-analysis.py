"""Exercise image/ZIP previews, explicit analysis, cancellation, local commands and scene."""
import asyncio,http.server,threading,json,io,zipfile
from functools import partial
from pathlib import Path
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'],headless=True)
  page=await browser.new_page(viewport={'width':1600,'height':900},device_scale_factor=1)
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'test'})}}")
  await page.route('**/status',lambda r:r.fulfill(json={'privacy_mode':'online','fish_configured':False,'fish_speech_configured':False}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':False}}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/sync',lambda r:r.fulfill(json={}))
  graph={'nodes':[{'path':f'notes/{i}.md','title':f'Nota de teste {i}'} for i in range(300)],'edges':[{'source':f'notes/{i}.md','target':f'notes/{i//3}.md'} for i in range(1,300)],'total':300,'next_offset':None}
  await page.route('**/memory/graph?*',lambda r:r.fulfill(json=graph))
  image=ROOT/'frontend/src/assets/images/news_ai_safety_1791817511005.jpg'
  analyses=[];release=asyncio.Event()
  await page.route('**/vision/preview',lambda r:r.fulfill(body=image.read_bytes(),content_type='image/jpeg'))
  async def analyze(r):
   data=json.loads(r.request.post_data);analyses.append(data);assert data['consent'] is True
   await release.wait();await r.fulfill(json={'reply':'Esta é a análise real retornada pelo provedor de teste.'})
  await page.route('**/vision/analyze',analyze)
  await page.route('**/documents/analyze',analyze)
  await page.route('**/documents/preview',lambda r:r.fulfill(json={'files':[{'name':'main.py','truncated':False}],'skipped':['.env'],'truncated':False}))
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.locator('canvas[data-render-thread=worker]')).to_have_count(1)
  await expect(page.locator('.memory-node')).to_have_count(300)
  before=await page.locator('canvas').screenshot();await page.wait_for_timeout(250);assert before!=await page.locator('canvas').screenshot(), 'hologram must actually move'
  assert await page.locator('.holographic-globe,.world-map-frame,.eye-slot').count()==0
  assert await page.locator('.cosmic-starfield').count()==1 and await page.locator('.cosmic-star').count()==38
  await page.get_by_role('button',name='Analisar imagem',exact=True).click()
  await page.get_by_label('Selecionar imagem',exact=True).set_input_files(str(image))
  await expect(page.locator('.analysis-panel img')).to_be_visible()
  assert not analyses and await page.locator('.analysis-scan').count()==0
  await page.get_by_label('Pergunta sobre o arquivo').fill('Explique a imagem.')
  await page.get_by_role('button',name='Analisar',exact=True).click()
  await expect(page.locator('.analysis-panel.is-scanning')).to_be_visible()
  await page.wait_for_timeout(500)
  assert analyses[0]['prompt']=='Explique a imagem.' and analyses[0]['image_base64']
  await page.wait_for_timeout(8200) # let the isolated fixture's missing-voice startup notice expire
  await page.screenshot(path='/tmp/cronos-interface-analysis-preview.png')
  release.set()
  await expect(page.locator('.analysis-result')).to_contain_text('provedor de teste')
  await expect(page.locator('.analysis-scan')).to_have_count(0)
  await page.get_by_role('button',name='Fechar análise').click()
  await page.get_by_role('button',name='Analisar ZIP ou código',exact=True).click()
  await page.get_by_label('Selecionar ZIP ou código',exact=True).set_input_files({'name':'project.zip','mimeType':'application/zip','buffer':b'fixture ZIP preview handled by mock'})
  await expect(page.locator('.analysis-file-list')).to_contain_text('main.py')
  assert len(analyses)==1
  await page.get_by_role('button',name='Analisar',exact=True).click()
  await expect(page.locator('.analysis-result')).to_be_visible()
  assert analyses[-1]['name']=='project.zip' and analyses[-1]['data_base64']
  await page.keyboard.press('Escape');await expect(page.locator('.analysis-panel')).to_have_count(0)
  # A natural spoken/typed upload request opens a chooser panel locally, no Gemini call.
  await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
  await page.locator('#chat-input').fill('Cronos, quero que você analise uma imagem')
  await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
  await expect(page.get_by_role('region',name='Análise de imagem',exact=True)).to_be_visible()
  await page.keyboard.press('Escape')
  # A preview/read error cannot leave a pretend scanning animation running.
  await page.route('**/vision/preview',lambda r:r.fulfill(status=422,json={'detail':'Imagem inválida de teste'}))
  await page.get_by_role('button',name='Analisar imagem',exact=True).click()
  await page.get_by_label('Selecionar imagem',exact=True).set_input_files(str(image))
  await expect(page.get_by_role('alert')).to_contain_text('Imagem inválida de teste')
  assert await page.locator('.analysis-scan').count()==0
  assert not errors,errors
  await page.set_viewport_size({'width':1366,'height':768})
  box=await page.locator('.analysis-panel').bounding_box();assert box and box['x']>=0 and box['x']+box['width']<=1366
  # Removing all notes also removes the spiral and its decorative dust, not the starfield.
  graph.update(nodes=[],edges=[],total=0)
  await page.reload();await page.wait_for_timeout(500)
  assert await page.locator('.memory-spiral').count()==0
  assert len(page.context.pages)==1
  print('PASS: native image/ZIP selection, preview without cloud call, consent-bound analysis, live scanner, returned result, ESC, local analysis command, clear errors, bounded layout; no idle globe and no invented memories. Providers mocked.')
  await browser.close()
try:asyncio.run(main())
finally:server.shutdown()
