"""Screen snapshot/review/repair and explicit retry in the built application.
A deterministic vision/code fixture and a canvas MediaStream replace paid AI and
an OS chooser. The actual browser video, canvas, HTTP API and UI are exercised.
"""
import asyncio
import os
import httpx
from playwright.async_api import async_playwright,expect

BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8895')
AUTH={'Authorization':'Bearer studio-test-only'}

async def wait_job(client,id):
 for _ in range(200):
  result=(await client.get('/studio/projects/'+id)).json()
  if result['status']!='running':return result
  await asyncio.sleep(.05)
 raise AssertionError('Job did not end')

async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH,timeout=30) as c:
  await c.patch('/panels/preferences',json={'device_auto_connect':False,'proactive_suggestions':False})
  created=(await c.post('/studio/projects',json={'name':'Revisão visual teste','category':'restaurante','brief':'Uma cozinha de bairro com contato e reserva.'})).json()
  id=created['id'];url='/studio/projects/'+id
  await c.post(url+'/generate',json={'mode':'autonomous','prompt':'Crie este site com fotos e formulários claros.'})
  saved=await wait_job(c,id);assert saved['status']=='ready',saved.get('error')
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=await browser.new_page(viewport={'width':1672,'height':1000})
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   await page.add_init_script('''
   window.testShares=[];window.testShareOptions=[];
   navigator.mediaDevices.getDisplayMedia=async options=>{
    window.testShareOptions.push(options);
    const canvas=document.createElement('canvas');canvas.width=900;canvas.height=600;
    const ctx=canvas.getContext('2d');ctx.fillStyle='#f8f0db';ctx.fillRect(0,0,900,600);
    ctx.fillStyle='#112c23';ctx.font='30px sans-serif';ctx.fillText('Site de teste compartilhado',60,100);
    const stream=canvas.captureStream(2);window.testShares.push(stream);
    const timer=setInterval(()=>{ctx.fillRect(60,200,400,44);},300);
    stream.getTracks()[0].addEventListener('ended',()=>clearInterval(timer));
    return stream;
   };''')
   await page.goto(BASE+'/#cronos-session=studio-test-only')
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await page.locator('.ss-recent-projects button').filter(has_text='Revisão visual teste').click()
   await expect(page.locator('.ss-frame-container iframe')).to_be_visible()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   await page.get_by_role('button',name='Ampliar prévia',exact=True).click()
   bounds=await page.locator('.ss-preview-pane').bounding_box()
   assert bounds['width']>=1650 and bounds['height']>=978,bounds
   await expect(page.get_by_role('button',name='Fechar prévia ampliada',exact=True)).to_be_visible()
   await page.keyboard.press('Escape')
   await expect(page.get_by_role('dialog',name='Estúdio de Sites')).to_be_visible()
   assert await page.locator('.site-studio.expanded').count()==0
   await page.get_by_role('tab',name='Ver minha tela',exact=True).click()
   before=(await c.get('/fixture/calls')).json().get('screen',0)
   await page.get_by_role('button',name='Compartilhar tela',exact=True).click()
   await expect(page.get_by_role('button',name='Capturar este site',exact=True)).to_be_visible()
   assert await page.evaluate('window.testShareOptions[0].audio===false')
   assert (await c.get('/fixture/calls')).json().get('screen',0)==before
   await page.get_by_role('button',name='Capturar este site',exact=True).click()
   await expect(page.locator('.ss-screen-frame img')).to_be_visible()
   assert (await c.get('/fixture/calls')).json().get('screen',0)==before
   assert await page.locator('.ss-screen-frame img').evaluate('n=>n.naturalWidth===900')
   await page.get_by_role('button',name='Parar compartilhamento',exact=True).click()
   assert await page.evaluate('window.testShares[0].getTracks().every(t=>t.readyState==="ended")')
   await page.get_by_role('button',name='Analisar captura',exact=True).click()
   await expect(page.locator('.ss-screen-review')).to_contain_text('Campos muito pequenos',timeout=10000)
   reviewed=await wait_job(c,id)
   assert reviewed['revision']==saved['revision'] and reviewed['current']==saved['current']
   assert (await c.get('/fixture/calls')).json()['screen_has_image']
   await page.get_by_role('button',name='Corrigir site com esta captura',exact=True).click()
   await expect(page.locator('.ss-badge')).to_contain_text('v2',timeout=15000)
   repaired=await wait_job(c,id)
   assert repaired['revision']==2 and repaired['current']['files']['styles.css']!=saved['current']['files']['styles.css']
   assert not repaired['assets'] and not await page.locator('.ss-screen-frame').count()
   await page.set_viewport_size({'width':390,'height':844})
   assert await page.locator('.site-studio').evaluate('n=>n.scrollWidth<=innerWidth+2')
   assert await page.locator('.ss-screen-panel').evaluate('n=>n.scrollWidth<=n.clientWidth+2')
   await page.set_viewport_size({'width':1672,'height':1000})
   await page.screenshot(path='/tmp/cronos-screen-review.png')
   # Capture-file flow uses the same explicit analysis request.
   await page.get_by_label('Arquivo de captura de tela',exact=True).set_input_files('/tmp/cronos-screen-review.png')
   await expect(page.locator('.ss-screen-frame img')).to_be_visible()
   await page.get_by_role('button',name='Descartar captura',exact=True).click()
   await expect(page.locator('.ss-screen-frame')).to_have_count(0)
   # Check actual computed geometry, then intentionally break saved CSS.
   await page.get_by_role('tab',name='Prévia',exact=True).click()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   await page.get_by_role('button',name='Testar esta prévia',exact=True).click()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   state=(await c.get(url)).json()
   assert not any(x['status']=='failed' for r in state['browser_reports'] for x in r['checks']),state['browser_reports']
   broken={**state['current']['files'],'styles.css':'body{margin:0}input,select,button{height:20px;min-height:0;padding:0;font:12px serif}textarea{height:20px;min-height:0}'}
   res=await c.post(url+'/files',json={'base_revision':state['revision'],'files':broken});assert res.status_code==200,res.text
   # Reload projects to observe external editing, then inspect browser findings.
   await page.get_by_role('button',name='Voltar aos projetos',exact=True).click()
   await page.locator('.ss-saved-card').filter(has_text='Revisão visual teste').click()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   await page.get_by_role('button',name='Testar esta prévia',exact=True).click()
   await expect(page.get_by_role('button',name='Testar esta prévia',exact=True)).to_be_enabled(timeout=15000)
   await expect(page.locator('.ss-notification')).to_contain_text('apontaram problemas')
   state=(await c.get(url)).json()
   assert any(x['status']=='failed' and x['name']=='Campos e botões com tamanho utilizável' for r in state['browser_reports'] for x in r['checks'])
   # A failed generation remains on the same project, then the button actually reruns it.
   result=await c.post(url+'/generate',json={'mode':'autonomous','prompt':'simular falha 429, corrija os formulários.'});assert result.status_code==200
   failed=await wait_job(c,id);assert failed['status']=='failed'
   await page.get_by_role('button',name='Voltar aos projetos',exact=True).click()
   await page.locator('.ss-saved-card').filter(has_text='Revisão visual teste').click()
   retry=page.locator('.ss-job-error').get_by_role('button',name='Tentar novamente',exact=True)
   await expect(retry).to_be_visible()
   calls=(await c.get('/fixture/calls')).json()['site']
   await retry.click()
   await expect(retry).to_be_visible(timeout=15000)
   failed_again=await wait_job(c,id)
   assert failed_again['status']=='failed' and failed_again['revision']==failed['revision']
   assert (await c.get('/fixture/calls')).json()['site']>calls
   await c.post('/fixture/recover-retry')
   await retry.click()
   await expect(page.locator('.ss-badge')).to_contain_text('Versão disponível',timeout=15000)
   recovered=await wait_job(c,id)
   assert recovered['status']=='ready' and recovered['last_request']==failed['last_request'] and recovered['revision']==failed['revision']+1
   assert len((await c.get('/studio/projects')).json()['projects'])==1
   assert recovered['assets']==failed['assets']
   # Closing a Studio with active sharing stops the browser tracks.
   await page.get_by_role('tab',name='Ver minha tela',exact=True).click()
   await page.get_by_role('button',name='Compartilhar tela',exact=True).click()
   await expect(page.get_by_role('button',name='Capturar este site',exact=True)).to_be_visible()
   await page.get_by_role('button',name='Fechar Estúdio de Sites',exact=True).click()
   assert await page.evaluate('window.testShares.every(s=>s.getTracks().every(t=>t.readyState==="ended"))')
   assert not errors,errors
   await browser.close()
 print('PASS: full preview and ESC; audio-free sharing; explicit frame review; revisioned repair; upload/discard; track cleanup; real CSS/form geometry reports; retry button fails safely then recovers same request/project. Vision/code/OS chooser are test fixtures, not paid API or Windows validation.')

asyncio.run(main())
