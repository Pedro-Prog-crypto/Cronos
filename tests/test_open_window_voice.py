import json
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from cronos.app import create_app
from test_backend import AUTH,settings


def node(script):
    result=subprocess.run(['node','--experimental-strip-types','--input-type=module','-e',script],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


def test_optional_output_device_never_blocks_default_voice():
    source=json.dumps(Path('frontend/src/audio/outputDevice.ts').resolve().as_uri())
    node("""
    import assert from 'node:assert/strict';
    import {routeVoiceOutput} from SOURCE;
    const original=setTimeout;globalThis.setTimeout=(fn,ms,...args)=>original(fn,ms===1500?10:ms,...args);
    let calls=0,warnings=[];
    const context={setSinkId:async()=>{calls++;throw Error('Unsupported WebView API');}};
    await routeVoiceOutput(context,undefined,message=>warnings.push(message));
    assert.equal(calls,0);assert.equal(warnings.length,0);
    Object.defineProperty(globalThis,'navigator',{value:{mediaDevices:{enumerateDevices:async()=>[]}},configurable:true});
    await routeVoiceOutput(context,'Old Bluetooth speaker',m=>warnings.push(m));
    assert.equal(calls,0);assert.equal(warnings.length,1);
    navigator.mediaDevices.enumerateDevices=()=>new Promise(()=>{});
    await routeVoiceOutput(context,'Old Bluetooth speaker',m=>warnings.push(m));
    assert.equal(warnings.length,2);
    navigator.mediaDevices.enumerateDevices=async()=>[{kind:'audiooutput',label:'Speaker',deviceId:'chosen'}];
    let routed='';await routeVoiceOutput({setSinkId:async id=>{routed=id;}},'Speaker',()=>assert.fail());assert.equal(routed,'chosen');
    await assert.rejects(routeVoiceOutput({sinkId:'stale',setSinkId:()=>new Promise(()=>{})},undefined,()=>assert.fail()),/não respondeu/);
    """.replace('SOURCE',source))


def test_device_voice_reads_the_answer_and_can_be_cancelled():
    source=json.dumps(Path('frontend/src/audio/deviceSpeech.ts').resolve().as_uri())
    node("""
    import assert from 'node:assert/strict';
    import {findDeviceVoice,speakDeviceText} from SOURCE;
    const original=setTimeout;globalThis.setTimeout=(fn,ms,...args)=>original(fn,ms>=1200?10:ms,...args);
    const voice={localService:true,lang:'pt-BR',name:'Português Windows'};
    const events=new EventTarget();let voices=[{localService:false,lang:'pt-BR'},voice];let spoken=[],starts=[];
    globalThis.speechSynthesis={getVoices:()=>voices,addEventListener:events.addEventListener.bind(events),removeEventListener:events.removeEventListener.bind(events),cancel(){},resume(){},speak(u){spoken.push(u.text);queueMicrotask(()=>{u.onstart?.();u.onend?.();});}};
    globalThis.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
    const signal=new AbortController();assert.equal(await findDeviceVoice(signal.signal),voice);
    const actual='A resposta da integração precisa chegar inteira. '.repeat(12);
    await speakDeviceText(actual,voice,signal.signal,{volume:1,rate:1,onStart:p=>starts.push(p)});
    assert.equal(spoken.join(''),actual);assert.deepEqual(starts,spoken);assert(spoken.every(p=>p.length<=160));
    let cancelled=0;const abort=new AbortController();speechSynthesis.cancel=()=>cancelled++;
    speechSynthesis.speak=u=>{u.onstart?.();queueMicrotask(()=>abort.abort());};
    await speakDeviceText(actual,voice,abort.signal,{volume:1,rate:1,onStart(){}});assert(cancelled>0);
    speechSynthesis.speak=()=>{};
    await assert.rejects(speakDeviceText('Teste',voice,signal.signal,{volume:1,rate:1,onStart:()=>assert.fail()}),/não iniciou/);
    speechSynthesis.speak=u=>u.onstart?.();
    await assert.rejects(speakDeviceText('Teste',voice,signal.signal,{volume:1,rate:1,onStart(){}}),/parou de responder/);
    voices=[];assert.equal(await findDeviceVoice(signal.signal),null);
    const pending=findDeviceVoice(signal.signal);voices=[voice];events.dispatchEvent(new Event('voiceschanged'));assert.equal(await pending,voice);
    voices=[];const stop=new AbortController();const waiting=findDeviceVoice(stop.signal);stop.abort();assert.equal(await waiting,null);
    speechSynthesis.getVoices=()=>{throw Error('Speech service blocked');};assert.equal(await findDeviceVoice(signal.signal),null);
    """.replace('SOURCE',source))


def test_local_speech_is_identified_as_device_not_cloud(settings):
    turn=str(uuid4())
    with TestClient(create_app(settings)) as client:
        response=client.post('/panels/latency',headers=AUTH,json={'turn_id':turn,'source':'voice','voice_source':'device','chat_ms':100,'first_audio_ms':250,'status':'responding'})
        assert response.status_code==200
        rows=client.get('/voice/delivery',headers=AUTH).json()['turns']
    receipt=next(row for row in rows if row['turn_id']==turn)
    playback=next(event for event in receipt['events'] if event['stage']=='playback_started')
    assert playback['provider']=='device'


def test_command_routing_does_not_open_windows_for_descriptions():
    result=subprocess.run(['node','--experimental-strip-types','frontend/scripts/check-open-window-commands.mjs'],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['routing_checks_passed']==10000


def test_pcm_device_stall_releases_both_backpressure_and_final_playback():
    source=json.dumps(Path('frontend/src/audio/playPCM.ts').resolve().as_uri())
    node("""
    import assert from 'node:assert/strict';
    import {playPCM} from SOURCE;
    const original=setTimeout;globalThis.setTimeout=(fn,ms,...args)=>original(fn,ms===40?1:ms>=10000?20:ms,...args);
    let now=0;Object.defineProperty(performance,'now',{value:()=>now+=600,configurable:true});
    const context={currentTime:0,destination:{},createAnalyser:()=>({connect(){},disconnect(){}}),createGain:()=>({gain:{},connect(){},disconnect(){}}),
     createBuffer:(_,samples,rate)=>({duration:samples/rate,getChannelData:()=>new Float32Array(samples)}),
     createBufferSource:()=>({playbackRate:{},connect(){},disconnect(){},start(){},stop(){}})};
    const response=seconds=>new Response(new Uint8Array(Math.floor(seconds*24000)*2),{headers:{'X-PCM-Sample-Rate':'24000'}});
    const options={volume:()=>1,rate:()=>1,onNodes(){},onStart(){}};
    await assert.rejects(playPCM(response(3),context,new AbortController().signal,options),/dispositivo parou/);
    await assert.rejects(playPCM(response(.01),context,new AbortController().signal,options),/não concluiu/);
    """.replace('SOURCE',source))
