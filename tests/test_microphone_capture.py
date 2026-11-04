"""Exercise the actual AudioWorklet with a synthetic phrase and prior silence."""
import subprocess
from pathlib import Path


def test_manual_send_contains_the_phrase_instead_of_the_last_minute_of_room_noise():
    script = r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
let source=fs.readFileSync('frontend/src/audio/capture.worklet.js','utf8');
source=source.replace("import {createSpeechDetector} from './speechDetector.js';",'');
let Processor;
const messages=[];
const context={sampleRate:16000,Int16Array,Float32Array,Math,Promise,
  AudioWorkletProcessor:class {constructor(){this.port={postMessage:(value)=>messages.push(value)};}},
  registerProcessor:(_name,value)=>{Processor=value;}};
vm.runInNewContext(source,context);
const worklet=new Processor();
    // Reproduce a detector that never classifies this quiet voice as speech.
    worklet.vad={process:()=>false,mode:()=>{}};
for(let index=0;index<1250;index++)worklet.process([[new Float32Array(128)]]);
    assert.equal(messages.some(value=>value.manualReady),true);
for(let index=0;index<50;index++)worklet.process([[new Float32Array(128).fill(.1)]]);
    assert.equal(messages.some(value=>value.samples&&!value.manual),false);
worklet.port.onmessage({data:{flush:true}});
const recording=messages.find(value=>value.manual);
assert.ok(recording);
assert.ok(recording.samples.length>4000);
    assert.ok(recording.samples.length<16000*3,'the old 10 seconds of silence must be excluded');
assert.ok(recording.samples.some(value=>value!==0));
'''
    result=subprocess.run(['node','--input-type=module','-e',script],cwd=Path(__file__).resolve().parents[1],
                          capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


def test_worklet_keeps_speech_across_a_natural_pause_then_submits_once():
    script = r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
let source=fs.readFileSync('frontend/src/audio/capture.worklet.js','utf8');
source=source.replace("import {createSpeechDetector} from './speechDetector.js';",'');
let Processor;
const messages=[];
const context={sampleRate:16000,Int16Array,Float32Array,Math,Promise,
  AudioWorkletProcessor:class {constructor(){this.port={postMessage:value=>messages.push(value)};}},
  registerProcessor:(_name,value)=>{Processor=value;}};
vm.runInNewContext(source,context);
const worklet=new Processor();
worklet.vad={process:frame=>frame.some(value=>value!==0),mode:()=>{}};
const run=(milliseconds,value)=>{for(let i=0;i<Math.ceil(milliseconds/8);i++)worklet.process([[new Float32Array(128).fill(value)]]);};
run(650,.12);run(1000,0);
assert.equal(messages.filter(value=>value.samples&&!value.manual).length,0,'one-second pause ended the question');
run(650,.12);run(1500,0);
const recordings=messages.filter(value=>value.samples&&!value.manual);
assert.equal(recordings.length,1,'the two clauses should form one utterance');
assert.ok(recordings[0].samples.length>16000,'both speech clauses should be included');
'''
    result=subprocess.run(['node','--input-type=module','-e',script],cwd=Path(__file__).resolve().parents[1],
                          capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
