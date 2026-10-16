"""Integration check against a local Cronos with a fixture builder, never live API keys.
Start the fixture server documented in docs/STUDIO_DE_SITES.md; BASE_URL defaults to 8871.
"""
import asyncio,json,os,struct,io,zipfile
from datetime import date,timedelta
from pathlib import Path
import httpx
from playwright.async_api import async_playwright,expect
BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8871')
TOKEN='studio-test-only'
AUTH={'Authorization':'Bearer '+TOKEN}


def model_glb():
 positions=struct.pack('<9f',-1,0,0,1,0,0,0,1.5,0)
 doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0,1]}], 'nodes':[{'mesh':0,'translation':[-.8,0,0]},{'mesh':0,'translation':[.8,0,0]}],
      'meshes':[{'primitives':[{'attributes':{'POSITION':0},'material':0}]}],'materials':[{'pbrMetallicRoughness':{'baseColorFactor':[.1,.7,.9,1],'metallicFactor':.2,'roughnessFactor':.4},'doubleSided':True}],
      'buffers':[{'byteLength':len(positions)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(positions)}],
      'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[-1,0,0],'max':[1,1.5,0]}]}
 data=json.dumps(doc,separators=(',',':')).encode();data+=b' ' * (-len(data)%4)
 return b'glTF'+struct.pack('<II',2,12+8+len(data)+8+len(positions))+struct.pack('<II',len(data),0x4e4f534a)+data+struct.pack('<II',len(positions),0x004e4942)+positions


