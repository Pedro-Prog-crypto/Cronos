"""Real compiled UI + HTTP server + SSE parser + audio playback; controlled AI/TTS.
No cloud credentials are used. These timings do not measure Gemini or Fish service latency.
Run after npm --prefix frontend run build: PYTHONPATH=. .venv/bin/python tools/check_conversation_latency_browser.py
"""
import asyncio
import io
import importlib
import json
import math
import shutil
import socket
import struct
import tempfile
import threading
import time
import wave
from pathlib import Path
from types import SimpleNamespace

import httpx
import uvicorn
from playwright.async_api import async_playwright

from cronos.app import create_app
from cronos.config import Settings
from cronos.conversation_transport import receive_conversation
from cronos.providers import parse_completed_reply, ProviderError
from cronos import usage

ROOT=Path(__file__).resolve().parents[1]
AUTH={'Authorization':'Bearer latency-fixture'}


def audio_fixture():
    output=io.BytesIO()
    with wave.open(output,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
        wav.writeframes(b''.join(struct.pack('<h',int(1200*math.sin(2*math.pi*220*i/16000))) for i in range(16000)))
    return output.getvalue()


class ControlledFish:
    fail_asr=False
    def __init__(self):self.tts=self;self.asr=self
    async def transcribe(self,**kwargs):
        await asyncio.sleep(.25)
        if self.fail_asr:raise RuntimeError("Controlled ASR failure")
        return SimpleNamespace(text="E aí, Kronos, de boa? Como é que você tá, mano?")
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def convert(self,**kwargs):
        await asyncio.sleep(.10)
        return audio_fixture()


class ControlledProvider:
    def __init__(self):self.mode='normal';self.finished=threading.Event();self.cancelled=threading.Event()
    async def reply(self,system,messages):
        if self.mode=='fail':raise ProviderError('Falha externa simulada.',503)
        if self.mode=='wait':
            try:await asyncio.sleep(30)
            finally:self.cancelled.set()
        self.finished.clear()
        owner=self
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                def event(text):return ('data: '+json.dumps({'candidates':[{'content':{'parts':[{'text':text}]}}]})+'\n\n').encode()
                await asyncio.sleep(.15)
                yield event('{"tool_calls":[],"reply":"Tudo certo, senhor. ')
                await asyncio.sleep(1.2)
                yield event('Como foi seu dia?",')
                await asyncio.sleep(.8)
                yield event('"topics":[]}')
                owner.finished.set()
        async def handle(request):return httpx.Response(200,headers={'Content-Type':'text/event-stream'},stream=Stream())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            response=await receive_conversation(client,'https://fixture.invalid/model:generateContent',{}, {})
        return parse_completed_reply(response.json()['candidates'][0]['content']['parts'][0]['text'])


async def exercise(base,provider,mic_file):
    checks=[];errors=[]
    async with async_playwright() as driver:
        browser=await driver.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox','--autoplay-policy=no-user-gesture-required','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',f'--use-file-for-fake-audio-capture={mic_file}'])
        page=await browser.new_page(viewport={'width':1366,'height':768})
        page.on('pageerror',lambda error:errors.append(str(error)))
        await page.goto(base+'/#cronos-session=latency-fixture')
        async def compose(text):
            if not await page.locator('#chat-input').is_visible():
                await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
                await page.locator('.phrase-card').click()
            await page.locator('#chat-input').fill(text)
            await page.get_by_role('button',name='Enviar mensagem',exact=True).click()
        await compose('E aí, Kronos, de boa? Como é que você tá, mano?')
        await page.locator('.response-clock').filter(has_text='Voz começou em').wait_for()
        assert not provider.finished.is_set(),'Voice must begin before the full response and metadata finish'
        await page.screenshot(path='/tmp/cronos-speed-clock.png')
        checks.append('compiled App plays first audio before complete provider response')
        async def history():
            response=await page.request.get(base+'/panels',headers=AUTH)
            return (await response.json())['latency_history']
        measured=(await history())[-1]
        assert 0<measured['response_ms']<5000
        checks.append('measured start under five seconds with controlled 150 ms AI / 100 ms TTS fixtures')
        await page.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        await page.get_by_role('button',name='Ver tempos das respostas').click()
        await page.get_by_role('heading',name='TEMPO DE CADA PERGUNTA').wait_for()
        assert await page.locator('.response-history tbody tr').count()==1
        checks.append('timing history is reachable from the stopwatch and records a single turn')
        await page.keyboard.press('Escape')
        provider.mode='wait'
        await compose('Teste de espera pendente')
        await page.locator('.response-clock').filter(has_text='Preparando resposta').wait_for()
        await page.wait_for_timeout(150)
        await page.keyboard.press('Escape')
        await page.locator('.response-clock').filter(has_text='Interrompido pelo senhor').wait_for()
        for _ in range(40):
            if provider.cancelled.is_set():break
            await asyncio.sleep(.05)
        assert provider.cancelled.is_set()
        checks.append('Escape cancels pending server generation and logs cancellation')
        provider.mode='fail'
        await compose('Teste de erro externo')
        await page.locator('.response-clock').filter(has_text='Resposta interrompida').wait_for()
        assert (await history())[-1]['status']=='failed'
        checks.append('failed request stays in history instead of disappearing from measurements')
        provider.mode='normal'
        await compose('Oi Cronos')
        await page.locator('.response-clock').filter(has_text='Voz começou em').wait_for()
        rows=await history()
        assert [row['status'] for row in rows[1:3]]==['cancelled','failed']
        assert rows[-1]['response_ms']>0
        checks.append('next question responds after cancellation and failure, without a stale lock')
        await page.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        await page.get_by_role('button',name='Ligar microfone',exact=True).click()
        await page.locator('.reference-mic.recording').wait_for()
        await page.wait_for_timeout(1100)
        await page.get_by_role('button',name='Enviar fala agora',exact=True).click()
        await page.locator('.response-clock').filter(has_text='Transcrevendo').wait_for()
        await page.locator('.response-clock').filter(has_text='Voz começou em').wait_for()
        voice_row=(await history())[-1]
        assert voice_row['source']=='voice' and voice_row['recognition_ms']>=250
        assert voice_row['response_ms']==voice_row['first_audio_ms']+voice_row['recognition_ms']+voice_row['endpoint_ms']
        checks.append('AudioWorklet manual send includes actual ASR and endpoint delay in the same question timer')
        await page.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        ControlledFish.fail_asr=True
        await page.wait_for_timeout(1100)
        await page.get_by_role('button',name='Enviar fala agora',exact=True).click()
        await page.locator('.response-clock').filter(has_text='Resposta interrompida').wait_for()
        failure=(await history())[-1]
        assert failure['source']=='voice' and failure['status']=='failed' and failure['first_audio_ms'] is None
        checks.append('ASR failure is recorded even when no chat request can be sent')
        await page.get_by_role('button',name='Desligar microfone',exact=True).click()
        importlib.import_module('cronos.app').VOICE_REQUEST_TIMEOUT_SECONDS=.04
        await compose('Oi Cronos, teste de voz indisponível')
        await page.locator('.response-clock').filter(has_text='Resposta interrompida').wait_for()
        await page.locator('.reference-mic.thinking, .reference-mic.generating').wait_for(state='detached')
        rows=await history()
        assert rows[-1]['status']=='failed' and rows[-1]['first_audio_ms'] is None
        await page.locator('.answer-card-deck').filter(has_text='Como foi seu dia?').wait_for()
        checks.append('stalled TTS finishes with a visible error while the complete written answer stays available')
        assert not errors,errors
        await page.close();await browser.close()
    return {'checks_passed':len(checks),'checks':checks,'first_audio_ms':measured['first_audio_ms'],'response_ms':measured['response_ms'],
            'environment':'Chromium + compiled UI + real local FastAPI/HTTP + real SSE parser and WAV playback; external AI and TTS controlled, synthetic microphone, controlled ASR/AI/TTS, no physical Windows microphone/speaker validation'}


def main():
    with tempfile.TemporaryDirectory(prefix='cronos-latency-') as folder:
        folder=Path(folder);personality=folder/'personality.md';personality.write_text('Converse em português.',encoding='utf-8')
        usage.ROOT=folder/'usage'
        mic_file=folder/'microphone.wav';mic_file.write_bytes(audio_fixture())
        settings=Settings(folder/'vault',personality,'latency-fixture','gemini','','gemini-2.5-flash','fixture','','s1','http://127.0.0.1:9','fixture',providers_file=folder/'providers.json',files_root=folder/'files',fish_format='wav')
        provider=ControlledProvider();app=create_app(settings,provider,fish_factory=ControlledFish)
        sock=socket.socket();sock.bind(('127.0.0.1',0));base=f'http://127.0.0.1:{sock.getsockname()[1]}'
        server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        try:
            for _ in range(150):
                if server.started:break
                time.sleep(.05)
            assert server.started
            with httpx.Client() as client:
                r=client.patch(base+'/panels/preferences',headers=AUTH,json={'device_auto_connect':False,'proactive_suggestions':False,'voice_volume':1,'auto_refresh':False})
                r.raise_for_status()
            print(json.dumps(asyncio.run(exercise(base,provider,mic_file)),ensure_ascii=False,indent=2))
        finally:server.should_exit=True;thread.join(10);sock.close()


if __name__=='__main__':main()
