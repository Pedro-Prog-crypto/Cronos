"""Browser checks against real panel routes with isolated memory and fake providers.
No user keys, paid calls, real Windows commands, or user-vault writes.
"""
import asyncio, http.server, json, os, sys, threading, tempfile, io, math, struct, wave
from pathlib import Path
from functools import partial
from types import SimpleNamespace
from urllib.parse import urlsplit
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright, expect
from cronos.app import create_app
from cronos.config import Settings
from cronos.providers import Gemini

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'.cronos-local'/'panel-previews';OUTPUT.mkdir(parents=True,exist_ok=True)
TOKEN='browser-test-only-'+'x'*32
AUTH={'Authorization':'Bearer '+TOKEN}
class Provider:
 async def reply(self,system,messages):
  return {'reply':json.dumps({'summary':'Cena de teste','text':'CRONOS','objects':[{'name':'Notebook','confidence':.9,'box':[.2,.2,.4,.4]}]}),'topics':[]}
def runner(name,timeout):
 if name=='devices':return {'cpu':'CPU de teste','ram_gib':4,'audio':[{'name':'Microfone de teste','status':'OK'}]}
 return {'windows':{'build':19045},'defender':{'antivirus_enabled':True,'realtime_enabled':True,'signatures_age_days':1},'firewall':[{'name':'Public','enabled':True}],'encryption':'Off','secure_boot':True,'legacy_rules':[]}
