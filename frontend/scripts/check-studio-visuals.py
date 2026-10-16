"""Exercise visual planning and explicit API confirmation against the local fixture."""
import asyncio
import json
import os
from pathlib import Path

import httpx
from playwright.async_api import async_playwright, expect

BASE = os.getenv('STUDIO_TEST_URL', 'http://127.0.0.1:8876')
AUTH = {'Authorization':'Bearer studio-test-only'}


async def main():
    async with httpx.AsyncClient(base_url=BASE,headers=AUTH) as client:
        await client.patch('/panels/preferences',json={'device_auto_connect':False,'proactive_suggestions':False})
        async with async_playwright() as p:
            browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=await browser.new_page(viewport={'width':1672,'height':1000})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('dialog',lambda dialog:dialog.dismiss()) # No native browser dialog is needed for generation.
            await page.goto(BASE+'/#cronos-session=studio-test-only')
            await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
            await expect(page.locator('.ss-restaurant-direction')).not_to_have_count(0)
            await page.get_by_role('button',name='Explorar demonstração funcional',exact=True).click()
            await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled()
            website=page.frame_locator('.ss-frame-container iframe')
            await expect(website.locator('h1')).to_contain_text('O mar decide.')
            await expect(website.locator('.opening-photo img')).to_be_visible()
            await website.get_by_role('button',name='Para terminar',exact=True).click()
            assert await website.locator('.menu-items article:visible').count()==1
            await website.get_by_role('button',name='Detalhes').click()
            await expect(website.get_by_role('dialog')).to_be_visible()
            await expect(website.get_by_role('dialog').get_by_role('heading',name='Cocada de forno',exact=True)).to_be_visible()
            await website.get_by_role('button',name='Fechar detalhes do prato').click()
            await page.screenshot(path='/tmp/cronos-studio-restaurant-editor.png')
            projects=(await client.get('/studio/projects')).json()['projects'];project=projects[0];pid=project['id']
            ticket=(await client.post('/studio/projects/'+pid+'/preview',json={})).json()
            visual=await browser.new_page(viewport={'width':1440,'height':1050})
            await visual.goto(BASE+ticket['url'])
            await visual.screenshot(path='/tmp/cronos-restaurant-redesigned-desktop.png',full_page=True)
            await visual.set_viewport_size({'width':390,'height':844})
            await visual.screenshot(path='/tmp/cronos-restaurant-redesigned-mobile.png',full_page=True)
            assert await visual.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
            await visual.close()
            initial_calls=(await client.get('/fixture/calls')).json()
            await page.get_by_role('button',name='Exportar',exact=True).click()
            await expect(page.get_by_role('alertdialog')).to_contain_text('apenas o rascunho')
            await page.get_by_role('button',name='Voltar sem enviar').click()
            assert (await client.get('/fixture/calls')).json()==initial_calls
            await page.get_by_role('tab',name='Ideias e direção',exact=True).click()
            await page.get_by_role('button',name='CRIAR 3 PROPOSTAS COM IA',exact=True).click()
            await page.keyboard.press('Escape')
            await expect(page.get_by_role('dialog',name='Estúdio de Sites',exact=True)).to_be_visible()
            assert (await client.get('/fixture/calls')).json()==initial_calls
            await page.get_by_role('button',name='CRIAR 3 PROPOSTAS COM IA',exact=True).click()
            await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO').click()
            await expect(page.locator('.ss-idea')).to_have_count(3,timeout=15000)
            await expect(page.locator('.ss-badge')).to_contain_text('v0')
            assert (await client.get('/fixture/calls')).json()['plans']==initial_calls['plans']+1
            await page.locator('.ss-idea').nth(1).get_by_role('button',name='ESCOLHER ESTA DIREÇÃO').click()
            await expect(page.locator('.ss-idea.chosen')).to_have_count(1)
            await page.screenshot(path='/tmp/cronos-studio-ideas-approved.png')
            await page.get_by_role('button',name='CRIAR IMAGEM DA PROPOSTA').click()
            await page.get_by_label('Formato da imagem',exact=True).select_option('vertical')
            await page.get_by_label('Descrição da imagem a gerar',exact=True).fill('Crie uma composição vertical com a direção aprovada para demonstrar o site.')
            await page.get_by_role('button',name='REVISAR E GERAR IMAGEM').click()
            await expect(page.get_by_role('alertdialog')).to_contain_text('créditos da API')
            await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO').click()
            await expect(page.locator('.ss-assets')).to_contain_text('Proposta visual vertical.jpg',timeout=15000)
            await expect(page.locator('.ss-assets')).to_contain_text('1024 × 1536 · VERTICAL')
            await expect(page.locator('.ss-assets img')).to_have_count(2) # Example photo + image API fixture.
            assert (await client.get('/fixture/calls')).json()['image']==initial_calls['image']+1
            search=[]
            async def image_search(route):
                search.append(json.loads(route.request.post_data))
                await route.fulfill(json={'images':[{'title':'File:Portrait fixture.jpg','width':900,'height':1400,'orientation':'vertical','author':'Fixture author','license':'CC0','source':'https://commons.wikimedia.org/wiki/File:Fixture.jpg','thumbnail':''}]})
            await page.route('**/studio/images/search',image_search)
            await page.get_by_label('Pesquisar imagens públicas',exact=True).fill('restaurant kitchen')
            await page.get_by_label('Formato da busca de imagens').select_option('vertical')
            await page.get_by_role('button',name='Pesquisar',exact=True).click()
            await expect(page.locator('.ss-image-results')).to_contain_text('900 × 1400 · vertical')
            assert search[-1]['orientation']=='vertical'
            await page.get_by_role('tab',name='Ideias e direção',exact=True).click()
            await page.get_by_role('button',name='CONSTRUIR DIREÇÃO APROVADA',exact=True).click()
            await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO').click()
            await expect(page.locator('.ss-badge')).to_contain_text('Versão disponível',timeout=15000)
            await expect(page.locator('.ss-badge')).to_contain_text('v1')
            await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
            # The failed request remains visible, even after reopening the saved project.
            request='Simular falha 429 e preservar o meu pedido completo de alteração.'
            await page.get_by_label('Pedido de alteração do site',exact=True).fill(request)
            await page.get_by_role('button',name='GERAR NOVA VERSÃO',exact=True).click()
            await page.get_by_role('button',name='Voltar sem enviar').click()
            assert await page.get_by_label('Pedido de alteração do site',exact=True).input_value()==request
            await page.get_by_role('button',name='GERAR NOVA VERSÃO',exact=True).click()
            await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO').click()
            await expect(page.locator('.ss-job-error')).to_contain_text('429',timeout=15000)
            assert await page.get_by_label('Pedido de alteração do site',exact=True).input_value()==request
            assert (await client.get('/studio/projects/'+pid)).json()['revision']==1
            await page.get_by_role('button',name='Voltar aos projetos',exact=True).click()
            await page.locator('.ss-saved-card').filter(has_text=project['name']).first.click()
            await expect(page.get_by_label('Pedido de alteração do site',exact=True)).to_have_value(request)
            await page.set_viewport_size({'width':390,'height':844})
            await page.get_by_role('tab',name='Ideias e direção',exact=True).click()
            await page.screenshot(path='/tmp/cronos-studio-ideas-mobile.png')
            assert await page.locator('.site-studio').evaluate('n=>n.scrollWidth<=innerWidth+2')
            await page.set_viewport_size({'width':1672,'height':1000})
            await page.get_by_role('button',name='Voltar aos projetos',exact=True).click()
            await page.get_by_role('button',name='Novo projeto',exact=True).click()
            await page.get_by_label('Nome do projeto',exact=True).fill('Ateliê do bairro')
            await page.get_by_label('Briefing do site',exact=True).fill('Quero três direções diferentes de um site editorial de restaurante, com fotografia e cardápio.')
            await page.locator('.ss-mode-options button').first.click()
            await page.get_by_role('button',name='PREPARAR PROPOSTAS VISUAIS',exact=True).click()
            await expect(page.get_by_role('alertdialog')).to_contain_text('três propostas')
            await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO').click()
            await expect(page.locator('.ss-project-heading h2')).to_have_text('Ateliê do bairro',timeout=15000)
            await expect(page.locator('.ss-idea')).to_have_count(3,timeout=15000)
            assert not errors,errors
            await browser.close()
            print('PASS: restaurant imagery, filters and details; draft export warning; in-app authorization and ESC preserve requests; three proposals, explicit choice, vertical image, source orientation search, approved-direction build, failed-generation request persistence, responsive layout. Provider calls are fixtures, not live APIs.')


asyncio.run(main())
