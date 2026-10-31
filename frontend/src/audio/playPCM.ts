// Fish legacy PCM: signed 16-bit little endian, mono, 24 kHz.
// Decode small blocks while the HTTP response is still arriving.
export async function playPCM(response:Response,context:AudioContext,signal:AbortSignal,options:{
  rate:()=>number;volume:()=>number;onNodes:(meter:AnalyserNode,gain:GainNode)=>void;onStart:(firstBytesMs:number,playbackMs:number)=>void;
}){
  if(response.headers.get('X-PCM-Sample-Rate')!=='24000')throw new Error('Formato de áudio PCM não reconhecido.');
  const reader=response.body?.getReader();if(!reader)throw new Error('Atualize o WebView2 para reproduzir áudio em streaming.');
  const meter=context.createAnalyser();meter.fftSize=256;
  const gain=context.createGain();gain.gain.value=options.volume();meter.connect(gain);gain.connect(context.destination);options.onNodes(meter,gain);
  const nodes=new Set<AudioBufferSourceNode>();let ended=false,carry=new Uint8Array(0),scheduled=context.currentTime,first=true,firstTimer:ReturnType<typeof setTimeout>|undefined;
  let finish=()=>{};const played=new Promise<void>(resolve=>{finish=resolve;});
  const abort=()=>{if(firstTimer)clearTimeout(firstTimer);for(const node of nodes){try{node.stop();}catch{}}nodes.clear();void reader.cancel().catch(()=>{});finish();};
  signal.addEventListener('abort',abort,{once:true});
  const arrived=performance.now();
  try{
    while(!signal.aborted){
      let idleTimer:ReturnType<typeof setTimeout>|undefined;
      const idle=new Promise<never>((_,reject)=>{idleTimer=setTimeout(()=>reject(new Error('O serviço parou de enviar a voz. A resposta escrita continua disponível.')),8000);});
      let next:ReadableStreamReadResult<Uint8Array>;
      try{next=await Promise.race([reader.read(),idle]);}finally{clearTimeout(idleTimer);}
      if(next.done)break;
      const bytes=new Uint8Array(carry.length+next.value.length);bytes.set(carry);bytes.set(next.value,carry.length);
      const samples=Math.floor(bytes.length/2);carry=bytes.slice(samples*2);if(!samples)continue;
      if(first&&bytes.length>=4&&new TextDecoder().decode(bytes.slice(0,4))==='RIFF')throw new Error('O provedor retornou WAV em vez de PCM.');
      const buffer=context.createBuffer(1,samples,24000),channel=buffer.getChannelData(0),view=new DataView(bytes.buffer);
      for(let i=0;i<samples;i++)channel[i]=view.getInt16(i*2,true)/32768;
      const node=context.createBufferSource();node.buffer=buffer;const rate=Math.max(.25,Math.min(4,options.rate()));node.playbackRate.value=rate;node.connect(meter);
      const start=Math.max(scheduled,context.currentTime+.06);scheduled=start+buffer.duration/rate;nodes.add(node);
      node.onended=()=>{node.disconnect();nodes.delete(node);if(ended&&!nodes.size)finish();};node.start(start);
      if(first){first=false;const bytesMs=performance.now()-arrived,playbackMs=(start-context.currentTime)*1000;firstTimer=setTimeout(()=>{if(!signal.aborted)options.onStart(bytesMs,playbackMs);},Math.max(0,playbackMs));}
      // Bound scheduled audio to roughly two seconds; HTTP applies backpressure.
      let observed=context.currentTime,advanced=performance.now();
      while(scheduled-context.currentTime>2&&!signal.aborted){
        if(context.currentTime>observed){observed=context.currentTime;advanced=performance.now();}
        else if(performance.now()-advanced>5000)throw new Error('O dispositivo parou de reproduzir a voz. A resposta escrita continua disponível.');
        await new Promise<void>(resolve=>{const cancel=()=>{clearTimeout(timer);resolve();};const timer=setTimeout(()=>{signal.removeEventListener('abort',cancel);resolve();},40);signal.addEventListener('abort',cancel,{once:true});});
      }
    }
    if(signal.aborted)return;
    if(first)throw new Error('O provedor retornou áudio vazio.');
    if(carry.length)throw new Error('O provedor encerrou um bloco PCM incompleto.');
    ended=true;if(!nodes.size)finish();
    let playbackTimer:ReturnType<typeof setTimeout>|undefined;
    try{await Promise.race([played,new Promise<never>((_,reject)=>{playbackTimer=setTimeout(()=>reject(new Error('O dispositivo não concluiu a reprodução da voz. A resposta escrita continua disponível.')),Math.max(0,scheduled-context.currentTime)*1000+10000);})]);}
    finally{clearTimeout(playbackTimer);}
  }finally{
    signal.removeEventListener('abort',abort);abort();reader.releaseLock();meter.disconnect();gain.disconnect();
  }
}
