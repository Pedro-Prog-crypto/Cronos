import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createSpeechDetector} from '../src/audio/speechDetector.js';
const binary=fs.readFileSync(new URL('../node_modules/@echogarden/fvad-wasm/fvad.wasm',import.meta.url));
const bytes=fs.readFileSync(new URL('./fixtures/speech-16k.pcm',import.meta.url));
const pcm=new Int16Array(bytes.buffer,bytes.byteOffset,bytes.length/2);
let Capture;
class Processor {constructor(){this.events=[];this.port={postMessage:event=>this.events.push(event)};}}
const code=fs.readFileSync(new URL('../src/audio/capture.worklet.js',import.meta.url),'utf8').replace(/^import .*;$/m,'');
vm.runInNewContext(code,{AudioWorkletProcessor:Processor,sampleRate:16000,createSpeechDetector,registerProcessor:(_,klass)=>{Capture=klass;}});
async function capture(){const n=new Capture();n.port.onmessage({data:{vadBinary:binary}});for(let i=0;i<100&&!n.events.some(e=>e.vadReady);i++)await new Promise(r=>setTimeout(r,5));assert.ok(n.events.some(e=>e.vadReady),'actual WebRTC WASM must initialize');return n;}
let seed=17;
function feed(node,seconds,kind='silence',gain=1){for(let frame=0;frame<seconds*16000;frame+=128){const data=new Float32Array(128);for(let i=0;i<128;i++){
 if(kind==='speech')data[i]=gain*pcm[(frame+i)%pcm.length]/32768;
 if(kind==='noise'){seed=(Math.imul(seed,1664525)+1013904223)|0;data[i]=gain*(seed/2147483648);}
 if(kind==='tone')data[i]=gain*Math.sin((frame+i)*Math.PI/8);
}node.process([[data]]);}}
const quiet=await capture();feed(quiet,.2);feed(quiet,.8,'speech',.04);feed(quiet,.35);feed(quiet,.8,'speech',.04);
assert.equal(quiet.events.filter(e=>e.samples).length,0,'a normal short pause must not split the question');
feed(quiet,1.1);assert.equal(quiet.events.filter(e=>e.samples).length,1,'question must close after a short speech pause');
const fan=await capture();feed(fan,4,'noise',.004);assert.equal(fan.events.filter(e=>e.samples).length,0,'steady fan noise is not a spoken command');
const mixed=await capture();feed(mixed,.2);feed(mixed,1.2,'speech',.25);feed(mixed,3,'noise',.004);
const segment=mixed.events.find(e=>e.samples);assert.ok(segment,'background noise must not hold the spoken question open');assert.ok(segment.samples.length<3*16000,'noise must not add a long tail to ASR');
const click=await capture();feed(click,.2);feed(click,.04,'tone',.1);feed(click,1.1);assert.equal(click.events.filter(e=>e.samples).length,0,'short click must not become a question');
const aborted=await capture();feed(aborted,.2);feed(aborted,.5,'speech',.25);aborted.port.onmessage({data:{blocked:true}});feed(aborted,1.1);assert.equal(aborted.events.filter(e=>e.samples).length,0);
console.log('PASS: actual WebRTC VAD detects speech, retains short pauses, rejects steady fan noise and clicks, closes speech despite background noise, and honors capture cancellation.');
const distant=await capture();feed(distant,.2);feed(distant,.9,'speech',.025);feed(distant,1.1);assert.ok(distant.events.find(e=>e.samples),'soft speech must remain detectable');
const loud=await capture();feed(loud,.2);feed(loud,.8,'speech',2);feed(loud,1.1);const loudClip=loud.events.find(e=>e.samples);assert.ok(loudClip);
let max=0;for(const sample of loudClip.samples)max=Math.max(max,Math.abs(sample));assert.ok(max<=31130,'capture gain must not hard-clip loud speech');
console.log('PASS: soft and loud real speech fixtures work without clipping; no speaker identity is inferred.');
const fading=await capture();feed(fading,.2);feed(fading,.8,'speech',.3);feed(fading,1.0,'speech',.04);
assert.equal(fading.events.filter(e=>e.samples).length,0,'lowering the voice must not cut the rest of the question');feed(fading,1.1);assert.ok(fading.events.find(e=>e.samples));
const trimmed=await capture();feed(trimmed,3,'speech',.25);trimmed.port.onmessage({data:{arm:true}});assert.ok(trimmed.frames<=16000*1.5+128,'activation must discard old ambient speech, retaining only a bounded wake pre-roll');
console.log('PASS: quieter phrase endings are retained and wake activation discards old ambient recordings.');
const waiting=await capture();waiting.port.onmessage({data:{waiting:true}});feed(waiting,8,'speech',.25);
assert.equal(waiting.events.filter(e=>e.samples).length,0,'idle voice must never be emitted as a cloud question');assert.ok(waiting.pre.reduce((n,c)=>n+c.length,0)<=16000*1.5+128);
waiting.port.onmessage({data:{keyword:true}});const preroll=waiting.events.find(e=>e.keywordPre)?.keywordPre;assert.ok(preroll&&preroll.length<=16000+128,'keyword startup reuses bounded local pre-roll');
waiting.port.onmessage({data:{arm:true}});feed(waiting,1.4);assert.equal(waiting.events.filter(e=>e.samples).length,1,'a locally recognized wake word opens one finite question');
console.log('PASS: name-only idle capture keeps a bounded ring, emits no question, and reuses pre-roll for keyword startup.');
