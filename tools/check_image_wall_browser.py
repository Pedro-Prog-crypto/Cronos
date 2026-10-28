"""Exercise the actual React image wall in Chromium, with controlled media servers.

Run: .venv/bin/python tools/check_image_wall_browser.py
Requires frontend/node_modules, Playwright, Pillow and Chromium. Network responses
are fixtures; this verifies rendering/lifecycle, not external provider availability.
"""
import asyncio
import io
import json
import random
import shutil
import socket
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


def png(seed, portrait=False):
    rng = random.Random(seed)
    image = Image.new('RGB', (9, 8))
    image.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(72)])
    output = io.BytesIO()
    image.resize((240, 360) if portrait else (360, 240)).save(output, format='PNG')
    return output.getvalue()


async def exercise(base, harness):
    passed=[]
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
        page = await browser.new_page(viewport={'width':1366, 'height':768})
        errors=[]; searches=[]; mode={'value':'normal'}
        page.on('pageerror', lambda error: errors.append(str(error)))
        await page.add_init_script('''window.liveBlobs=new Set();
          const make=URL.createObjectURL.bind(URL), revoke=URL.revokeObjectURL.bind(URL);
          URL.createObjectURL=value=>{const url=make(value);window.liveBlobs.add(url);return url};
          URL.revokeObjectURL=url=>{window.liveBlobs.delete(url);revoke(url)};''')
        async def search(route):
            params=parse_qs(urlsplit(route.request.url).query)
            query=params['query'][0]; searches.append((query, params.get('attempt',['0'])[0]))
            if query=='SlowTopic': await asyncio.sleep(.7)
            if query=='Plato': await asyncio.sleep(.2)
            records=[] if mode['value']=='empty' else [
                {'title':f'{query} picture {index}', 'url':f'https://images.example/th?id={query}-{index}&w=360',
                 'proxy_url':f'/studies/media/{query}-{index}', 'source_url':'https://museum.example/source',
                 'license':'CC0', 'artist':'Fixture'} for index in range(18)]
            await route.fulfill(json={'images':records,'message':'Nenhuma imagem nesta busca.'})
        async def media(route):
            query,index=urlsplit(route.request.url).path.rsplit('/',1)[-1].rsplit('-',1)
            index=int(index)
            if mode['value']=='broken' or index<2:
                await route.fulfill(status=502,json={'detail':'fixture source offline'});return
            await asyncio.sleep(.015)
            # Two different addresses returning exactly the same pixels must collapse.
            await route.fulfill(content_type='image/png',body=png((query, 3 if index==4 else index).__repr__(), portrait=query=='PortraitTopic'))
        await page.route('**/studies/images?*', search)
        await page.route('**/studies/media/*', media)
        await page.route('**/connection',lambda route:route.fulfill(status=401,json={}))
        await page.goto(f'{base}/ui/{harness}/index.html')
        await page.wait_for_function('typeof window.renderWall==="function"')
        def panel(title='Socrates', **extra):
            return dict(id='review',title=title,reply=f'{title} foi um pensador com uma longa história e ideias que influenciaram sua época.',
                        slot=0,locked=False,minimized=False,createdAt=1,**extra)
        async def render(value, speaking=False):
            await page.evaluate('value=>window.renderWall(value.panel,value.speaking)',{'panel':value,'speaking':speaking})
        photos=page.locator('.study-film-lane-set:not([aria-hidden="true"]) img')
        await render(panel())
        await page.wait_for_function('document.querySelectorAll(".study-film-lane-set:not([aria-hidden=true]) img").length===12')
        assert await photos.count()==12
        assert await photos.evaluate_all('(items)=>items.every(img=>img.complete&&img.naturalWidth===360)')
        assert await photos.evaluate_all('(items)=>new Set(items.map(img=>img.src)).size')==12
        passed.append('12 decoded unique images despite failures and duplicate pixels')
        before=await page.locator('.study-film-lane-track').first.evaluate('(el)=>getComputedStyle(el).transform')
        await page.wait_for_timeout(350)
        after=await page.locator('.study-film-lane-track').first.evaluate('(el)=>getComputedStyle(el).transform')
        assert before!=after and after!='none'
        bounds=await page.locator('.study-film-wall').bounding_box()
        assert bounds['width']==1366 and bounds['height']==768
        assert await page.locator('.study-film-lane').count()==3
        assert await page.locator('.study-cinema').inner_text()==''
        passed.append('fullscreen wall moves left, three rows, no transcript')
        count=len(searches)
        value=panel(); value['reply']+=' Uma nova frase chegou pela resposta em andamento.'
        await render(value); await page.wait_for_timeout(200)
        assert len(searches)==count
        passed.append('streaming text does not restart identical media searches')
        value=panel('Filósofos'); value['reply']='Sócrates investigou a ética e influenciou profundamente a filosofia. Platão fundou a Academia e escreveu diálogos sobre conhecimento.'
        value['spokenChunk']='Platão fundou a Academia e escreveu diálogos sobre conhecimento.'
        await render(value)
        await page.wait_for_function('document.querySelector(".study-film-tile img")?.alt.startsWith("Plato")')
        assert ('Plato','0') in searches
        passed.append('spoken Plato changes the subject instead of retaining Socrates')
        await render(panel('SlowTopic')); await page.wait_for_timeout(80)
        await render(panel('NewTopic'))
        await page.wait_for_function('document.querySelector(".study-film-tile img")?.alt.startsWith("NewTopic")')
        await page.wait_for_timeout(800)
        assert (await photos.first.get_attribute('alt')).startswith('NewTopic')
        passed.append('late cancelled search cannot overwrite a newer topic')
        mode['value']='empty'; await render(panel('EmptyTopic'))
        await page.get_by_role('button',name='TENTAR OUTRAS IMAGENS').wait_for()
        mode['value']='normal'; await page.get_by_role('button',name='TENTAR OUTRAS IMAGENS').click()
        await page.wait_for_function('document.querySelectorAll(".study-film-lane-set:not([aria-hidden=true]) img").length===12')
        assert ('EmptyTopic','1') in searches
        passed.append('empty search is not permanently cached; retry recovers')
        mode['value']='broken'; await render(panel('BrokenTopic'))
        await page.get_by_role('button',name='TENTAR OUTRAS IMAGENS').wait_for()
        mode['value']='normal'; await page.get_by_role('button',name='TENTAR OUTRAS IMAGENS').click()
        await page.wait_for_function('document.querySelectorAll(".study-film-lane-set:not([aria-hidden=true]) img").length===12')
        passed.append('all proxy failures report failure and allow working retry')
        await page.clock.install()
        await render(panel('RefreshTopic'),speaking=True)
        await page.wait_for_function('document.querySelector(".study-film-tile img")?.alt.startsWith("RefreshTopic")')
        count=len(searches)
        await page.clock.fast_forward(30001)
        await page.wait_for_function('document.querySelectorAll(".study-film-lane-set:not([aria-hidden=true]) img").length===12')
        await page.wait_for_timeout(100)
        assert len(searches)>count
        passed.append('new page of images is requested while narration continues')
        await render(panel('PortraitTopic'))
        await page.wait_for_function('document.querySelectorAll(".study-film-lane-set:not([aria-hidden=true]) img").length===12 && document.querySelector(".study-film-tile img")?.alt.startsWith("PortraitTopic")')
        assert await page.locator('.study-film-lane').count()==2
        assert await photos.evaluate_all('(items)=>items.every(img=>img.naturalWidth===240&&getComputedStyle(img).objectFit==="contain")')
        passed.append('portrait photographs adapt to two rows without forced cropping')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_function('document.querySelectorAll(".study-film-lane").length===4')
        close=await page.get_by_role('button',name='Fechar apresentação').bounding_box()
        assert 0<=close['x'] and close['x']+close['width']<=390
        assert await photos.count()==12
        passed.append('small viewport preserves all photographs and a reachable close button')
        await page.screenshot(path='/tmp/cronos-review-wall.png')
        await page.get_by_role('button',name='Fechar apresentação').click()
        assert await page.locator('.study-cinema').count()==0
        await page.wait_for_timeout(100)
        assert await page.evaluate('window.liveBlobs.size')==0
        assert not errors,errors
        passed.append('closing releases every object URL with no browser errors')
        # Exercise the parent App and real audio hook, not only the standalone panel.
        full=await browser.new_page(viewport={'width':1366,'height':768})
        full_errors=[]
        full.on('pageerror',lambda error:full_errors.append(str(error)))
        preferences={'device_auto_connect':False,'proactive_suggestions':False,'voice_volume':1,'voice_speed':1,'voice_pitch':.5,'auto_refresh':False,'response_style':'detailed'}
        async def api_fixture(route):
            path=urlsplit(route.request.url).path
            payload={}
            if path=='/status':payload={'privacy_mode':'online','fish_speech_configured':True,'fish_configured':True,'fish_pcm_streaming':False}
            elif path=='/panels':payload={'preferences':preferences}
            elif path=='/memory/graph':payload={'nodes':[],'edges':[],'total':0,'next_offset':None}
            elif path=='/monitor':payload={'cursor':0,'events':[],'alerts':[]}
            elif path=='/wake/status':payload={'windows_available':False,'state':'stopped','settings':{'activation_phrase':'cronos','pause_phrase':'pausar cronos','resume_phrase':'retomar cronos','start_with_windows':False}}
            await route.fulfill(json=payload)
        for endpoint in ('status','panels','memory/**','monitor?*','wake/status','conversation/metrics','voice/metrics'):
            await full.route('**/'+endpoint,api_fixture)
        await full.route('**/studies/images?*',search)
        await full.route('**/studies/media/*',media)
        async def chat(route):
            result={'session_id':'00000000-0000-0000-0000-000000000001',
                'reply':'Sócrates foi um filósofo ateniense que investigou a ética e o conhecimento por meio de perguntas. Sua influência permanece na filosofia.',
                'topics':[],'notes':[],'tool_results':[],'warnings':[]}
            await route.fulfill(content_type='application/x-ndjson',body=json.dumps({'type':'result','result':result})+'\n')
        await full.route('**/chat/stream',chat)
        audio=io.BytesIO()
        with wave.open(audio,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b'\0\0'*16000*45)
        await full.route('**/voice/speech',lambda route:route.fulfill(content_type='audio/wav',body=audio.getvalue()))
        await full.goto(base+'/ui/#cronos-session=test-token')
        await full.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click()
        await full.get_by_role('button',name='Fale com o Cronos ou clique para escrever.').click()
        await full.clock.install()
        await full.locator('#chat-input').fill('Explique detalhadamente quem foi Sócrates')
        await full.get_by_role('button',name='Enviar mensagem',exact=True).click()
        await full.wait_for_function('document.querySelector(".reference-mic.speaking")!==null')
        await full.wait_for_function('document.querySelectorAll(".study-film-lane-set:not([aria-hidden=true]) img").length===12')
        count=len(searches)
        await full.clock.fast_forward(30001)
        for _ in range(30):
            if len(searches)>count:break
            await asyncio.sleep(.05)
        assert len(searches)>count, 'Main App did not connect voice state to periodic image renewal'
        assert not full_errors, full_errors
        await full.close()
        passed.append('main App sends a study question, plays real WAV and renews images during speech')
        await browser.close()
    return passed


