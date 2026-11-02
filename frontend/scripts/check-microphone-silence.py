"""Browser microphone check: silence cannot turn into a cloud question."""
import asyncio
import base64
import http.server
import json
import threading
from functools import partial
from pathlib import Path

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SPEECH = base64.b64encode((ROOT/'frontend/scripts/fixtures/speech-16k.pcm').read_bytes()).decode()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def end_headers(self):
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'")
        super().end_headers()


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever, daemon=True).start()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'], headless=True)
        page = await browser.new_page(viewport={'width':1366,'height':900})
        await page.add_init_script("window.testSpeech='"+SPEECH+"';"+"""window.pywebview={api:{connection:async()=>({token:'test'})}};
          navigator.mediaDevices.getUserMedia=async()=>{
            const ctx=new AudioContext(),dest=ctx.createMediaStreamDestination(),voice=ctx.createBufferSource(),gain=ctx.createGain();
            const pcm=new Int16Array(Uint8Array.from(atob(testSpeech),c=>c.charCodeAt(0)).buffer);
            voice.buffer=ctx.createBuffer(1,pcm.length,16000);voice.buffer.copyToChannel(Float32Array.from(pcm,v=>v/32768),0);
            voice.loop=true;voice.connect(gain);gain.connect(dest);gain.gain.value=0;voice.start();window.micGain=gain;
            return dest.stream;};""")
        await page.route('**/status', lambda r:r.fulfill(json={'fish_configured':False,'fish_speech_configured':False,'transcription_provider':'vosk','direct_audio_chat':False,'local_voice_interrupt':False}))
        await page.route('**/panels', lambda r:r.fulfill(json={'preferences':{'device_auto_connect':True,'called_only':False}}))
        await page.route('**/monitor?*', lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
        await page.route('**/memory/**', lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
        await page.route('**/panels/latency', lambda r:r.fulfill(json={}))
        recognized=[]; chats=[]
        async def asr(route):
            recognized.append(True)
            await route.fulfill(json={'text':'Quem foi Sócrates?'})
        async def chat(route):
            chats.append(True)
            result={'type':'result','result':{'reply':'Sócrates viveu em Atenas.','session_id':'fixture','tool_results':[], 'warnings':[]}}
            await route.fulfill(body=json.dumps(result)+'\n',content_type='application/x-ndjson')
        await page.route('**/voice/transcribe', asr)
        await page.route('**/chat/stream', chat)
        await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
        await expect(page.get_by_role('button',name='Desligar microfone')).to_have_attribute('aria-pressed','true')
        await page.wait_for_timeout(1200)
        await expect(page.get_by_role('button',name='Enviar fala agora')).to_be_disabled()
        await page.wait_for_timeout(350)
        assert not recognized and not chats, 'Enviar durante silêncio não pode disparar reconhecimento nem conversa.'
        await page.evaluate('()=>{micGain.gain.value=.25;setTimeout(()=>micGain.gain.value=0,850)}')
        for _ in range(60):
            if recognized: break
            await page.wait_for_timeout(100)
        assert len(recognized)==1, 'Uma frase real precisa chegar ao reconhecedor uma vez.'
        print('PASS: silêncio e envio manual não iniciam ASR; uma frase real inicia exatamente uma transcrição. Microfone sintético e resposta simulada.')
        await browser.close()


try: asyncio.run(main())
finally: server.shutdown()
