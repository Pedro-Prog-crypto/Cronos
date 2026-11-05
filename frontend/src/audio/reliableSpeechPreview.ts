import {createLiveSpeechPreview} from './liveSpeechPreview';
import {createLocalSpeechPreview} from './localSpeechPreview';

// Prefer the browser's immediate captions. If WebView2 supplies no words,
// start the local Portuguese stream with captured pre-roll while speech goes on.
export function createReliableSpeechPreview(onUpdate:(text:string)=>void,token:string){
 let browserSawWords=false,localStarted=false,localAttempted=false;
 const browser=createLiveSpeechPreview(text=>{if(text.trim())browserSawWords=true;if(!localStarted)onUpdate(text);});
 let local:ReturnType<typeof createLocalSpeechPreview>=null;
 const backlog:Int16Array[]=[];
 let backlogBytes=0,closed=false;
 const startLocal=()=>{
  if(localAttempted||closed)return;
  localAttempted=true;
  local=createLocalSpeechPreview(onUpdate,token);
  localStarted=Boolean(local);
  if(local)for(const part of backlog)local.push(part);
  backlog.length=0;backlogBytes=0;
 };
 const timer=browser?setTimeout(()=>{if(!browserSawWords)startLocal();},1500):null;
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
   if(!localAttempted)startLocal();
   const text=await local?.finish(durationSeconds)||null;
   closed=true;return text;
  },
  abort(){closed=true;if(timer)clearTimeout(timer);browser?.abort();local?.abort();backlog.length=0;},
 };
}
