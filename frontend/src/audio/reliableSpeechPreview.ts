import {createLiveSpeechPreview} from './liveSpeechPreview';
import {createLocalSpeechPreview} from './localSpeechPreview';

// Browser captions take priority when available. Vosk gives a provisional
// caption only when the browser has produced no words; it is not authoritative
// for an online turn whose recorded WAV can be checked by cloud ASR.
export function createReliableSpeechPreview(onUpdate:(text:string)=>void,token:string,localOnly=false){
 let browserSawWords=false,localStarted=false,localAttempted=false;
 const browser=localOnly?null:createLiveSpeechPreview(text=>{if(text.trim()){browserSawWords=true;onUpdate(text);}});
 let local:ReturnType<typeof createLocalSpeechPreview>=null;
 const backlog:Int16Array[]=[];
 let backlogBytes=0,closed=false;
 const startLocal=()=>{
  if(localAttempted||closed)return;
  localAttempted=true;
  local=createLocalSpeechPreview(text=>{if(!browserSawWords)onUpdate(text);},token);
  localStarted=Boolean(local);
  if(local)for(const part of backlog)local.push(part);
  backlog.length=0;backlogBytes=0;
 };
 const timer=browser?setTimeout(()=>{if(!browserSawWords)startLocal();},500):null;
 if(!browser)startLocal();
 return {
  push(samples:Int16Array){
   if(closed||!samples.length)return;
   if(localStarted){local?.push(samples);return;}
   const copy=samples.slice();backlog.push(copy);backlogBytes+=copy.byteLength;
   while(backlogBytes>256000&&backlog.length)backlogBytes-=backlog.shift()!.byteLength;
  },
  async finish(durationSeconds:number){
   if(timer)clearTimeout(timer);
   const browserText=await browser?.finish(durationSeconds);
   if(browserText){closed=true;local?.abort();return browserText;}
   // A failed/unfinished browser recognition must not cause Vosk to process
   // a truncated eight-second backlog after the user has stopped speaking.
   if(!localOnly||browserSawWords){closed=true;local?.abort();return null;}
   if(!localAttempted)startLocal();
   const text=await local?.finish(durationSeconds)||null;
   closed=true;return text;
  },
  abort(){closed=true;if(timer)clearTimeout(timer);browser?.abort();local?.abort();backlog.length=0;},
 };
}
