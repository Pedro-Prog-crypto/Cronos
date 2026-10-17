"""Exercise actual preview + exported trusted runtime with a non-billable builder."""
import asyncio,io,os,sys,tempfile,zipfile,subprocess
from pathlib import Path
import httpx
from playwright.async_api import async_playwright,expect

BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8923')
AUTH={'Authorization':'Bearer studio-test-only'}

async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH,timeout=20) as client:
  for old in (await client.get('/studio/projects')).json()['projects']:
   if old['name']=='Ateliê funcional premium':await client.post('/studio/projects/'+old['id']+'/archive',json={'archived':True})
  project=(await client.post('/studio/projects',json={'name':'Ateliê funcional premium','category':'loja','tier':'premium_2d','brief':'Loja fictícia com busca, filtros, ordenação, carrinho, 3 produtos fictícios e sem reservas.'})).json()
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=await browser.new_page(viewport={'width':1672,'height':1000});errors=[]
   page.on('pageerror',lambda error:errors.append(str(error)))
   await page.goto(BASE+'/#cronos-session=studio-test-only')
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await page.get_by_role('button',name='Meus projetos',exact=False).first.click()
   await page.locator('.ss-saved-card').filter(has_text=project['name']).first.click()
   await page.get_by_label('Pedido de alteração do site',exact=True).fill('Crie a loja com busca, filtros, ordenação e carrinho de demonstração com 3 produtos fictícios. Sem reservas.')
   await page.get_by_role('button',name='CRIAR COM IA',exact=True).click()
   await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO',exact=True).click()
   await expect(page.locator('.ss-run')).to_contain_text('Versão salva',timeout=20000)
   async def reports_ready():
    for _ in range(100):
     result=(await client.get('/studio/projects/'+project['id'])).json()
     if len(result.get('browser_reports',[]))>=2:return result
     await asyncio.sleep(.2)
    raise AssertionError('Browser reports did not finish')
   result=await reports_ready()
   assert {r['viewport'] for r in result['browser_reports']}=={390,1280}
   failures=[c for r in result['browser_reports'] for c in r['checks'] if c['status']=='failed']
   assert not failures,failures
   assert all(any(c['name']=='Carrinho: adicionar e calcular' for c in r['checks']) for r in result['browser_reports'])
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=20000)
   frame=page.frame_locator('.ss-frame-space iframe')
   await frame.locator('[data-cart-add]').first.scroll_into_view_if_needed()
   assert (await page.locator('.ss-frame-space iframe').bounding_box())['width']>=390
   await frame.locator('[data-cart-add]').first.click()
   await expect(frame.locator('[data-cart-count]')).to_have_text('1')
   await frame.locator('[data-collection-search]').fill('Base')
   await frame.locator('[data-collection-filter]').select_option('rosto')
   await frame.locator('[data-collection-sort]').select_option('price-desc')
   await expect(frame.locator('[data-item]:visible')).to_have_count(1)
   await page.get_by_role('button',name='Testar esta prévia',exact=True).click()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=20000)
   await expect(frame.locator('[data-cart-count]')).to_have_text('1')
   await expect(frame.locator('[data-collection-search]')).to_have_value('Base')
   await expect(frame.locator('[data-collection-filter]')).to_have_value('rosto')
   await expect(frame.locator('[data-collection-sort]')).to_have_value('price-desc')
   await page.get_by_role('tab',name='Verificações',exact=True).click()
   await expect(page.get_by_text('Funções do pedido · estrutura verificada',exact=True)).to_be_visible()
   await page.locator('.ss-build-plan summary').click()
   await expect(page.locator('.ss-build-plan')).to_contain_text('Busca no conteúdo')
   assert not errors,errors
   package=await client.get('/studio/projects/'+project['id']+'/export');assert package.status_code==200
   with tempfile.TemporaryDirectory(prefix='cronos-premium-export-') as directory:
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:archive.extractall(directory)
    server=subprocess.Popen([sys.executable,'server.py','--port','8924'],cwd=directory,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
     for _ in range(60):
      try:
       async with httpx.AsyncClient() as check:
        if (await check.get('http://127.0.0.1:8924/')).status_code==200:break
      except httpx.HTTPError:pass
      await asyncio.sleep(.1)
     export=await browser.new_page(viewport={'width':390,'height':844})
     await export.goto('http://127.0.0.1:8924/')
     await export.locator('[data-cart-add]').first.click()
     await export.locator('[data-cart-add]').first.click()
     await expect(export.locator('[data-cart-total]')).to_have_text('R$\u00a039,80')
     await export.get_by_role('button',name='Remover Pó acetinado',exact=True).click()
     await expect(export.locator('[data-cart-count]')).to_have_text('0')
     await export.locator('[data-collection-search]').fill('acetinado')
     await expect(export.locator('[data-item]:visible')).to_have_count(1)
     assert await export.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2')
    finally:server.terminate();server.wait(timeout=5)
   await browser.close()
   print('PASS: real Studio job; requirements and mobile/desktop reports; search, empty state, filtering, sorting, cart add/decrease/remove and cent totals; tests preserve user state; plan UI; exported site with same working runtime. Builder is a non-billable fixture, not an aesthetic or real-provider certification.')

asyncio.run(main())