def main():
    with tempfile.TemporaryDirectory(prefix='review-wall-',dir=ROOT/'frontend') as folder, tempfile.TemporaryFile() as log:
        folder=Path(folder)
        (folder/'index.html').write_text('<html><body style="margin:0"><div id="root"></div><script type="module" src="./main.tsx"></script></body></html>')
        (folder/'main.tsx').write_text('''import React from 'react';import{createRoot}from'react-dom/client';
          import{StudyExplanationPanel}from'../src/components/StudyExplanationPanel';import{connect}from'../src/api';
          connect('test-token');const root=createRoot(document.getElementById('root')!);
          window.renderWall=(panel,speaking=false)=>root.render(<StudyExplanationPanel panels={panel?[panel]:[]} activeId={panel?.id} speaking={speaking} onClose={()=>window.renderWall(null)}/>);''')
        with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--port',str(port),'--strictPort'],cwd=ROOT/'frontend',stdout=log,stderr=log)
        try:
            for _ in range(100):
                with socket.socket() as sock:
                    if sock.connect_ex(('127.0.0.1',port))==0:break
                if server.poll() is not None:raise RuntimeError('Vite failed to start')
                time.sleep(.1)
            passed=asyncio.run(exercise(f'http://127.0.0.1:{port}',folder.name))
            print(json.dumps({'passed':len(passed),'scenarios':passed,'external_media':'mocked','browser':'Chromium'},ensure_ascii=False,indent=2))
        finally:
            server.terminate();server.wait(timeout=10)

if __name__=='__main__': main()
