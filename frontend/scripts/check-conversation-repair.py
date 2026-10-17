"""Real local backend + browser; media, AI and display chooser use explicit fixtures."""
import asyncio,base64,io,json,math,socket,struct,sys,tempfile,threading,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import uvicorn
from playwright.async_api import async_playwright,expect
from cronos.app import create_app
from cronos.config import Settings
from cronos import music,media_streams,stremio

audio=io.BytesIO()
with wave.open(audio,'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
    f.writeframes(b''.join(struct.pack('<h',int(1500*math.sin(i*2*math.pi*220/16000))) for i in range(320000)))
WAV=audio.getvalue();spoken=[];systems=[];images=[];opened=[]
class Chat:
    async def reply(self,system,messages):
        systems.append(system);images.append(bool(messages[-1].get("image")))
        return {'reply':'C:\\Users\\Pedro\\vault\\Temas\\mentalista.md\nSenhor, a captura mostra campos sobrepostos.\n```python\nprint("private-code")\n```\n\nResumo para memória: O usuário falou sobre O Mentalista.', 'topics':[], 'tool_calls':[]}
class Vision:
    async def reply(self,system,messages):
        assert messages[0]['image']['mime_type']=='image/jpeg'
        return {'reply':'A captura mostra campos sobrepostos e falta de espaçamento.', 'topics':[],'tool_calls':[]}
class Fish:
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    @property
    def tts(self):return self
    async def convert(self,**kwargs):spoken.append(kwargs['text']);return WAV
async def search(query,similar=False,video=False):return {'query':query,'video':video,'tracks':[{'id':'abcdefghijk','title':'Música de teste'}]}
def resolve(ident,clip):return {'audio_url':'https://media.example/audio.wav','video_url':None,'title':'Música de teste'}
class Response:
    status=200
    def __init__(self):self.buffer=io.BytesIO(WAV)
    def getheader(self,name,default=None):return {'Content-Length':str(len(WAV)),'Accept-Ranges':'bytes'}.get(name,default)
    def read1(self,size):return self.buffer.read(size)
class Conn:
    def close(self):pass
def open_media(url,byte_range=None):return Conn(),Response(),'audio/wav'
async def catalog(body):return {'query':body.query,'kind':body.kind,'items':[{'id':'tt1196946','name':body.query,'year':'2008','kind':body.kind}]}
async def sources(body):return [{'name':'Fonte de teste autorizada','title':'Áudio gerado para teste','url':'https://media.example/audio.wav'}]
music.search_music=search;music.resolve_native=resolve;media_streams.open_media=open_media;stremio.search=catalog;stremio.addon_streams=sources

async def main(base,app):
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
        page=await browser.new_page(viewport={'width':1366,'height':900})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        await page.add_init_script("""window.pywebview={api:{connection:async()=>({token:'repair-fixture-only'})}};
        window.micStarts=0;navigator.mediaDevices.getUserMedia=async()=>{window.micStarts++;const ctx=new AudioContext(),dest=ctx.createMediaStreamDestination();window.inputFixture=dest.stream;return dest.stream;};
        window.displayCalls=[];navigator.mediaDevices.getDisplayMedia=async options=>{
          window.displayCalls.push(options);const canvas=document.createElement('canvas');canvas.width=900;canvas.height=600;
          const c=canvas.getContext('2d');c.fillStyle='#fff';c.fillRect(0,0,900,600);c.fillStyle='#000';c.font='32px Arial';c.fillText('Campos sobrepostos',30,100);
          window.sharedFixture=canvas.captureStream(2);return window.sharedFixture;};""")
        await page.goto(base+'/')
        await page.get_by_role('button',name='Ver minha tela',exact=True).click()
        await page.get_by_role('button',name='Compartilhar tela inteira',exact=True).click()
        widget=page.get_by_role('region',name='Acompanhamento da tela',exact=True)
        await expect(widget).to_contain_text('TELA INTEIRA · AO VIVO')
        await page.get_by_role('button',name='Mostrar tela acompanhada',exact=True).click()
        await expect(widget.locator('img')).to_be_visible()
        assert not app.state.engine.screen_observations and app.state.live_screen.frame
        assert await page.evaluate('displayCalls[0].audio===false')
        assert not spoken # Updating the capture must never trigger narration.
        async def command(text):
            await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
            await page.locator('.phrase-card').click()
            await page.locator('#chat-input').fill(text)
            await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
        await command('O que está errado na captura compartilhada?')
        await page.wait_for_function("()=>!document.querySelector('.reference-mic.thinking')")
        assert images[-1] and any('Acompanhamento da tela inteira ativado' in system for system in systems)
        await page.get_by_role('button',name='Parar de ver a tela',exact=True).click()
        assert await page.evaluate('sharedFixture.getVideoTracks()[0].readyState')=='ended'
        assert app.state.live_screen.frame is None
        await page.wait_for_timeout(1500)
        assert spoken and all('private-code' not in text and 'O usuário falou' not in text and 'Users' not in text and 'Resumo' not in text for text in spoken),spoken
        await command('Cronos, tocar música Nada pra Fazer')
        await page.wait_for_function("()=>document.querySelector('.music-player audio')?.currentTime>0")
        assert (await page.locator('.music-player audio').get_attribute('src')).startswith('/media/stream/')
        assert await page.locator('.music-player iframe').count()==0
        await page.locator('.reference-mic').click()
        await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
        assert await page.locator('.music-player audio').evaluate('e=>e.paused')
        await page.keyboard.press('F4')
        await expect(page.get_by_role('button',name='Ligar microfone')).to_have_attribute('aria-pressed','false')
        await page.get_by_role('button',name='Continuar',exact=True).click()
        # Fail the actual HTML element and recover with a new resolver ticket.
        await page.locator('.music-player audio').evaluate("e=>e.dispatchEvent(new Event('error'))")
        await page.get_by_role('button',name='Preparar música novamente',exact=True).click()
        await page.wait_for_function("()=>document.querySelector('.music-player audio')?.currentTime>0")
        await page.get_by_role('button',name='Fechar música',exact=True).click()
        await command('Cronos, abrir a série O Mentalista temporada 1 episódio 2')
        await expect(page.get_by_role('dialog',name='Filmes e séries no Stremio')).to_be_visible()
        await page.get_by_label('Manifest do complemento Stremio').fill('https://addon.example/manifest.json')
        await page.get_by_role('button',name='Consultar fontes de O Mentalista').click()
        await page.get_by_role('button',name='Fonte de teste autorizada',exact=False).click()
        await page.wait_for_function("()=>document.querySelector('.stremio-playback video')?.currentTime>0")
        assert len(page.context.pages)==1 and not errors,errors
        await browser.close()
        print('PASS: actual authenticated backend, screen consent/frame/session/context and track cleanup; real WAV speech without paths/code/memory; opaque media playback and retry; Stremio internal source playback. AI, catalog, media and display chooser are fixtures; no live accounts tested.')

with tempfile.TemporaryDirectory(prefix='cronos-repair-browser-') as directory:
    root=Path(directory);(root/'personality.md').write_text('Responda ao senhor com clareza.')
    settings=Settings(root/'vault',root/'personality.md','repair-fixture-only','gemini','','gemini-2.5-flash','fixture-key','','s1','http://127.0.0.1:11434','gemma3:4b',providers_file=root/'providers.json',gemini_transport='rest')
    app=create_app(settings,Chat(),fish_factory=Fish,vision_provider=Vision())
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:asyncio.run(main(f'http://127.0.0.1:{port}',app))
    finally:server.should_exit=True;thread.join(timeout=10)
