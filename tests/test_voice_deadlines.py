import asyncio
import importlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos.reply_stream import deliver_intro
from test_backend import settings,AUTH

app_module=importlib.import_module('cronos.app')


def test_silent_conversation_is_cancelled_and_next_question_can_run(settings,monkeypatch):
    monkeypatch.setattr(app_module,'CONVERSATION_FIRST_REPLY_TIMEOUT_SECONDS',.025)
    cancelled=[]
    class Provider:
        async def reply(self,system,messages):
            if messages[-1]['content']=='Oi':return {'reply':'Olá, senhor.','topics':[],'tool_calls':[]}
            try:await asyncio.sleep(60)
            finally:cancelled.append(True)
    with TestClient(create_app(settings,Provider())) as client:
        response=client.post('/chat/stream',headers=AUTH,json={'message':'Pergunta que ficou presa'})
        event=json.loads(response.text)
        assert event['type']=='error' and event['status']==504 and 'preservada' in event['detail']['message']
        next_response=client.post('/chat/stream',headers=AUTH,json={'message':'Oi'})
        assert json.loads(next_response.text.splitlines()[-1])['type']=='result'
    assert cancelled==[True]


def test_initial_response_deadline_does_not_truncate_active_explanation(settings,monkeypatch):
    monkeypatch.setattr(app_module,'CONVERSATION_FIRST_REPLY_TIMEOUT_SECONDS',.02)
    class Provider:
        async def reply(self,*args):
            await deliver_intro('A explicação começou. ')
            await asyncio.sleep(.06)
            return {'reply':'A explicação começou. E chegou ao final.','topics':[],'tool_calls':[]}
    with TestClient(create_app(settings,Provider())) as client:
        events=[json.loads(line) for line in client.post('/chat/stream',headers=AUTH,json={'message':'Explique algo'}).text.splitlines()]
    assert [event['type'] for event in events]==['intro','reply','result']


def test_fish_sdk_retry_wait_is_bounded_for_voice_and_transcription(settings,monkeypatch):
    monkeypatch.setattr(app_module,'VOICE_REQUEST_TIMEOUT_SECONDS',.025)
    monkeypatch.setattr(app_module,'TRANSCRIPTION_TIMEOUT_SECONDS',.025)
    cancelled=[]
    class Fish:
        def __init__(self):self.tts=self;self.asr=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def stalled(self,**kwargs):
            try:await asyncio.sleep(60)
            finally:cancelled.append(True)
        convert=stalled
        transcribe=stalled
    with TestClient(create_app(replace(settings,fish_key='fixture'),fish_factory=Fish)) as client:
        r=client.post('/voice/speech',headers=AUTH,json={'text':'Olá'})
        assert r.status_code==504
        r=client.post('/voice/transcribe',headers=AUTH,content=b'controlled-audio')
        assert r.status_code==504
    assert len(cancelled)==2


def test_network_deadline_covers_body_and_cleans_parent_listener():
    source=Path('frontend/src/audio/requestDeadline.ts').resolve().as_uri()
    script='''import assert from 'node:assert/strict';
    import {withRequestDeadline} from SOURCE;
    const parent=new AbortController();let aborted=false;
    await assert.rejects(withRequestDeadline(parent.signal,20,async signal=>{
      // Simulate received headers followed by an indefinitely stalled body.
      await Promise.resolve();
      return await new Promise((resolve,reject)=>signal.addEventListener('abort',()=>{aborted=true;reject(new Error('aborted body'));},{once:true}));
    }),/não respondeu a tempo/);
    assert(aborted);
    assert.equal(await withRequestDeadline(parent.signal,30,async signal=>'ready'), 'ready');
    const originalTimeout=globalThis.setTimeout;
    globalThis.setTimeout=(fn,ms,...args)=>originalTimeout(fn,ms===8000?20:ms,...args);
    const {playPCM}=await import(PCM_SOURCE);
    let streamCancelled=false;
    const stream=new ReadableStream({cancel(){streamCancelled=true;}});
    const context={currentTime:0,createAnalyser:()=>({connect(){},disconnect(){}}),createGain:()=>({gain:{},connect(){},disconnect(){}}),destination:{}};
    await assert.rejects(playPCM(new Response(stream,{headers:{'X-PCM-Sample-Rate':'24000'}}),context,parent.signal,{volume:()=>1,onNodes(){},rate:()=>1,onStart(){}}),/parou de enviar/);
    assert(streamCancelled);
    globalThis.setTimeout=originalTimeout;

    const cancelled=new AbortController();cancelled.abort();
    await assert.rejects(withRequestDeadline(cancelled.signal,50,async signal=>{signal.throwIfAborted();}),/abort/i);
    '''.replace('PCM_SOURCE',json.dumps(Path('frontend/src/audio/playPCM.ts').resolve().as_uri())).replace('SOURCE',json.dumps(source))
    r=subprocess.run(['node','--experimental-strip-types','--input-type=module','-e',script],capture_output=True,text=True,timeout=5)
    assert r.returncode==0,r.stderr


def test_nonstreaming_chat_also_releases_a_stalled_request(settings,monkeypatch):
    monkeypatch.setattr(app_module,'CONVERSATION_FIRST_REPLY_TIMEOUT_SECONDS',.025)
    cancelled=[]
    class Provider:
        async def reply(self,*args):
            try:await asyncio.sleep(60)
            finally:cancelled.append(True)
    with TestClient(create_app(settings,Provider())) as client:
        response=client.post('/chat',headers=AUTH,json={'message':'Oi'})
        assert response.status_code==504
    assert cancelled==[True]
