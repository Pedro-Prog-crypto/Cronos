"""Home -> public-business fixture -> one autonomous job -> saved preview, with failover."""
import asyncio
import os
from pathlib import Path
import httpx
from playwright.async_api import async_playwright,expect

BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8891')
AUTH={'Authorization':'Bearer studio-test-only'}

async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH,timeout=20) as client:
  await client.patch('/panels/preferences',json={'device_auto_connect':False,'proactive_suggestions':False})
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=await browser.new_page(viewport={'width':1672,'height':1000})
   errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   await page.route('https://images.unsplash.com/**',lambda route:route.fulfill(body=(Path(__file__).resolve().parents[2]/'cronos/studio/media/restaurant-fire.jpg').read_bytes(),content_type='image/jpeg'))
   await page.goto(BASE+'/#cronos-session=studio-test-only')
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await expect(page.locator('.ss-home h2')).to_contain_text('Da primeira ideia')
   await expect(page.locator('.ss-home-status')).to_contain_text('configurada')
   await page.screenshot(path='/tmp/cronos-workspace-home-desktop.png')
   await page.set_viewport_size({'width':390,'height':844})
   assert await page.locator('.site-studio').evaluate('n=>n.scrollWidth<=innerWidth+2')
   await page.screenshot(path='/tmp/cronos-workspace-home-mobile.png')
   await page.set_viewport_size({'width':1672,'height':1000})
   await page.get_by_role('button',name='Explorar negócios',exact=False).click()
   await page.get_by_label('Cidade do estúdio',exact=True).fill('Brasília, DF')
   await page.get_by_role('button',name='PESQUISAR',exact=True).click()
   await expect(page.locator('.ss-lead-card')).to_have_count(2)
   initial=(await client.get('/fixture/calls')).json()
   assert not initial['site'] and not initial['plans']
   assert not (await client.get('/studio/projects')).json()['projects']
   await page.screenshot(path='/tmp/cronos-workspace-opportunities.png')
   await page.locator('.ss-lead-card').filter(has_text='Mesa da Praça').get_by_role('button',name='Criar proposta com IA').click()
   await expect(page.locator('.ss-job-view')).to_be_visible()
   assert await page.locator('.ss-frame-container iframe').count()==0
   await page.screenshot(path='/tmp/cronos-workspace-progress.png')
   await expect(page.locator('.ss-run')).to_contain_text('IA ativa: mistral',timeout=15000)
   await expect(page.locator('.ss-frame-container iframe')).to_be_visible(timeout=25000)
   await expect(page.locator('.ss-badge')).to_contain_text('Versão disponível')
   projects=(await client.get('/studio/projects')).json()['projects']
   assert len(projects)==1
   saved=(await client.get('/studio/projects/'+projects[0]['id'])).json()
   assert saved['code_origin']=='generated' and saved['status']=='ready'
   assert saved['quote']['min']==200 and not saved['quote']['has_3d']
   assert len(saved['directions'])==3 and saved['direction_id']
   assert saved['current']['report']['composition'][0]['status']=='passed'
   assert any(e['phase']=='fallback' for e in saved['events']) and not saved.get('error')
   frame=page.frame_locator('.ss-frame-container iframe')
   await expect(frame.locator('h1')).to_be_visible()
   await page.screenshot(path='/tmp/cronos-workspace-created.png')
   await page.get_by_role('button',name='Voltar aos resultados',exact=True).click()
   await expect(page.locator('.ss-lead-card')).to_have_count(2)
   assert await page.get_by_label('Cidade do estúdio',exact=True).input_value()=='Brasília, DF'
   calls=(await client.get('/fixture/calls')).json()
   await page.locator('.ss-lead-card').filter(has_text='Mesa da Praça').get_by_role('button',name='Abrir proposta salva').click()
   await expect(page.locator('.ss-project-heading h2')).to_contain_text('Mesa da Praça')
   assert (await client.get('/fixture/calls')).json()==calls
   await page.get_by_role('tab',name='Verificações',exact=True).click()
   await expect(page.locator('.ss-content-pane:visible')).to_contain_text('Composição diferente dos projetos recentes')
   await page.locator('.ss-sidebar').get_by_role('button',name='Início',exact=True).click()
   await expect(page.locator('.ss-recent-projects')).to_contain_text('Mesa da Praça')
   await page.get_by_role('button',name='Criar um site com IA',exact=False).click()
   await expect(page.get_by_role('button',name='CRIAR SITE COM IA',exact=True)).to_be_visible()
   await page.get_by_label('Nome do projeto',exact=True).fill('Novo trabalho do senhor')
   await page.get_by_label('Briefing do site',exact=True).fill('Uma página em duas dimensões, com fotografias e movimentos leves, para uma cozinha autoral.')
   assert await page.get_by_label('Faixa do novo site',exact=True).input_value()=='economy'
   await page.get_by_role('button',name='CRIAR SITE COM IA',exact=True).click()
   await expect(page.get_by_role('alertdialog')).to_be_visible()
   before=(await client.get('/fixture/calls')).json()
   await page.keyboard.press('Escape')
   assert (await client.get('/fixture/calls')).json()==before
   await expect(page.get_by_label('Nome do projeto',exact=True)).to_have_value('Novo trabalho do senhor')
   await page.set_viewport_size({'width':390,'height':844})
   assert await page.locator('.ss-wizard').evaluate('n=>n.scrollWidth<=n.clientWidth+2')
   await page.screenshot(path='/tmp/cronos-workspace-new-mobile.png')
   await page.get_by_role('button',name='CRIAR SITE COM IA',exact=True).click()
   await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO',exact=True).click()
   await expect(page.locator('.ss-job-view')).to_be_visible()
   await expect(page.locator('.ss-frame-container iframe')).to_be_visible(timeout=25000)
   all_projects=(await client.get('/studio/projects')).json()['projects']
   assert len(all_projects)==2
   second=(await client.get('/studio/projects/'+all_projects[0]['id'])).json()
   assert second['name']=='Novo trabalho do senhor' and second['code_origin']=='generated'
   assert second['design_comparison']['compared_projects']==1
   assert second['current']['report']['composition'][0]['status']=='passed'
   assert second['current']['files']['styles.css']!=saved['current']['files']['styles.css']
   await page.locator('.ss-mobile-nav').get_by_role('button',name='Oportunidades',exact=True).click()
   await expect(page.locator('.ss-lead-card')).to_have_count(2)
   assert await page.locator('.site-studio').evaluate('n=>n.scrollWidth<=innerWidth+2')
   await page.screenshot(path='/tmp/cronos-workspace-opportunities-mobile.png')
   assert not errors,errors
   await browser.close()
 print('PASS: organized home desktop/mobile; no generation during search; click creates one real project with plans, saved assets, failover and functional preview; repeated click reopens without calls; search retained; composition report; direct-create form and ESC preserve inputs. Business and AI sources are explicit fixtures.')

asyncio.run(main())
