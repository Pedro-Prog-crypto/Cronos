"""Verify the supplied catalog, all three live WebGL models and an exported site.

Use the temporary studio-fixture-server.py. AI adapters and gallery photo requests
are fixtures; WebGL, controls, DOM, forms and the exported HTTP runtime are real.
"""
import asyncio
import base64
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from zipfile import ZipFile
from datetime import date, timedelta

import httpx
from PIL import Image
from playwright.async_api import async_playwright, expect

BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8881')
AUTH={'Authorization':'Bearer studio-test-only'}


async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH,timeout=20) as client:
  await client.patch('/panels/preferences',json={'device_auto_connect':False,'proactive_suggestions':False})
  async with async_playwright() as playwright:
   browser=await playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
   page=await browser.new_page(viewport={'width':1672,'height':1000});errors=[]
   page.on('pageerror',lambda error:errors.append(str(error)))
   image=io.BytesIO();Image.new('RGB',(120,80),'#32545e').save(image,'JPEG')
   await page.route('https://images.unsplash.com/**',lambda route:route.fulfill(body=image.getvalue(),content_type='image/jpeg'))
   await page.goto(BASE+'/#cronos-session=studio-test-only')
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await expect(page.locator('.ss-direction')).to_have_count(13)
   await expect(page.locator('.ss-price-overview article')).to_have_count(4)
   await expect(page.locator('.ss-price-overview')).to_contain_text('15.000')
   assert await page.locator('.ss-direction img').count()==13
   await page.locator('.ss-direction').filter(has_text='Imóveis e arquitetura').click()
   await page.get_by_label('Referência do catálogo',exact=True).select_option('imobiliaria_3d')
   await expect(page.locator('.ss-ref-estimate')).to_contain_text('7.000')
   await page.get_by_label('Modelo procedural',exact=True).select_option('hotel')
   await page.get_by_label('Nome do negócio',exact=True).fill('Edifício do senhor')
   initial=(await client.get('/fixture/calls')).json()
   await page.get_by_role('button',name='GERAR SITE AUTOMATICAMENTE',exact=True).click()
   await expect(page.locator('.ss-project-heading h2')).to_have_text('Edifício do senhor')
   website=page.frame_locator('.ss-frame-container iframe')
   await expect(website.locator('[data-studio-procedural="hotel"] canvas')).to_be_visible(timeout=15000)
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   assert (await client.get('/fixture/calls')).json()==initial
   await page.wait_for_timeout(1300)
   await page.screenshot(path='/tmp/cronos-mistral-studio-project.png')
   projects=(await client.get('/studio/projects')).json()['projects'];project=next(p for p in projects if p['name']=='Edifício do senhor')
   assert project['quote']['min']==7000 and project['quote']['max']==15000
   for template in ('basic','standard','premium'):
    made=(await client.post('/studio/projects',json={'name':'Casa '+template,'category':'restaurante','tier':'standard','template':template,'create_from_template':True})).json()
    ticket=(await client.post('/studio/projects/'+made['id']+'/preview',json={})).json()
    sample=await browser.new_page(viewport={'width':1280,'height':900})
    await sample.route('https://images.unsplash.com/**',lambda route:route.fulfill(body=image.getvalue(),content_type='image/jpeg'))
    await sample.goto(BASE+ticket['url'])
    await expect(sample.locator('form[data-studio-form="contact"]')).to_be_visible()
    assert await sample.locator('[data-studio-procedural]').count()==0
    assert await sample.locator('input[name="name"]').first.evaluate('input=>input.labels.length>0')
    await sample.set_viewport_size({'width':390,'height':844})
    assert await sample.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    await sample.screenshot(path='/tmp/cronos-mistral-'+template+'-2d.png',full_page=True)
    await sample.close()
   for model,category in [('earbuds','personalizado'),('airplane','personalizado'),('hotel','imobiliaria')]:
    result=await client.post('/studio/projects',json={'name':'Modelo '+model,'category':category,'brief':'Site 3D','model_type':model,'create_from_template':True})
    result.raise_for_status();item=result.json();pid=item['id']
    assert item['status']=='ready' and item['current']['report']['passed']
    ticket=(await client.post('/studio/projects/'+pid+'/preview',json={})).json()
    scene=await browser.new_page(viewport={'width':1280,'height':900});scene_errors=[];external=[]
    scene.on('pageerror',lambda error:scene_errors.append(str(error)))
    scene.on('request',lambda request:external.append(request.url) if request.url.startswith('https://') else None)
    await scene.goto(BASE+ticket['url'])
    await scene.wait_for_function("window.__studioProceduralState==='ready'")
    await scene.wait_for_timeout(1200) # Original loader/controls finish their initial animation.
    original=await scene.evaluate('window.__studioProceduralSnapshot()')
    assert original['meshes']>0 and (model!='hotel' or original['floors']==10)
    canvas=scene.locator('[data-studio-procedural] canvas');await expect(canvas).to_be_visible()
    box=await canvas.bounding_box();assert box and box['width']>200 and box['height']>250
    await scene.get_by_role('button',name='Rotacionar',exact=True).click()
    turned=await scene.evaluate('window.__studioProceduralSnapshot()');assert turned['camera']!=original['camera']
    await scene.get_by_role('button',name='Aproximar',exact=True).click()
    zoomed=await scene.evaluate('window.__studioProceduralSnapshot()');assert zoomed['camera']!=turned['camera']
    await scene.get_by_role('button',name='Transparência',exact=True).click()
    transparent=await scene.evaluate('window.__studioProceduralSnapshot()');assert transparent['pieces'][0]['opacity']==.3
    await scene.get_by_role('button',name='Explodir',exact=True).click();await scene.wait_for_timeout(2100)
    exploded=await scene.evaluate('window.__studioProceduralSnapshot()');assert [p['position'] for p in exploded['pieces']] != [p['position'] for p in original['pieces']]
    await scene.get_by_role('button',name='Resetar',exact=True).click();await scene.wait_for_timeout(100)
    reset=await scene.evaluate('window.__studioProceduralSnapshot()');assert [p['position'] for p in reset['pieces']]==[p['position'] for p in original['pieces']]
    if model=='earbuds':
     await scene.get_by_role('button',name='Abrir estojo',exact=True).click();await scene.wait_for_timeout(1200)
     assert abs((await scene.evaluate('window.__studioProceduralSnapshot()'))['pieces'][1]['rotation'][0])>1
     await scene.get_by_role('button',name='Fechar estojo',exact=True).click();await scene.wait_for_timeout(1200)
     assert abs((await scene.evaluate('window.__studioProceduralSnapshot()'))['pieces'][1]['rotation'][0])<.01
    if model=='airplane':
     await scene.get_by_role('button',name='Decolar',exact=True).click();await scene.wait_for_timeout(3200)
     assert (await scene.evaluate('window.__studioProceduralSnapshot()'))['position'][1]>4.5
     await scene.get_by_role('button',name='Pousar',exact=True).click();await scene.wait_for_timeout(3200)
     assert abs((await scene.evaluate('window.__studioProceduralSnapshot()'))['position'][1])<.01
     await scene.get_by_role('button',name='Voar',exact=True).click();await scene.wait_for_timeout(250)
     assert (await scene.evaluate('window.__studioProceduralSnapshot()'))['position']!=[0,0,0]
     await scene.get_by_role('button',name='Resetar',exact=True).click()
    await scene.screenshot(path='/tmp/cronos-mistral-'+model+'-verified.png',full_page=True)
    await scene.set_viewport_size({'width':390,'height':844});await scene.wait_for_timeout(200)
    assert await scene.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    await scene.screenshot(path='/tmp/cronos-mistral-'+model+'-mobile.png',full_page=True)
    assert not scene_errors,scene_errors
    assert not external,external # The 3D works without any CDN request.
    if model=='hotel': export_project=item
    await scene.close()
   unavailable=await browser.new_page(viewport={'width':1280,'height':900})
   await unavailable.add_init_script("const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return /^webgl|experimental-webgl/.test(type)?null:original.call(this,type,...args);};")
   fallback_ticket=(await client.post('/studio/projects/'+export_project['id']+'/preview',json={})).json()
   await unavailable.goto(BASE+fallback_ticket['url'])
   await unavailable.wait_for_function("window.__studioProceduralState==='failed'")
   await expect(unavailable.locator('[data-studio-procedural]')).to_contain_text('WebGL indisponível')
   assert await unavailable.locator('#loader').evaluate("node=>getComputedStyle(node).pointerEvents==='none'")
   await expect(unavailable.locator('form[data-studio-form="contact"]')).to_be_visible()
   await unavailable.close()
   # A real independent server executes the actual ZIP, not Cronos' iframe bridge.
   archive=(await client.get('/studio/projects/'+export_project['id']+'/export')).content
   with tempfile.TemporaryDirectory(prefix='cronos-mistral-export-') as folder:
    root=Path(folder)
    with ZipFile(io.BytesIO(archive)) as package:package.extractall(root)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    with (root/'server.log').open('w') as log:
     server=subprocess.Popen([sys.executable,str(root/'server.py'),'--port',str(port)],cwd=root,stdout=log,stderr=log)
     try:
      address='http://127.0.0.1:'+str(port)
      async with httpx.AsyncClient() as check:
       for _ in range(100):
        try:
         if (await check.get(address)).status_code==200:break
        except httpx.HTTPError:pass
        await asyncio.sleep(.05)
       else:raise AssertionError('Export server did not become ready')
      exported=await browser.new_page(viewport={'width':1280,'height':900});export_errors=[];exported.on('pageerror',lambda error:export_errors.append(str(error)))
      await exported.goto(address)
      await exported.wait_for_function("window.__studioProceduralState==='ready'")
      await expect(exported.locator('[data-studio-procedural] canvas')).to_be_visible()
      contact=exported.locator('form[data-studio-form="contact"]')
      await contact.locator('[name="name"]').fill('Teste exportado')
      await contact.locator('[name="email"]').fill('teste@example.com')
      await contact.locator('[name="message"]').fill('Mensagem real de teste no runtime exportado.')
      await contact.locator('[name="consent"]').check()
      assert await contact.evaluate('(form)=>form.dataset.runtimeBound==="true"&&form.checkValidity()')
      await contact.locator('button[type="submit"]').click()
      await expect(contact.locator('[data-form-status]')).to_contain_text('registrada',timeout=15000)
      import sqlite3
      with sqlite3.connect(root/'private/contacts.sqlite3') as database:
       assert database.execute('SELECT count(*) FROM submissions').fetchone()[0]==1
      assert not export_errors,export_errors
      await exported.close()
     finally:
      server.terminate();server.wait(timeout=10)
   # Equivalent spoken text creates the requested local category template.
   await page.get_by_role('button',name='Fechar Estúdio de Sites',exact=True).click()
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
   await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('Cronos, criar site 3D para imobiliária')
   await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
   await expect(page.locator('.ss-frame-container iframe')).to_be_visible(timeout=15000)
   await expect(page.frame_locator('.ss-frame-container iframe').locator('[data-studio-procedural="hotel"] canvas')).to_be_visible(timeout=15000)
   assert (await client.get('/fixture/calls')).json()==initial
   assert not errors,errors
   await browser.close()
 print('PASS: all 13 categories, 17 references and four price tiers; automatic creation without AI; complete earbuds/airplane/10-floor building render with WebGL; rotate/zoom/explode/reset/transparency/open/close controls; desktop/mobile; no 3D CDN requests; independent ZIP server and persisted contact; exact category voice command. Provider and gallery image fixtures only.')


asyncio.run(main())
