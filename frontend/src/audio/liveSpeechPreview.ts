// Optional browser recognition runs beside the recorded WAV. The WAV remains
// available for Fish/Gemini/Vosk when the browser cannot confirm the words.
type Alternative={transcript:string;confidence?:number};
type Result={isFinal:boolean;length:number;[index:number]:Alternative};
type Recognition={lang:string;continuous:boolean;interimResults:boolean;maxAlternatives:number;
 onresult:((event:{results:ArrayLike<Result>})=>void)|null;
 onerror:((event:{error?:string})=>void)|null;onend:(()=>void)|null;
 start:()=>void;stop:()=>void;abort:()=>void};
type RecognitionHost={SpeechRecognition?:new()=>Recognition;webkitSpeechRecognition?:new()=>Recognition};

export function createLiveSpeechPreview(onUpdate:(text:string)=>void,host:RecognitionHost=globalThis as RecognitionHost){
 const Constructor=host.SpeechRecognition||host.webkitSpeechRecognition;
 if(!Constructor)return null;
 let recognition:Recognition;
 try{recognition=new Constructor();}catch{return null;}
 recognition.lang='pt-BR';recognition.continuous=true;recognition.interimResults=true;recognition.maxAlternatives=1;
 let finalText='',allFinal=false,minimumConfidence=1,confidenceReported=false,failed=false,closed=false;
 let finished:(()=>void)|null=null;
 recognition.onresult=event=>{
  const parts:string[]=[];let complete=true,confidence=1,reported=false,finals=0;
  for(let index=0;index<event.results.length;index++){
   const result=event.results[index],word=result[0];if(!word?.transcript?.trim())continue;
   parts.push(word.transcript.trim());
   if(result.isFinal){
    finals++;
    // WebView/Chromium can return zero when no confidence is supplied. Treat
    // that as unknown, not as proof that a complete transcript is incorrect.
    if(typeof word.confidence==='number'&&Number.isFinite(word.confidence)&&word.confidence>0){
     reported=true;confidence=Math.min(confidence,word.confidence);
    }
   }else complete=false;
  }
  if(closed)return;
  finalText=parts.join(' ').trim();allFinal=complete&&finals>0;minimumConfidence=confidence;confidenceReported=reported;
  onUpdate(finalText);
  if(allFinal)finished?.();
 };
 recognition.onerror=()=>{failed=true;finished?.();};
 recognition.onend=()=>finished?.();
 try{recognition.start();}catch{return null;}
 return {
  async finish(durationSeconds:number){
   try{recognition.stop();}catch{/* The browser already ended recognition. */}
   if(!allFinal&&!failed)await Promise.race([new Promise<void>(resolve=>{finished=resolve;}),
                                             new Promise<void>(resolve=>setTimeout(resolve,700))]);
   closed=true;finished=null;
   const words=finalText.split(/\s+/).filter(Boolean);
   // One accidental word from room noise must not replace the complete WAV
   // with a confident but unrelated browser transcript.
   return !failed&&allFinal&&(!confidenceReported||minimumConfidence>=.82)&&words.length>=Math.max(3,Math.floor(durationSeconds*.75))
    ?finalText:null;
  },
  abort(){closed=true;finished=null;try{recognition.abort();}catch{/* Already stopped. */}}
 };
}