speech_calls=[]
class Fish:
 @property
 def tts(self):return self
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
 async def convert(self,**kwargs):
  speech_calls.append(kwargs)
  data=io.BytesIO()
  with wave.open(data,'wb') as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
   w.writeframes(b''.join(struct.pack('<h',int(4000*math.sin(i*2*math.pi*220/24000))) for i in range(60000)))
  return data.getvalue()
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main(client):
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path=os.getenv('CRONOS_TEST_CHROMIUM') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required'])
  page=await b.new_page(viewport={'width':1672,'height':941},timezone_id='America/Sao_Paulo',permissions=['microphone','camera'])
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.add_init_script("const originalPlay=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){window.testPlayer=this;return originalPlay.call(this)};window.pywebview={api:{connection:async()=>({token:'"+TOKEN+"'})}}")
  async def backend(route):
   url=urlsplit(route.request.url)
   if url.path.startswith('/ui/') or url.path in ['/world/view','/tests']:await route.continue_();return
   response=client.request(route.request.method,url.path+('?' +url.query if url.query else ''),content=route.request.post_data_buffer,headers={**AUTH,**({'Content-Type':route.request.headers['content-type']} if 'content-type' in route.request.headers else {})})
   await route.fulfill(status=response.status_code,body=response.content,content_type=response.headers.get('content-type','application/json'))
  await page.route('**/*',backend)
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  await expect(page.get_by_role('button',name='Desligar microfone')).to_be_visible()
  labels=['PROCESSAMENTO','VISÃO COMPUTACIONAL','SÍNTESE DE VOZ','ENTENDIMENTO DE LINGUAGEM','PLANEJAMENTO','FERRAMENTAS','INTEGRAÇÕES','BANCO DE DADOS','INTERNET','DISPOSITIVOS','SEGURANÇA','MONITORAMENTO']
  for index,label in enumerate(labels):
   await page.get_by_role('button',name=label,exact=True).click()
   panel=page.get_by_role('dialog',name=label,exact=True)
   await expect(panel).to_be_visible();await page.wait_for_timeout(250)
   assert not await panel.locator('iframe').count()
   assert await panel.evaluate('p=>p.scrollWidth<=p.clientWidth+1')
   await panel.screenshot(path=str(OUTPUT/f'{index+1:02d}-{label.lower().replace(" ","-")}.png'))
   if index==2:
    await page.get_by_role('button',name='Aumentar VELOCIDADE',exact=True).click()
    await page.wait_for_timeout(100)
    assert abs(client.get('/panels',headers=AUTH).json()['preferences']['voice_speed']-1.1)<.001
    await page.get_by_role('button',name='TESTAR VOZ',exact=True).click()
    await expect(page.get_by_text('REPRODUZINDO',exact=True)).to_be_visible()
    await page.wait_for_function("()=>{const c=document.querySelector('.voice-wave canvas'),d=c.getContext('2d').getImageData(0,0,800,170).data;for(let y=0;y<170;y++){if(y>=83&&y<=87)continue;for(let x=0;x<800;x++){const i=(y*800+x)*4;if(d[i]>180&&d[i+1]<90&&d[i+3]>100)return true;}}return false;}",timeout=10000)
    assert speech_calls[-1]['speed']==1.1 and speech_calls[-1]['reference_id']=='original-voice'
    await page.get_by_role('button',name='Aumentar TOM',exact=True).click()
    await page.wait_for_function('()=>window.testPlayer?.playbackRate>1&&window.testPlayer?.preservesPitch===false')
    await page.get_by_role('button',name='Pausar ou retomar voz',exact=True).click()
    assert await page.evaluate('window.testPlayer.paused')
    await page.get_by_role('button',name='Pausar ou retomar voz',exact=True).click()
    assert not await page.evaluate('window.testPlayer.paused')
   if index==3:
    await page.get_by_label('Contexto da conversa',exact=True).select_option('12')
    await page.wait_for_timeout(100)
    assert client.app.state.engine.settings.context_messages==12
    await page.get_by_role('switch',name='Responder só após ser chamado',exact=True).click()
    await expect(page.get_by_role('switch',name='Responder só após ser chamado',exact=True)).to_have_attribute('aria-checked','true')
   if index==4:
    await page.get_by_role('button',name='CRIAR PLANO',exact=True).click()
    await page.get_by_label('Objetivo do plano',exact=True).fill('Estudar Platão')
    await page.get_by_label('Etapas do plano',exact=True).fill('Ler\nEscrever\nRevisar')
    await page.get_by_role('button',name='Salvar plano',exact=True).click()
    await expect(page.get_by_role('heading',name='Estudar Platão',exact=True)).to_be_visible()
    await page.get_by_label('Estado da etapa 1',exact=True).select_option('completed')
    await page.wait_for_timeout(100)
    assert client.app.state.missions.list()[0]['plan']['steps'][0]['done']
   if index==5:
    switches=page.get_by_role('switch',name='ATIVADA',exact=True)
    await switches.first.click();await page.wait_for_timeout(100)
    assert client.get('/panels',headers=AUTH).json()['preferences']['web_enabled'] is False
   if index==6:
    await page.get_by_role('button',name='TESTAR CONEXÃO',exact=True).click()
    await expect(page.get_by_role('status')).to_contain_text('integridade SQLite verificadas')
   if index==7:
    await page.get_by_role('button',name='CRIAR BACKUP',exact=True).click()
    await expect(page.get_by_role('status')).to_contain_text('Backup criado')
    assert client.get('/panels',headers=AUTH).json()['backup'] is not None
   if index==10:
    await page.get_by_role('button',name='VERIFICAR WINDOWS',exact=True).click()
    await expect(page.get_by_role('status')).to_contain_text('Auditoria do Windows concluída')
   if index==11:
    await page.get_by_label('INTERVALO',exact=True).select_option('15')
    await page.wait_for_timeout(100)
    assert client.get('/panels',headers=AUTH).json()['preferences']['refresh_seconds']==15
   await panel.screenshot(path=str(OUTPUT/f'{index+1:02d}-{label.lower().replace(" ","-")}.png'))
   await page.get_by_role('button',name='Fechar módulo',exact=True).click()
   await expect(panel).to_have_count(0)
  await page.get_by_role('button',name='VISÃO COMPUTACIONAL',exact=True).click()
  await page.get_by_role('button',name='ATIVAR CÂMERA',exact=True).click()
  await page.wait_for_function('()=>document.querySelector(".vision-preview video")?.videoWidth>0')
  await page.get_by_role('button',name='ANALISAR IMAGEM',exact=True).click()
  await expect(page.locator('.vision-bound')).to_have_count(1)
  await expect(page.locator('.vision-description')).to_contain_text('CRONOS')
  await page.keyboard.press('Escape');assert not await page.locator('.cronos-panel').count()
  await page.evaluate('''()=>{const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=async(c)=>{const s=await original(c);if(c.video){window.delayedCamera=s;await new Promise(r=>setTimeout(r,700));}return s;};}''')
  await page.get_by_role('button',name='VISÃO COMPUTACIONAL',exact=True).click()
  await page.get_by_role('button',name='ATIVAR CÂMERA',exact=True).click()
  await page.get_by_role('button',name='DISPOSITIVOS',exact=True).click()
  await page.wait_for_function('()=>window.delayedCamera&&window.delayedCamera.getVideoTracks().every(t=>t.readyState==="ended")')
  await page.keyboard.press('Escape')
  assert not errors,errors
  print('PASS: all 12 panels render; preferences, voice speed, context, wake gate, plans, permissions, vault verification, backup, Windows audit, refresh interval and camera analysis operate through real isolated routes.')
  mobile=await b.new_page(viewport={'width':800,'height':650})
  await mobile.add_init_script("window.pywebview={api:{connection:async()=>({token:'"+TOKEN+"'})}}")
  await mobile.route('**/*',backend);await mobile.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  # At this width the main stage hides the large tree. Inspect the panel at desktop,
  # then resize without adding a launcher absent from the user's reference.
  await page.get_by_role('button',name='MONITORAMENTO',exact=True).click();await page.set_viewport_size({'width':800,'height':650})
  await expect(page.locator('.cronos-panel')).to_be_visible()
  assert await page.locator('.cronos-panel').evaluate('p=>p.scrollWidth<=p.clientWidth+1')
  await b.close()
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);personality=root/'personality.md';personality.write_text('Personalidade de teste.')
 settings=Settings(root/'vault',personality,TOKEN,'gemini','test-gemini','gemini-test','test-fish','original-voice','s1','http://127.0.0.1:11434','test-model',fish_format='wav',providers_file=root/'providers.json')
 with TestClient(create_app(settings,provider=Provider(),vision_provider=Provider(),windows_runner=runner,windows_platform='win32',fish_factory=Fish),base_url='http://127.0.0.1',client=('127.0.0.1',50000)) as client:
  for i in range(150):
   (settings.vault/'Temas'/f'Tema-{i:03d}.md').write_text(f'# Nota de demonstração {i}\n\n[[Temas/Tema-{max(0,i-5):03d}]]')
  client.post('/memory/sync',headers=AUTH)
  try:asyncio.run(main(client))
  finally:server.shutdown()
