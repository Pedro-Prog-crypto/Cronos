import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
let Capture;
class Processor {constructor(){this.events=[];this.port={postMessage:event=>this.events.push(event)};}}
vm.runInNewContext(fs.readFileSync(new URL('../src/audio/capture.worklet.js',import.meta.url),'utf8'),{AudioWorkletProcessor:Processor,sampleRate:16000,registerProcessor:(_,klass)=>{Capture=klass;}});
function feed(node,seconds,amplitude){for(let frame=0;frame<seconds*16000;frame+=128){const data=new Float32Array(128);for(let i=0;i<128;i++)data[i]=amplitude*Math.sin((frame+i)*Math.PI/8);node.process([[data]]);}}
const quiet=new Capture();feed(quiet,.2,0);feed(quiet,.7,.012);feed(quiet,.35,0);feed(quiet,.7,.012);
assert.equal(quiet.events.filter(e=>e.samples).length,0,'a normal short pause must not split the question');
feed(quiet,.76,0);assert.equal(quiet.events.filter(e=>e.samples).length,1,'soft speech must finish within about 750ms of silence');
const noise=new Capture();feed(noise,.2,.004);feed(noise,2,.004);assert.equal(noise.events.filter(e=>e.samples).length,0);
const click=new Capture();feed(click,.2,0);feed(click,.04,.1);feed(click,.8,0);assert.equal(click.events.filter(e=>e.samples).length,0);
const aborted=new Capture();feed(aborted,.2,0);feed(aborted,.5,.1);aborted.port.onmessage({data:{blocked:true}});feed(aborted,1,0);assert.equal(aborted.events.filter(e=>e.samples).length,0);
console.log('PASS: soft speech, brief pauses, bounded endpoint delay, ambient noise, short clicks and capture interruption.');
const distant=new Capture();feed(distant,.2,0);feed(distant,.8,.003);feed(distant,.76,0);
const distantClip=distant.events.find(e=>e.samples);assert.ok(distantClip,'faint speech above the calibrated floor must be detected');
assert.ok(Math.max(...distantClip.samples)>140,'capture gain must amplify the faint PCM signal');
const insensitive=new Capture();insensitive.port.onmessage({data:{blocked:false,sensitivity:0,gain:1}});feed(insensitive,.2,0);feed(insensitive,.8,.003);feed(insensitive,.76,0);assert.equal(insensitive.events.filter(e=>e.samples).length,0,'sensitivity control must change detection');
console.log('PASS: quieter speech, PCM gain and adjustable sensitivity.');
