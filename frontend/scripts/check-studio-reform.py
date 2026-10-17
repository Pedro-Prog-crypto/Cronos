"""Built UI acceptance: real study previews, responsive forms, filters and 30 MiB upload.
Uses the isolated fixture vault. No paid IA calls are made.
"""
import asyncio,io,os
from pathlib import Path
import httpx
from PIL import Image
from playwright.async_api import async_playwright,expect
BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8901');AUTH={'Authorization':'Bearer studio-test-only'}

async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH,timeout=40) as c:
  await c.patch('/panels/preferences',json={'device_auto_connect':False,'proactive_suggestions':False})
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
   page=await browser.new_page(viewport={'width':1672,'height':1000});errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   await page.goto(BASE+'/#cronos-session=studio-test-only')
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await page.locator('.ss-sidebar').get_by_role('button',name='Modelos prontos',exact=True).click()
   await expect(page.locator('.ss-direction')).to_have_count(13)
   await page.locator('.ss-direction').last.scroll_into_view_if_needed()
   await expect(page.locator('.ss-direction .ss-real-study img')).to_have_count(13)
   for picture in await page.locator('.ss-direction .ss-real-study img').all():
    await picture.scroll_into_view_if_needed()
    await picture.evaluate('img=>img.decode()')
    assert await picture.evaluate('img=>img.naturalWidth>0')
   await page.locator('.ss-direction').filter(has_text='Restaurantes').click()
   await expect(page.get_by_label('Origem do exemplo')).to_have_value('curated')
   await page.get_by_label('Nome do negócio',exact=True).fill('Mesa de teste editorial')
   before=(await c.get('/fixture/calls')).json()
   await page.get_by_role('button',name='GERAR SITE AUTOMATICAMENTE',exact=True).click()
   frame=page.frame_locator('.ss-frame-container iframe')
   await expect(frame.locator('h1')).to_contain_text('Fogo baixo')
   await expect(frame.locator('.visual img')).to_be_visible()
   await expect(frame.locator('.selection-row:visible')).to_have_count(6)
   await frame.get_by_role('button',name='Da horta',exact=True).click()
   await expect(frame.locator('.selection-row:visible')).to_have_count(2)
   await frame.get_by_role('button',name='Ver tudo',exact=True).click()
   await expect(frame.locator('.selection-row:visible')).to_have_count(6)
   contact=frame.locator('form[data-studio-form="contact"]')
   await contact.locator('[name="name"]').fill('Teste de formulário')
   await contact.locator('[name="email"]').fill('teste@example.com')
   await contact.locator('[name="message"]').fill('Mensagem de teste do estudo.')
   await contact.locator('[name="consent"]').check()
   await contact.get_by_role('button',name='Enviar mensagem',exact=False).click()
   await expect(contact.locator('[data-form-status]')).to_contain_text('TESTE LOCAL')
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   await page.set_viewport_size({'width':390,'height':844})
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   assert await page.locator('.site-studio').evaluate('n=>n.scrollWidth<=innerWidth+2')
   assert await frame.locator('html').evaluate('n=>n.scrollWidth<=innerWidth+2')
   await page.screenshot(path='/tmp/cronos-new-studio-mobile.png')
   await page.set_viewport_size({'width':1672,'height':1000})
   await page.get_by_role('tab',name='Imagens e 3D',exact=True).click()
   photo=io.BytesIO();Image.new('RGB',(64,48),'green').save(photo,'JPEG')
   raw=photo.getvalue()+b'\0'*(30*1024*1024-len(photo.getvalue()))
   async with page.expect_file_chooser() as chooser:
    await page.get_by_role('button',name='Imagem própria',exact=True).click()
   await (await chooser.value).set_files({'name':'foto-30mb.jpg','mimeType':'image/jpeg','buffer':raw})
   await expect(page.locator('.ss-assets')).to_contain_text('foto-30mb.jpg',timeout=20000)
   assert (await c.get('/fixture/calls')).json()==before
   # Request failures have a real retry and preserve the typed city.
   await page.locator('.ss-sidebar').get_by_role('button',name='Oportunidades no Brasil',exact=True).click()
   await page.route('**/prospects/search',lambda route:route.fulfill(status=502,content_type='application/json',body='{"detail":"Falha simulada da fonte pública."}'))
   await page.get_by_label('Cidade do estúdio',exact=True).fill('Manaus, AM')
   await page.get_by_role('button',name='PESQUISAR',exact=True).click()
   await expect(page.get_by_role('button',name='Tentar pesquisa novamente',exact=True)).to_be_visible()
   await expect(page.get_by_label('Cidade do estúdio',exact=True)).to_have_value('Manaus, AM')
   assert await page.get_by_label('Fonte de negócios').input_value()=='osm'
   await page.get_by_role('button',name='Tentar pesquisa novamente',exact=True).click()
   await expect(page.get_by_role('alert')).to_contain_text('Falha simulada')
   assert not errors,errors
   await browser.close()
 print('PASS: 13 actual local preview images; curated default; real menu filters; persisted contact; mobile page and Studio; 30 MiB UI upload normalized; search retry retains city. No real AI calls; search failure is simulated.')

asyncio.run(main())
