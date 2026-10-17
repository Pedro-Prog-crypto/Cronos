"""Actual Studio continuation in the fixture backend, with native audio playback."""
import asyncio,io,math,os,struct,wave
import httpx
from playwright.async_api import async_playwright,expect

BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8921')
AUTH={'Authorization':'Bearer studio-test-only'}
data=io.BytesIO()
with wave.open(data,'wb') as file:
 file.setnchannels(1);file.setsampwidth(2);file.setframerate(8000)
 file.writeframes(b''.join(struct.pack('<h',int(900*math.sin(i*2*math.pi*220/8000))) for i in range(240000)))

async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH) as client:
  assert (await client.get('/health')).status_code==200
  await client.patch('/panels/preferences',json={'device_auto_connect':False,'proactive_suggestions':False})
  for old in (await client.get('/studio/projects')).json()['projects']:
   if old['name']=='Hotel em segundo plano':await client.post('/studio/projects/'+old['id']+'/archive',json={'archived':True})
  initial_calls=(await client.get('/fixture/calls')).json()
  project=(await client.post('/studio/projects',json={'name':'Hotel em segundo plano','category':'hotel','brief':'Um hotel com contato e solicitação de horário.'})).json()
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
   page=await browser.new_page(viewport={'width':1672,'height':1000});errors=[]
   page.on('pageerror',lambda error:errors.append(str(error)))
   await page.route('**/music/search?*',lambda route:route.fulfill(json={'tracks':[{'id':'abcdefghijk','title':'Música de teste'}]}))
   await page.route('**/music/resolve?*',lambda route:route.fulfill(json={'audio_url':'/fixture/audio.wav','video_url':None,'title':'Música de teste'}))
   await page.route('**/fixture/audio.wav',lambda route:route.fulfill(body=data.getvalue(),content_type='audio/wav'))
   await page.goto(BASE+'/#cronos-session=studio-test-only')
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await page.get_by_role('button',name='Meus projetos',exact=False).first.click()
   await page.locator('.ss-saved-card').filter(has_text=project['name']).first.click()
   await page.get_by_label('Pedido de alteração do site',exact=True).fill('Crie um site específico com os formulários integrados e uma identidade editorial.')
   await page.get_by_role('button',name='CRIAR COM IA',exact=True).click()
   await page.get_by_role('button',name='CONFIRMAR SOLICITAÇÃO',exact=True).click()
   await expect(page.locator('.ss-run')).to_contain_text('EM CRIAÇÃO')
   await page.get_by_role('button',name='Minimizar Estúdio de Sites',exact=True).click()
   await expect(page.get_by_role('dialog',name='Estúdio de Sites',exact=True)).not_to_be_visible()
   await expect(page.get_by_role('button',name='Restaurar Estúdio de Sites',exact=True)).to_be_visible()
   # A hidden Studio must not intercept music requests or trap focus.
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
   await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('Cronos, coloque música Nada pra Fazer')
   await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
   await page.wait_for_function("()=>document.querySelector('.music-player audio')?.currentTime>.1")
   await page.locator('.music-player audio').evaluate("audio=>audio.dataset.identity='preserved'")
   await page.get_by_role('button',name='Minimizar música',exact=True).click()
   await expect(page.locator('.music-player')).not_to_be_visible()
   await expect(page.get_by_role('button',name='Restaurar Música',exact=True)).to_be_visible()
   before=await page.locator('.music-player audio').evaluate('audio=>audio.currentTime')
   await page.wait_for_timeout(600)
   assert await page.locator('.music-player audio').evaluate('audio=>audio.currentTime')>before+.2
   await page.get_by_role('button',name='Restaurar Estúdio de Sites',exact=True).click()
   await expect(page.get_by_role('dialog',name='Estúdio de Sites',exact=True)).to_be_visible()
   await expect(page.locator('.ss-run')).to_contain_text('Versão salva',timeout=20000)
   result=(await client.get('/studio/projects/'+project['id'])).json()
   assert result['status']=='ready' and result['revision']==1 and len(result['history'])==2,result.get('error')
   assert any(event['phase']=='continuation' for event in result['events'])
   assert not any(event['phase']=='fallback' for event in result['events'])
   # Restoring a mini player releases the Studio without losing either window.
   await page.get_by_role('button',name='Restaurar Música',exact=True).click()
   assert await page.locator('.music-player audio').get_attribute('data-identity')=='preserved'
   assert not await page.locator('.music-player audio').evaluate('audio=>audio.paused')
   await expect(page.get_by_role('dialog',name='Estúdio de Sites',exact=True)).not_to_be_visible()
   await page.get_by_role('button',name='Minimizar música',exact=True).click()
   await page.get_by_role('button',name='Pausar música minimizada',exact=True).click()
   assert await page.locator('.music-player audio').evaluate('audio=>audio.paused')
   await page.get_by_role('button',name='Continuar música minimizada',exact=True).click()
   assert not await page.locator('.music-player audio').evaluate('audio=>audio.paused')
   # Analysis uploads and form values survive minimization too.
   await page.get_by_role('button',name='Analisar imagem',exact=True).click()
   from PIL import Image
   image=io.BytesIO();Image.new('RGB',(30,30),'blue').save(image,'PNG')
   await page.get_by_label('Selecionar imagem',exact=True).set_input_files({'name':'captura.png','mimeType':'image/png','buffer':image.getvalue()})
   await page.get_by_label('Pergunta sobre o arquivo',exact=True).fill('Um pedido preservado ao minimizar.')
   await page.get_by_role('button',name='Minimizar imagem',exact=True).click()
   await expect(page.get_by_role('button',name='Restaurar Imagem',exact=True)).to_be_visible()
   await page.get_by_role('button',name='Restaurar Imagem',exact=True).click()
   await expect(page.get_by_role('region',name='Análise de imagem',exact=True)).to_be_visible()
   await expect(page.get_by_label('Pergunta sobre o arquivo',exact=True)).to_have_value('Um pedido preservado ao minimizar.')
   await expect(page.locator('.analysis-panel img')).to_be_visible()
   await page.get_by_role('button',name='Fechar análise',exact=True).click()
   await page.get_by_role('button',name='Restaurar Estúdio de Sites',exact=True).click()
   await page.get_by_role('tab',name='Código',exact=True).click()
   editor=page.get_by_label('Editor de index.html',exact=True)
   edited=await editor.input_value()+'<!-- edição não salva preservada -->'
   await editor.fill(edited)
   await page.get_by_role('button',name='Minimizar Estúdio de Sites',exact=True).click()
   await page.get_by_role('button',name='Restaurar Estúdio de Sites',exact=True).click()
   await expect(editor).to_have_value(edited)
   assert (await client.get('/studio/projects/'+project['id'])).json()['revision']==1
   assert not errors,errors
   calls=(await client.get('/fixture/calls')).json()
   assert calls.get('continuations',0)==initial_calls.get('continuations',0)+1,calls
   await browser.close()
   print('PASS: Studio generated through output-limit continuation while minimized; task/revision preserved; hidden Studio did not intercept music/focus; same audio element kept playing; shelf pause/resume/restore; analysis minimize/restore. AI, catalog and audio are fixtures.')

asyncio.run(main())
