"""Real compiled UI + HTTP server + SSE parser + audio playback; controlled AI/TTS.
No cloud credentials are used. These timings do not measure Gemini or Fish service latency.
Run after npm --prefix frontend run build: PYTHONPATH=. .venv/bin/python tools/check_conversation_latency_browser.py
"""
import asyncio
import io
import importlib
import json
import math
import re
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
from cronos.reply_stream import transcript_sink

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
    delay_asr=.25
    delay_tts=.10
    recordings=[]
    spoken=[]
    def __init__(self):self.tts=self;self.asr=self
    async def transcribe(self,**kwargs):
        self.recordings.append(kwargs['audio'])
        await asyncio.sleep(self.delay_asr)
        if self.fail_asr:raise RuntimeError("Controlled ASR failure")
        return SimpleNamespace(text="E aí, Kronos, de boa? Como é que você tá, mano?")
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def convert(self,**kwargs):
        self.spoken.append(kwargs['text'])
        await asyncio.sleep(self.delay_tts)
        return audio_fixture()


class ControlledProvider:
    def __init__(self):self.mode='normal';self.finished=threading.Event();self.cancelled=threading.Event();self.questions=[]
    async def reply(self,system,messages):
        native=messages[-1].get('audio_pcm') is not None
        question='E aí, Kronos, de boa? Como é que você tá, mano?' if native else messages[-1]['content']
        self.questions.append(question)
        if native and transcript_sink.get():await transcript_sink.get()(question)
        if 'somente o número inteiro' in question:
            return {'reply':str(sum(map(int,re.findall(r'\d+',question)))),'tool_calls':[],'topics':[]}
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
        result=parse_completed_reply(response.json()['candidates'][0]['content']['parts'][0]['text'])
        if native:result['recognized_text']=question
        return result


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
        receipt_response=await page.request.get(base+'/voice/delivery',headers=AUTH)
        receipts=(await receipt_response.json())['turns']
        receipt=next(row for row in receipts if row['turn_id']==voice_row['turn_id'])
        stages=[event['stage'] for event in receipt['events']]
        for expected in ('audio_received','recognition_requested','question_recognized','question_received','answer_requested','answer_received','voice_requested','voice_received','playback_started'):assert expected in stages,(expected,stages)
        checks.append('one receipt ID follows actual microphone bytes through recognition, AI, Fish response and playback')
        await page.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        ControlledFish.fail_asr=True
        await page.wait_for_timeout(1100)
        await page.get_by_role('button',name='Enviar fala agora',exact=True).click()
        await page.locator('.response-clock').filter(has_text='Resposta interrompida').wait_for()
        failure=(await history())[-1]
        assert failure['source']=='voice' and failure['status']=='failed' and failure['first_audio_ms'] is None
        checks.append('ASR failure is recorded even when no chat request can be sent')
        ControlledFish.fail_asr=False
        await page.get_by_role('button',name='Reenviar gravação',exact=True).click()
        await page.locator('.response-clock').filter(has_text='Voz começou em').wait_for()
        assert ControlledFish.recordings[-1]==ControlledFish.recordings[-2]
        assert provider.questions[-1]=='E aí, Kronos, de boa? Como é que você tá, mano?'
        assert 'Tudo certo, senhor.' in ''.join(ControlledFish.spoken)
        assert await page.get_by_role('button',name='Reenviar gravação',exact=True).count()==0
        checks.append('same recording is resent after ASR failure, its actual transcript reaches AI and the answer reaches TTS')
        await page.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        ControlledFish.delay_asr=13.2
        await page.wait_for_timeout(1100)
        await page.get_by_role('button',name='Enviar fala agora',exact=True).click()
        await page.locator('.response-clock').filter(has_text='Transcrevendo').wait_for()
        await page.wait_for_timeout(12200)
        assert await page.locator('.response-clock').filter(has_text='Transcrevendo').count()==1
        assert await page.get_by_role('button',name='Reenviar gravação',exact=True).count()==0
        await page.locator('.response-clock').filter(has_text='Voz começou em').wait_for()
        long_row=(await history())[-1]
        assert long_row['recognition_ms']>=13200 and long_row['first_audio_ms']>0
        checks.append('13-second recognition completes and reaches real audio playback instead of being aborted at the old 12-second deadline')
        ControlledFish.delay_asr=.25
        await page.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        ControlledFish.delay_tts=9.2
        await compose('Oi Cronos')
        await page.locator('.response-clock').filter(has_text='Preparando voz').wait_for()
        await page.wait_for_timeout(8500)
        assert await page.locator('.response-clock').filter(has_text='Preparando voz').count()==1
        await page.locator('.response-clock').filter(has_text='Voz começou em').wait_for()
        tts_row=(await history())[-1]
        assert tts_row['speech_request_ms']>=9200
        checks.append('9-second synthesis finishes with audible playback instead of being killed by the former 8-second voice deadline')
        ControlledFish.delay_tts=.10
        await page.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        await page.get_by_role('button',name='Desligar microfone',exact=True).click()
        importlib.import_module('cronos.app').VOICE_REQUEST_TIMEOUT_SECONDS=.04
        await compose('Oi Cronos, teste de voz indisponível')
        await page.locator('.response-clock').filter(has_text='Resposta interrompida').wait_for()
        await page.locator('.reference-mic.thinking, .reference-mic.generating').wait_for(state='detached')
        rows=await history()
        assert rows[-1]['status']=='failed' and rows[-1]['first_audio_ms'] is None
        await page.locator('.answer-card-deck').filter(has_text='Como foi seu dia?').wait_for()
        checks.append('stalled TTS finishes with a visible error while the complete written answer stays available')
        # Exercise the native-audio branch that previously stayed in
        # 'Transcrevendo' throughout the full conversation.
        importlib.import_module('cronos.app').VOICE_REQUEST_TIMEOUT_SECONDS=8
        native=await browser.new_page(viewport={'width':1366,'height':768})
        native.on('pageerror',lambda error:errors.append(str(error)))
        async def direct_status(route):
            response=await route.fetch();data=await response.json();data['direct_audio_chat']=True
            await route.fulfill(response=response,json=data)
        await native.route('**/status',direct_status)
        await native.goto(base+'/#cronos-session=latency-fixture')
        await native.get_by_role('button',name='Ligar microfone',exact=True).click()
        await native.locator('.reference-mic.recording').wait_for()
        await native.wait_for_timeout(1100)
        before=len(ControlledFish.recordings)
        await native.get_by_role('button',name='Enviar fala agora',exact=True).click()
        await native.locator('.response-clock').filter(has_text='Voz começou em').wait_for()
        assert not provider.finished.is_set()
        assert await native.locator('.reference-mic.transcribing').count()==0
        assert len(ControlledFish.recordings)==before
        assert await native.get_by_role('button',name='Reenviar gravação',exact=True).count()==0
        checks.append('native audio leaves transcription state on handoff, receives its recognized question and speaks before final metadata')
        await native.locator('.reference-mic.thinking, .reference-mic.speaking, .reference-mic.generating').wait_for(state='detached')
        provider.mode='fail'
        await native.wait_for_timeout(1100)
        await native.get_by_role('button',name='Enviar fala agora',exact=True).click()
        await native.locator('.response-clock').filter(has_text='Resposta interrompida').wait_for()
        await native.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
        await native.locator('.phrase-card').click()
        assert await native.locator('#chat-input').input_value()=='E aí, Kronos, de boa? Como é que você tá, mano?'
        assert len(ControlledFish.recordings)==before
        checks.append('native answer failure preserves the actual recognized question for retry, without redundant ASR or the voice placeholder')

        provider.mode='normal'
        await native.keyboard.press('Escape')
        await native.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
        await native.get_by_role('button',name='TESTAR IA E VOZ',exact=True).click()
        await native.locator('audio[controls]').wait_for()
        await native.locator('audio[controls]').evaluate('(audio)=>audio.play()')
        await native.wait_for_timeout(200)
        check_response=await native.request.get(base+'/voice/delivery',headers=AUTH)
        check=(await check_response.json())['turns'][0]
        assert any(event['stage']=='voice_received' and event.get('bytes',0)>0 for event in check['events'])
        assert any(event['stage']=='playback_started' and event.get('response_ms',0)>0 for event in check['events'])
        assert await native.get_by_role('button',name='COPIAR DIAGNÓSTICO',exact=True).is_enabled()
        checks.append('diagnostic button submits a fresh arithmetic question and plays the computed answer using the same backend and TTS path')
        await native.evaluate("()=>Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true})")
        await native.get_by_role('button',name='COPIAR DIAGNÓSTICO',exact=True).click()
        report=await native.get_by_role('textbox',name='Diagnóstico de entrega').input_value()
        assert 'audio_base64' not in report and 'api_key' not in report
        assert json.loads(report)['turns']
        checks.append('diagnostic stays copyable when the embedded browser does not provide clipboard permission')
        assert not errors,errors
        await native.close();await page.close();await browser.close()
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
