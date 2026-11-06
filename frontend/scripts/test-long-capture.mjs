import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source=readFileSync(new URL('../src/audio/capture.worklet.js',import.meta.url),'utf8')
  .replace(/^import .*;\s*$/m,'');
let Worklet;
let emitted=[];
class AudioWorkletProcessor {
  constructor(){this.port={postMessage(message){if(message.samples)emitted.push(message.samples);},onmessage:null};}
}
runInNewContext(source,{AudioWorkletProcessor,sampleRate:16000,
  createSpeechDetector:async()=>({process:()=>true,mode(){}}),
  registerProcessor(name,constructor){assert.equal(name,'cronos-capture');Worklet=constructor;}});

function feed(worklet,seconds,level=.1){
  const frame=new Float32Array(128).fill(level);
  for(let i=0;i<seconds*16000/128;i++)worklet.process([[frame]]);
}
emitted=[];
const manual=new Worklet();manual.vad={process:()=>true,mode(){}};
feed(manual,75);
assert.equal(emitted.length,0,'75 seconds must remain one utterance');
manual.port.onmessage({data:{flush:true}});
assert.equal(emitted.length,1);
assert.ok(emitted[0].length>=74*16000,'manual send must not keep only the final 30 seconds');

emitted=[];
const automatic=new Worklet();automatic.vad={process:()=>true,mode(){}};
feed(automatic,180);
assert.equal(emitted.length,1,'continuous speech must reach the three-minute boundary');
assert.equal(emitted[0].length,180*16000,'the emitted WAV must fit the backend limit');
emitted=[];
const paused=new Worklet();paused.vad={process:()=>true,mode(){}};
feed(paused,10);feed(paused,2,0);
assert.equal(emitted.length,0,'a natural two-second pause must not cut a long question');
feed(paused,1,0);
assert.equal(emitted.length,1,'prolonged silence should still end the question');
console.log('Long capture: manual 75 s and automatic 180 s passed.');
