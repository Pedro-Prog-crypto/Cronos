"""No native desktop access: use explicitly injected capture/provider fixtures."""
import asyncio,os
import httpx
from playwright.async_api import async_playwright,expect
BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8923')
AUTH={'Authorization':'Bearer studio-test-only'}
async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH) as client:
  await client.post('/fixture/reset-live-screen')
  before=(await client.get('/fixture/calls')).json()
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=await browser.new_page(viewport={'width':1672,'height':1000});errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   await page.add_init_script("window.screenPickerCalls=0;if(navigator.mediaDevices)navigator.mediaDevices.getDisplayMedia=async()=>{window.screenPickerCalls++;throw Error('The local mode must not request a browser picker.');};")
   await page.goto(BASE+'/#cronos-session=studio-test-only')
   await page.get_by_role('button',name='Ver minha tela',exact=True).click()
   widget=page.get_by_role('region',name='Acompanhamento da tela',exact=True)
   await expect(widget).to_contain_text('TELA INTEIRA · AO VIVO',timeout=10000)
   await page.wait_for_timeout(1500)
   calls=(await client.get('/fixture/calls')).json()
   assert calls['screen_captures']>=2 and calls.get('chat',0)==before.get('chat',0)
   assert await page.evaluate('window.screenPickerCalls')==0
   await page.get_by_role('button',name='Mostrar tela acompanhada',exact=True).click()
   await expect(widget.locator('img')).to_be_visible(timeout=5000)
   # Asking about the screen uses the latest frame, not a stale analysis paragraph.
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
   await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('O que você vê nessa tela?')
   await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
   for _ in range(60):
    calls=(await client.get('/fixture/calls')).json()
    if calls.get('screen_context'):break
    await asyncio.sleep(.1)
   assert calls.get('screen_context'),calls
   # Minimize/opening another feature must not end the screen session.
   await page.get_by_role('button',name='ESTÚDIO DE SITES',exact=True).click()
   await page.get_by_role('button',name='Minimizar Estúdio de Sites',exact=True).click()
   await expect(widget).to_be_visible()
   previous=calls['screen_captures'];await page.wait_for_timeout(1200)
   assert (await client.get('/fixture/calls')).json()['screen_captures']>previous
   # Typed control follows exactly the same runCommand path as transcribed voice.
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
   await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill('Cronos, pare de ver minha tela')
   await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
   await expect(widget).not_to_be_visible(timeout=5000)
   await page.wait_for_timeout(1100)
   stopped=(await client.get('/fixture/calls')).json()['screen_captures']
   await page.wait_for_timeout(1200)
   assert (await client.get('/fixture/calls')).json()['screen_captures']==stopped
   assert not errors,errors
   await browser.close()
   print('PASS: opt-in full-screen session, no browser picker in local mode, ongoing capture without AI calls/narration, current image on request, capture survives Studio minimization, explicit stop clears capture. Desktop and AI are test fixtures.')
asyncio.run(main())
