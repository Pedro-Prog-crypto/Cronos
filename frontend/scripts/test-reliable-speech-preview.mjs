import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const temporary=mkdtempSync(join(tmpdir(),'cronos-speech-test-'));
const browser=pathToFileURL(resolve('src/audio/liveSpeechPreview.ts')).href;
const local=pathToFileURL(resolve('src/audio/localSpeechPreview.ts')).href;
const reliable=readFileSync('src/audio/reliableSpeechPreview.ts','utf8')
 .replace("'./liveSpeechPreview'",JSON.stringify(browser))
 .replace("'./localSpeechPreview'",JSON.stringify(local));
const entry=join(temporary,'reliableSpeechPreview.ts');writeFileSync(entry,reliable);
const {createReliableSpeechPreview}=await import(pathToFileURL(entry).href);
const originalTimeout=globalThis.setTimeout;
globalThis.setTimeout=(callback,delay,...args)=>originalTimeout(callback,delay===500?5:delay,...args);
globalThis.location={href:'http://127.0.0.1:58805/ui/'};

const recognitions=[],sockets=[];
globalThis.SpeechRecognition=class {
 constructor(){recognitions.push(this);this.onresult=null;this.onerror=null;this.onend=null;}
 start(){}
 stop(){this.onend?.();}
 abort(){}
 emit(text,isFinal,confidence=.94){this.onresult?.({results:[{0:{transcript:text,confidence},length:1,isFinal}]});}
};
globalThis.WebSocket=class {
 constructor(){sockets.push(this);this.onopen=null;this.onmessage=null;this.onclose=null;this.onerror=null;this.bufferedAmount=0;this.sent=[];queueMicrotask(()=>{this.onopen?.();this.message({type:'ready'});});}
 send(value){this.sent.push(value);if(typeof value==='string'&&JSON.parse(value).type==='finish')queueMicrotask(()=>this.message({type:'final',text:'quem foi Platão'}));}
 message(value){this.onmessage?.({data:JSON.stringify(value)});}
 close(){this.onclose?.();}
};

try {
 const browserWords=[];
 let preview=createReliableSpeechPreview(text=>browserWords.push(text),'fixture');
 recognitions.at(-1).emit('quem foi Platão',false);
 recognitions.at(-1).emit('quem foi Platão',true);
 assert.equal(await preview.finish(2),'quem foi Platão');
 assert.deepEqual(browserWords,['quem foi Platão','quem foi Platão']);
 assert.equal(sockets.length,0);

 const mixedWords=[];
 preview=createReliableSpeechPreview(text=>mixedWords.push(text),'fixture');
 await new Promise(resolve=>originalTimeout(resolve,15));
 assert.equal(sockets.length,1);
 sockets.at(-1).message({type:'partial',text:'calçada alguma coisa'});
 recognitions.at(-1).emit('quem foi Aristóteles',false);
 sockets.at(-1).message({type:'partial',text:'calçada em outro lugar'});
 recognitions.at(-1).emit('quem foi Aristóteles',true);
 assert.deepEqual(mixedWords,['calçada alguma coisa','quem foi Aristóteles','quem foi Aristóteles']);
 assert.equal(await preview.finish(2),'quem foi Aristóteles');

 const provisional=[];
 preview=createReliableSpeechPreview(text=>provisional.push(text),'fixture');
 await new Promise(resolve=>originalTimeout(resolve,15));
 sockets.at(-1).message({type:'partial',text:'pode me explicar Sócrates'});
 assert.equal(provisional.at(-1),'pode me explicar Sócrates');
 assert.equal(await preview.finish(2),null,'online mode must verify the recorded WAV instead of sending a Vosk guess');

 const before=recognitions.length;
 preview=createReliableSpeechPreview(()=>{},'fixture',true);
 assert.equal(recognitions.length,before,'private local mode cannot start browser cloud recognition');
 assert.equal(await preview.finish(2),'quem foi Platão');
} finally {
 globalThis.setTimeout=originalTimeout;
 rmSync(temporary,{recursive:true,force:true});
}
console.log('Reliable live captions, browser priority, cloud verification, and local-only mode passed.');