async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH) as client:
  await client.patch('/panels/preferences',json={'device_auto_connect':False,'proactive_suggestions':False})
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-angle=swiftshader-webgl','--enable-unsafe-swiftshader'],headless=True)
   page=await browser.new_page(viewport={'width':1672,'height':941},device_scale_factor=1)
   errors=[];violations=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('console',lambda m:violations.append(m.text) if 'Refused to' in m.text or 'violates the following Content Security' in m.text else None)
   await page.route('https://images.unsplash.com/**',lambda route:route.fulfill(body=(Path(__file__).resolve().parents[2]/'cronos/studio/media/restaurant-fire.jpg').read_bytes(),content_type='image/jpeg'))
   await page.goto(BASE+'/#cronos-session='+TOKEN)
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await page.locator('.ss-sidebar').get_by_role('button',name='Modelos prontos',exact=True).click()
   await expect(page.get_by_role('dialog',name='Estúdio de Sites',exact=True)).to_be_visible()
   await expect(page.locator('.ss-direction')).to_have_count(13)
   await page.screenshot(path='/tmp/cronos-studio-gallery.png')
   await page.locator('.ss-direction.hotel').count() # Direction category belongs to nested art.
   await page.locator('.ss-direction').filter(has_text='Hotéis e pousadas').click()
   await page.get_by_role('button',name='GERAR SITE AUTOMATICAMENTE',exact=True).click()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=10000)
   website=page.frame_locator('.ss-frame-container iframe')
   await expect(website.locator('h1')).to_contain_text('Seu Refúgio')
   await page.screenshot(path='/tmp/cronos-studio-preview.png')
   contact=website.locator('form[data-studio-form="contact"]')
   await contact.locator('[name="name"]').fill('Senhor Teste')
   await contact.locator('[name="email"]').fill('teste@example.com')
   await contact.locator('[name="message"]').fill("Texto <script>não executa</script> '); DROP TABLE submissions;--")
   await contact.locator('[name="consent"]').check()
   await contact.get_by_role('button',name='Enviar mensagem').click()
   await expect(contact.locator('[data-form-status]')).to_contain_text('TESTE LOCAL:')
   booking=website.locator('form[data-studio-form="booking"]')
   for attempt in range(2):
    await booking.locator('[name="name"]').fill('Reserva Teste')
    await booking.locator('[name="email"]').fill('reserva@example.com')
    await booking.locator('[name="date"]').fill(str(date.today()+timedelta(days=17)))
    await booking.locator('[name="time"]').fill('12:00')
    await booking.locator('[name="consent"]').check()
    await booking.get_by_role('button',name='Solicitar horário').click()
    await expect(booking.locator('[data-form-status]')).to_contain_text('TESTE LOCAL:' if attempt==0 else 'já foi solicitado')
   await page.get_by_role('button',name='Testar esta prévia',exact=True).click()
   await expect(page.locator('.ss-notification')).to_contain_text('celular e desktop concluídas',timeout=15000)
   await page.get_by_role('tab',name='Verificações',exact=True).click()
   await expect(page.locator('.ss-content-pane')).to_contain_text('390 px')
   await expect(page.locator('.ss-content-pane')).to_contain_text('1280 px')
   assert await page.locator('.ss-checks .failed').count()==0
   await page.get_by_role('tab',name='Testes de envio',exact=True).click()
   await expect(page.locator('.ss-content-pane')).to_contain_text('Senhor Teste')
   await expect(page.locator('.ss-content-pane')).to_contain_text('DROP TABLE')
   await page.get_by_role('tab',name='Imagens e 3D',exact=True).click()
   async with page.expect_file_chooser() as info:
    await page.get_by_role('button',name='Modelo GLB',exact=True).click()
   await (await info.value).set_files({'name':'produto-real-de-teste.glb','mimeType':'model/gltf-binary','buffer':model_glb()})
   await expect(page.locator('.ss-assets')).to_contain_text('produto-real-de-teste.glb')
   await page.get_by_label('Direção do projeto',exact=True).select_option('autonomous')
   await page.get_by_label('Pedido de alteração do site',exact=True).fill('Crie uma direção visual de hotel e mostre o modelo 3D fornecido, sem inventar componentes.')
   await page.get_by_role('button',name='CRIAR COM IA',exact=True).click()
   await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO',exact=True).click()
   await expect(page.locator('.ss-badge')).to_contain_text('Versão disponível',timeout=15000)
   await page.get_by_role('tab',name='Prévia',exact=True).click()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   await expect(website.locator('[data-studio-model] canvas')).to_be_visible(timeout=15000)
   await expect(website.get_by_role('slider',name='Separação dos objetos existentes no GLB')).to_be_enabled()
   await website.get_by_role('slider',name='Separação dos objetos existentes no GLB').fill('60')
   await website.get_by_role('button',name='Restaurar câmera',exact=True).click()
   await page.get_by_role('tab',name='Código',exact=True).click()
   editor=page.get_by_label('Editor de index.html',exact=True)
   content=await editor.input_value()
   await editor.fill(content.replace('Seu Refúgio','Hotel Aurora — edição revisada.'))
   await page.get_by_role('button',name='Salvar versão',exact=True).click()
   await expect(page.locator('.ss-badge')).to_contain_text('v2')
   async with page.expect_download() as download:
    await page.get_by_role('button',name='Exportar',exact=True).click()
   downloaded=await download.value;path=await downloaded.path()
   with zipfile.ZipFile(path) as z:
    assert 'server.py' in z.namelist() and 'site/product-3d.js' in z.namelist()
    assert all('sqlite' not in n and '.env' not in n for n in z.namelist())
   await page.get_by_role('tab',name='Versões',exact=True).click()
   await expect(page.locator('.ss-revision')).to_have_count(3)
   await page.locator('.ss-revision').last.get_by_role('button',name='Restaurar versão').click()
   await expect(page.locator('.ss-badge')).to_contain_text('v3')
   await page.get_by_role('button',name='Fechar Estúdio de Sites',exact=True).click()
   await expect(page.locator('.site-studio')).to_have_count(0)
   # Voice-equivalent text command is routed locally before the chat provider.
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
   await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('Cronos, faça um site para um lava-jato de Manaus')
   await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
   await expect(page.locator('.ss-wizard')).to_be_visible()
   assert 'lava-jato' in await page.get_by_label('Briefing do site',exact=True).input_value()
   await page.get_by_role('button',name='Fechar novo projeto',exact=True).click()
   await page.get_by_role('button',name='Meus projetos',exact=False).click()
   await expect(page.locator('.ss-saved-card')).not_to_have_count(0)
   await page.set_viewport_size({'width':390,'height':844})
   await page.screenshot(path='/tmp/cronos-studio-mobile.png')
   width=await page.locator('.site-studio').evaluate('(e)=>e.scrollWidth')
   assert width<=392,width
   assert not errors,errors
   assert not violations,violations
   await browser.close()
   print('PASS: real local API, gallery, opaque sandbox and CSP, contact persistence, booking conflict, desktop/mobile DOM tests, GLB viewer, AI fixture generation, manual edit, history/restore, clean export and local command. No live-provider calls.')
asyncio.run(main())
