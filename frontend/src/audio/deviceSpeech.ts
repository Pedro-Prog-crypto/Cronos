/** Device speech is a fallback for the actual answer, never a canned reply. */
export async function findDeviceVoice(signal:AbortSignal):Promise<SpeechSynthesisVoice|null>{
 const synth=globalThis.speechSynthesis;if(!synth||signal.aborted)return null;
 const choose=()=>{try{return synth.getVoices().filter(v=>v.localService&&/^pt(?:-|$)/i.test(v.lang)).sort((a,b)=>Number(/^pt-BR$/i.test(b.lang))-Number(/^pt-BR$/i.test(a.lang)))[0]||null;}catch{return null;}};
 const ready=choose();if(ready)return ready;
 return new Promise(resolve=>{
  let timer:ReturnType<typeof setTimeout>;
  const finish=(voice:SpeechSynthesisVoice|null)=>{clearTimeout(timer);synth.removeEventListener('voiceschanged',changed);signal.removeEventListener('abort',abort);resolve(voice);};
  const changed=()=>{const voice=choose();if(voice)finish(voice);};const abort=()=>finish(null);
  synth.addEventListener('voiceschanged',changed);signal.addEventListener('abort',abort,{once:true});timer=setTimeout(()=>finish(choose()),1200);changed();
 });
}
export async function speakDeviceText(text:string,voice:SpeechSynthesisVoice,signal:AbortSignal,options:{volume:number;rate:number;onStart:(part:string)=>void}){
 const synth=globalThis.speechSynthesis;if(!synth||signal.aborted)return;
 const parts:string[]=[];let remaining=text;
 while(remaining.trim()){
  let end=remaining.length<=160?remaining.length:remaining.lastIndexOf(' ',160);if(end<1)end=Math.min(160,remaining.length);
  parts.push(remaining.slice(0,end));remaining=remaining.slice(end);
 }
 for(const part of parts){
  if(signal.aborted)return;
  await new Promise<void>((resolve,reject)=>{
   const utterance=new SpeechSynthesisUtterance(part);utterance.voice=voice;utterance.lang=voice.lang;utterance.rate=Math.max(.5,Math.min(2,options.rate));utterance.volume=options.volume;
   let timer:ReturnType<typeof setTimeout>,done=false;
   const finish=(error?:Error)=>{if(done)return;done=true;clearTimeout(timer);signal.removeEventListener('abort',abort);utterance.onstart=null;utterance.onend=null;utterance.onerror=null;if(error)reject(error);else resolve();};
   const fail=(message:string)=>{finish(new Error(message));synth.cancel();};
   const abort=()=>{finish();synth.cancel();};signal.addEventListener('abort',abort,{once:true});
   utterance.onstart=()=>{clearTimeout(timer);options.onStart(part);timer=setTimeout(()=>fail('A voz do dispositivo parou de responder. A resposta continua disponível para leitura.'),Math.max(30000,part.length*450/utterance.rate));};utterance.onend=()=>finish();utterance.onerror=event=>finish(new Error('A voz do dispositivo não pôde ser reproduzida: '+event.error));
   timer=setTimeout(()=>fail('A voz do dispositivo não iniciou. Confira a permissão de som.'),3000);
   synth.cancel();synth.resume();synth.speak(utterance);
  });
 }
}
