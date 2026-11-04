"""Browser regression: interim words are visible before the audio is transcribed."""
import asyncio
import base64
import http.server
import json
import sys
import threading
from functools import partial
from pathlib import Path

from playwright.async_api import async_playwright, expect


ROOT = Path(__file__).resolve().parents[2]
SPEECH = base64.b64encode((ROOT / 'frontend/scripts/fixtures/speech-16k.pcm').read_bytes()).decode()


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'")
        super().end_headers()


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'cronos')))
threading.Thread(target=server.serve_forever, daemon=True).start()


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'], headless=True)
        page = await browser.new_page(viewport={'width': 1366, 'height': 900})
        await page.add_init_script(f"""
            window.pywebview={{api:{{connection:async()=>({{token:'live-test'}})}}}};
            class FakeRecognition {{
              start() {{
                setTimeout(()=>this.onresult?.({{results:[{{0:{{transcript:'Cronos, quem foi Platão',confidence:0}},length:1,isFinal:false}}]}}),80);
              }}
              stop() {{ this.onresult?.({{results:[{{0:{{transcript:'Cronos, quem foi Platão',confidence:.99}},length:1,isFinal:true}}]}}); this.onend?.(); }}
              abort() {{ this.onend?.(); }}
            }}
            window.SpeechRecognition=FakeRecognition;
            navigator.mediaDevices.getUserMedia=async()=>{{
              const context=new AudioContext(),destination=context.createMediaStreamDestination();
              const bytes=Uint8Array.from(atob('{SPEECH}'),char=>char.charCodeAt(0));
              const samples=new Int16Array(bytes.buffer),buffer=context.createBuffer(1,samples.length,16000);
              const channel=buffer.getChannelData(0);
              for(let i=0;i<samples.length;i++)channel[i]=samples[i]/32768;
              const source=context.createBufferSource(),gain=context.createGain();
              source.buffer=buffer;source.loop=true;gain.gain.value=.3;
              source.connect(gain);gain.connect(destination);source.start();
              window.stopMicAudio=()=>source.stop();
              return destination.stream;
            }};
        """)
        await page.route('**/status', lambda route: route.fulfill(json={'fish_configured': False, 'fish_speech_configured': False, 'transcription_provider': 'vosk', 'direct_audio_chat': '--direct' in sys.argv}))
        await page.route('**/panels', lambda route: route.fulfill(json={'preferences': {'device_auto_connect': False}}))
        await page.route('**/monitor?*', lambda route: route.fulfill(json={'cursor': 0, 'alerts': [], 'events': []}))
        await page.route('**/memory/**', lambda route: route.fulfill(json={'nodes': [], 'edges': [], 'total': 0, 'next_offset': None}))
        await page.route('**/panels/latency', lambda route: route.fulfill(json={}))
        recorder_fallback = '--recorder' in sys.argv
        if recorder_fallback:
            await page.route('**/capture.worklet*.js', lambda route: route.abort())
        uploads, chats = [], []

        async def transcribe(route):
            uploads.append(route.request.post_data_buffer)
            await asyncio.sleep(.5)
            await route.fulfill(json={'text': 'quem foi Aristóteles'})

        await page.route('**/voice/transcribe', transcribe)
        async def chat(route):
            chats.append(json.loads(route.request.post_data)['message'])
            reply = 'Resposta de teste.'
            body = '\n'.join(json.dumps(event) for event in [
                {'type': 'reply', 'reply': reply},
                {'type': 'result', 'result': {'reply': reply, 'session_id': 'live-dictation', 'tool_results': []}},
            ]) + '\n'
            await route.fulfill(body=body, content_type='application/x-ndjson')

        await page.route('**/chat/stream', chat)
        if '--direct' in sys.argv:
            await page.route('**/chat/audio/stream*', lambda route: route.abort())
        await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
        normal_mode = '--normal' in sys.argv
        if not normal_mode:
            await page.get_by_role('button', name='Iniciar ditado longo').click()
        await page.get_by_role('button', name='Ligar microfone').click()
        await expect(page.get_by_role('button', name='Desligar microfone')).to_have_attribute('aria-pressed', 'true')
        if normal_mode:
            await expect(page.locator('.cronos-live-transcript')).to_contain_text('Cronos, quem foi Platão', timeout=10000)
        else:
            await expect(page.locator('#chat-input')).to_have_value('Cronos, quem foi Platão', timeout=10000)
        assert not uploads, 'Interim text appeared only after the final audio request.'
        await page.evaluate('stopMicAudio()')
        await page.get_by_role('button', name='Enviar fala agora').click()
        if normal_mode:
            for _ in range(100):
                if chats:
                    break
                await page.wait_for_timeout(100)
            assert chats == ['Cronos, quem foi Platão'], chats
            assert not uploads, 'A prévia final confirmada pelo navegador não precisa retranscrever o áudio.'
        else:
            await expect(page.locator('#chat-input')).to_have_value('quem foi Aristóteles', timeout=10000)
            assert len(uploads) == 1 and len(uploads[0]) > 1000, (len(uploads), [len(audio) for audio in uploads])
        assert await page.get_by_role('button', name='Desligar microfone').get_attribute('aria-pressed') == 'true'
        await page.get_by_role('button', name='Abrir Estúdio de Sites').click()
        await expect(page.get_by_role('dialog', name='Estúdio de Sites')).to_be_visible(timeout=10000)
        await browser.close()
        print('PASS:', 'MediaRecorder fallback' if recorder_fallback else 'AudioWorklet',
              'shows interim speech;', 'normal turn submitted' if normal_mode else 'long dictation corrected by final audio;',
              'microphone remains open.')


try:
    asyncio.run(main())
finally:
    server.shutdown()
