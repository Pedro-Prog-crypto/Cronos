import assert from 'node:assert/strict';
import {createLiveSpeechPreview} from '../src/audio/liveSpeechPreview.ts';

let instance;
class FakeRecognition {
  constructor(){instance=this;this.onresult=null;this.onerror=null;this.onend=null;}
  start(){}
  stop(){this.onend?.();}
  abort(){}
  emit(text,isFinal,confidence){this.onresult?.({results:[{0:{transcript:text,confidence},length:1,isFinal}]});}
}

const updates=[];
assert.equal(createLiveSpeechPreview(()=>{},{}),null);
const good=createLiveSpeechPreview(text=>updates.push(text),{SpeechRecognition:FakeRecognition});
instance.emit('quem foi',false,0);
assert.deepEqual(updates,['quem foi']);
instance.emit('quem foi Platão',true,.95);
assert.equal(await good.finish(2),'quem foi Platão');

const weak=createLiveSpeechPreview(()=>{},{SpeechRecognition:FakeRecognition});
instance.emit('quem foi Platão',true,.4);
assert.equal(await weak.finish(2),null);

const stray=createLiveSpeechPreview(()=>{},{SpeechRecognition:FakeRecognition});
instance.emit('Calçada.',true,.99);
assert.equal(await stray.finish(1),null);

const incomplete=createLiveSpeechPreview(()=>{},{SpeechRecognition:FakeRecognition});
instance.emit('foi',false,0);
assert.equal(await incomplete.finish(2),null);
console.log('Live transcription preview and WAV fallback cases passed.');
