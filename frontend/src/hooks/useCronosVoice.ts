import {useCallback, useEffect, useRef, useState} from 'react';
import {api} from '../api';

export function speechChunks(text:string):string[]{
  const chunks:string[]=[];let remaining=text;
  while(remaining.length){
    const limit=chunks.length?360:220;
    if(remaining.length<=limit){chunks.push(remaining);break;}
    const prefix=remaining.slice(0,limit),sentences=[...prefix.matchAll(/[.!?](?:[\s]|$)/g)];
    let cut=sentences.length?sentences[chunks.length?sentences.length-1:0].index!+1:prefix.lastIndexOf(' ');
    if(cut<40)cut=limit;
    chunks.push(remaining.slice(0,cut));remaining=remaining.slice(cut);
  }
  return chunks.filter(chunk=>chunk.trim());
}

interface VoiceProps { preferences?: any; onSpeechStart?: (metrics?:{speech_request_ms:number;playback_ms:number;turn_id?:string}) => void; onSpeechEnd?: () => void; onError?: (message: string) => void; }
export function useCronosVoice({preferences,onSpeechStart,onSpeechEnd,onError}: VoiceProps = {}) {
  const [isSpeaking,setIsSpeaking]=useState(false), [isGenerating,setIsGenerating]=useState(false);
  const audioLevelSource=useRef(0);
  const prefs=useRef(preferences);prefs.current=preferences;
  const callbacks=useRef({onSpeechStart,onSpeechEnd,onError});
  callbacks.current={onSpeechStart,onSpeechEnd,onError};
  const context=useRef<AudioContext|null>(null), audio=useRef<HTMLAudioElement|null>(null);
  const frame=useRef(0), url=useRef(''), pending=useRef<AbortController|null>(null);
  const source=useRef<MediaElementAudioSourceNode|null>(null), analyser=useRef<AnalyserNode|null>(null);
  const outputGain=useRef<GainNode|null>(null),renderedSpeed=useRef(1);
  useEffect(()=>{if(outputGain.current)outputGain.current.gain.value=preferences?.voice_volume??1;if(audio.current)audio.current.playbackRate=2**(((preferences?.voice_pitch??.5)-.5)*.7)*(preferences?.voice_speed??renderedSpeed.current)/renderedSpeed.current;},[preferences?.voice_volume,preferences?.voice_pitch,preferences?.voice_speed]);
  const generation=useRef(0);
  const prepare=useCallback(()=>{
    context.current ||= new AudioContext();
    if(context.current.state==='suspended')void context.current.resume().catch(()=>{});
  },[]);
  const stop=useCallback(()=>{
    generation.current++; pending.current?.abort();pending.current=null;
    outputGain.current?.disconnect();outputGain.current=null;
    audio.current?.pause(); if(audio.current)audio.current.removeAttribute('src');
    source.current?.disconnect();source.current=null;analyser.current?.disconnect();analyser.current=null;
    cancelAnimationFrame(frame.current);if(url.current)URL.revokeObjectURL(url.current);url.current='';
    audioLevelSource.current=0;setIsSpeaking(false);setIsGenerating(false);callbacks.current.onSpeechEnd?.();
  },[]);
  const speak=useCallback(async(text:string,turn_id?:string)=>{
    stop();const current=generation.current;setIsGenerating(true);
    try {
      // Web Audio ativado no gesto do usuário; nunca simular fala se houver falha.
      context.current ||= new AudioContext(); await context.current.resume();
      const controller=new AbortController();pending.current=controller;
      const chunks=speechChunks(text);
      const fetchChunk=async(part:string)=>{
        const speed=prefs.current?.voice_speed,started=performance.now();
        try{const response=await api('/voice/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:part,...(speed!==undefined?{speed}:{})}),signal:controller.signal});return {blob:await response.blob(),error:null,speed,elapsed:performance.now()-started};}
        catch(error){return {blob:null,error,speed,elapsed:performance.now()-started};}
      };
      // Only the current chunk and one look-ahead are retained. No voice/model changes.
      let next=fetchChunk(chunks[0]||text);
      for(let index=0;index<chunks.length;index++){
        const received=await next;if(current!==generation.current)return;
        if(received.error)throw received.error;
        if(index+1<chunks.length)next=fetchChunk(chunks[index+1]);
        if(url.current)URL.revokeObjectURL(url.current);
        source.current?.disconnect();analyser.current?.disconnect();cancelAnimationFrame(frame.current);
        const receivedAt=performance.now();url.current=URL.createObjectURL(received.blob!);const player=new Audio(url.current);audio.current=player;
        renderedSpeed.current=received.speed??1;player.playbackRate=2**(((prefs.current?.voice_pitch??.5)-.5)*.7)*(prefs.current?.voice_speed??renderedSpeed.current)/renderedSpeed.current;player.preservesPitch=false;
        const output=prefs.current?.output_label;
        if(output){const devices=await navigator.mediaDevices.enumerateDevices();const chosen=devices.find(d=>d.kind==='audiooutput'&&d.label===output);const ctx=context.current as any;if(!chosen||!ctx.setSinkId)throw new Error('Seleção de saída não disponível neste WebView. Use o dispositivo padrão do Windows.');await ctx.setSinkId(chosen.deviceId);}else if((context.current as any).setSinkId){await (context.current as any).setSinkId('');}
        const meter=context.current.createAnalyser();meter.fftSize=256;analyser.current=meter;
        source.current=context.current.createMediaElementSource(player);source.current.connect(meter);outputGain.current?.disconnect();const gain=context.current.createGain();outputGain.current=gain;gain.gain.value=prefs.current?.voice_volume??1;meter.connect(gain);gain.connect(context.current.destination);
        const values=new Uint8Array(meter.fftSize);let last=0;
        const measure=(time:number)=>{if(current!==generation.current)return;if(time-last>50){meter.getByteTimeDomainData(values);let sum=0;for(const value of values)sum+=((value-128)/128)**2;audioLevelSource.current=Math.min(1,Math.sqrt(sum/values.length)*4);last=time;}frame.current=requestAnimationFrame(measure);};
        player.onplaying=()=>{setIsGenerating(false);setIsSpeaking(true);if(!index)callbacks.current.onSpeechStart?.({turn_id,speech_request_ms:Math.round(received.elapsed),playback_ms:Math.round(performance.now()-receivedAt)});frame.current=requestAnimationFrame(measure);};
        await new Promise<void>((resolve,reject)=>{
          const aborted=()=>{player.pause();resolve();};controller.signal.addEventListener('abort',aborted,{once:true});
          const cleanup=()=>controller.signal.removeEventListener('abort',aborted);
          player.onended=()=>{cleanup();resolve();};player.onerror=()=>{cleanup();reject(new Error('O áudio recebido não pôde ser reproduzido.'));};
          player.play().catch(error=>{cleanup();reject(error);});
        });
        if(current!==generation.current)return;
        if(index+1<chunks.length){setIsSpeaking(false);setIsGenerating(true);}
      }
      if(current===generation.current)stop();
    } catch(error) {
      if(current!==generation.current)return;
      stop();callbacks.current.onError?.(error instanceof Error?error.message:'Não foi possível gerar ou reproduzir a voz.');
    }
  },[stop]);
  useEffect(()=>()=>{generation.current++;pending.current?.abort();audio.current?.pause();cancelAnimationFrame(frame.current);if(url.current)URL.revokeObjectURL(url.current);source.current?.disconnect();outputGain.current?.disconnect();context.current?.close();},[]);
  return {isSpeaking,isGenerating,audioLevelSource,speak,stop,prepare,audio,analyser};
}

async function localWave(blob:Blob){
  const decoder=new AudioContext();let decoded:AudioBuffer;
  try{decoded=await decoder.decodeAudioData(await blob.arrayBuffer());}finally{await decoder.close();}
  const renderer=new OfflineAudioContext(1,Math.ceil(decoded.duration*16000),16000),input=renderer.createBufferSource();
  input.buffer=decoded;input.connect(renderer.destination);input.start();
  const samples=(await renderer.startRendering()).getChannelData(0),bytes=new ArrayBuffer(44+samples.length*2),view=new DataView(bytes);
  const write=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
  write(0,'RIFF');view.setUint32(4,36+samples.length*2,true);write(8,'WAVE');write(12,'fmt ');view.setUint32(16,16,true);
  view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
  write(36,'data');view.setUint32(40,samples.length*2,true);
  for(let i=0;i<samples.length;i++){const v=Math.max(-1,Math.min(1,samples[i]));view.setInt16(44+i*2,v<0?v*32768:v*32767,true);}
  return new Blob([bytes],{type:'audio/wav'});
}

export function useMicrophone(onTranscript:(text:string,metrics?:{recognition_ms:number;endpoint_ms:number})=>void,onError:(message:string)=>void,local=false,blocked=false,preferences?:any) {
  const [recording,setRecording]=useState(false),[capturing,setCapturing]=useState(false),[starting,setStarting]=useState(false),[transcribing,setTranscribing]=useState(false);
  const audioLevelSource=useRef(0),enabled=useRef(false),opening=useRef(false),processing=useRef(false),mounted=useRef(true);
  const latest=useRef({onTranscript,onError,local,blocked,preferences});latest.current={onTranscript,onError,local,blocked,preferences};
  const captureVersion=useRef(0),resumeAfter=useRef(0);
  const resources=useRef<{stream?:MediaStream;recorded?:MediaStream;context?:AudioContext;recorder?:MediaRecorder;node?:AudioWorkletNode;timer?:ReturnType<typeof setInterval>;abort?:AbortController}>({});
  const cancelCapture=useCallback(()=>{captureVersion.current++;processing.current=false;resumeAfter.current=performance.now()+250;resources.current.abort?.abort();resources.current.node?.port.postMessage({blocked:true});if(resources.current.recorder?.state==='recording')resources.current.recorder.stop();audioLevelSource.current=0;if(mounted.current){setCapturing(false);setTranscribing(false);}},[]);
  const stop=useCallback(()=>{
    enabled.current=false;captureVersion.current++;processing.current=false;resources.current.abort?.abort();
    if(resources.current.timer)clearInterval(resources.current.timer);
    const recorder=resources.current.recorder;if(recorder?.state==='recording')recorder.stop();
    if(resources.current.node){resources.current.node.port.onmessage=null;resources.current.node.disconnect();}
    resources.current.recorded?.getTracks().forEach(track=>track.stop());resources.current.recorded=undefined;
    resources.current.stream?.getTracks().forEach(track=>track.stop());resources.current.context?.close();
    resources.current.stream=undefined;resources.current.context=undefined;audioLevelSource.current=0;
    if(mounted.current){setRecording(false);setCapturing(false);setStarting(false);setTranscribing(false);}
  },[]);
  const start=useCallback(async()=>{
    if(enabled.current||opening.current)return;
    enabled.current=true;opening.current=true;setStarting(true);
    try{
      let deviceId:string|undefined;
      if(latest.current.preferences?.input_label){const devices=await navigator.mediaDevices.enumerateDevices();deviceId=devices.find(d=>d.kind==='audioinput'&&d.label===latest.current.preferences.input_label)?.deviceId;if(!deviceId)throw new Error('Microfone selecionado não disponível. Escolha outro dispositivo.');}
      const stream=await navigator.mediaDevices.getUserMedia({audio:{...(deviceId?{deviceId:{exact:deviceId}}:{}),channelCount:{ideal:1},echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      if(!enabled.current||!mounted.current){stream.getTracks().forEach(track=>track.stop());return;}
      resources.current.stream=stream;const context=new AudioContext(latest.current.local?{sampleRate:16000}:undefined);resources.current.context=context;await context.resume();if(!enabled.current||!mounted.current)return;
      const meter=context.createAnalyser();meter.fftSize=256;context.createMediaStreamSource(stream).connect(meter);
      if(context.audioWorklet&&latest.current.local){
        await context.audioWorklet.addModule(new URL('../audio/capture.worklet.js',import.meta.url).href);if(!enabled.current||!mounted.current)return;
        const node=new AudioWorkletNode(context,'cronos-capture');resources.current.node=node;
        context.createMediaStreamSource(stream).connect(node);node.connect(context.destination);
        const values=new Uint8Array(256);
        node.port.onmessage=async event=>{
          if(typeof event.data.active==='boolean'){if(mounted.current)setCapturing(event.data.active);return;}
          if(!enabled.current||latest.current.blocked||processing.current)return;
          const samples=event.data.samples as Int16Array,rate=event.data.rate as number;
          if(rate!==16000||samples.length>61*rate)return;
          processing.current=true;setTranscribing(true);node.port.postMessage({blocked:true});
          const version=captureVersion.current;
          const abort=new AbortController();resources.current.abort=abort;const recognitionStarted=performance.now();
          try{
            const bytes=new ArrayBuffer(44),view=new DataView(bytes);
            const write=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
            write(0,'RIFF');view.setUint32(4,36+samples.length*2,true);write(8,'WAVE');write(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);write(36,'data');view.setUint32(40,samples.length*2,true);
            const response=await api('/voice/transcribe',{method:'POST',headers:{'Content-Type':'audio/wav'},body:new Blob([bytes,samples.buffer as ArrayBuffer],{type:'audio/wav'}),signal:abort.signal});
            const result=await response.json();if(version===captureVersion.current&&!abort.signal.aborted&&enabled.current&&mounted.current&&result.text?.trim())latest.current.onTranscript(result.text,{recognition_ms:Math.round(performance.now()-recognitionStarted),endpoint_ms:750});
          }catch(error){if(enabled.current&&!abort.signal.aborted)latest.current.onError(error instanceof Error?error.message:'Transcrição indisponível.');}
          finally{if(version===captureVersion.current){processing.current=false;resumeAfter.current=performance.now()+250;if(mounted.current)setTranscribing(false);}}
        };
        setRecording(true);setStarting(false);
        resources.current.timer=setInterval(()=>{
          if(latest.current.blocked||processing.current)resumeAfter.current=performance.now()+250;
          const blocked=latest.current.blocked||processing.current||performance.now()<resumeAfter.current;
          node.port.postMessage({blocked,sensitivity:latest.current.preferences?.microphone_sensitivity??70,gain:latest.current.preferences?.microphone_gain??2});meter.getByteTimeDomainData(values);let sum=0;for(const value of values)sum+=((value-128)/128)**2;audioLevelSource.current=blocked?0:Math.min(1,Math.sqrt(sum/values.length)*4);
        },80);
        return;
      }
      const recorded=context.createMediaStreamDestination(),gain=context.createGain();recorded.channelCount=1;resources.current.recorded=recorded.stream;context.createMediaStreamSource(stream).connect(gain);gain.connect(recorded);
      const values=new Uint8Array(256);let heard=false,lastSpeech=0,started=0,discard=false;
      const begin=()=>{
        const version=captureVersion.current;
        const type=['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'].find(type=>MediaRecorder.isTypeSupported(type));
        const recorder=new MediaRecorder(recorded.stream,type?{mimeType:type}:undefined);resources.current.recorder=recorder;
        const parts:BlobPart[]=[];let bytes=0;heard=false;discard=false;started=performance.now();lastSpeech=started;
        recorder.ondataavailable=event=>{parts.push(event.data);bytes+=event.data.size;if(bytes>10*1024*1024){discard=true;recorder.stop();}};
        recorder.onerror=()=>{discard=true;latest.current.onError('Falha na gravação do microfone.');stop();};
        recorder.onstop=async()=>{
          if(resources.current.recorder===recorder)resources.current.recorder=undefined;if(mounted.current)setCapturing(false);
          if(version!==captureVersion.current||!enabled.current||!mounted.current||discard||!heard||!bytes)return;
          processing.current=true;setTranscribing(true);const abort=new AbortController();resources.current.abort=abort;const recognitionStarted=performance.now();
          try{
            const blob=new Blob(parts,{type:recorder.mimeType}),audio=latest.current.local?await localWave(blob):blob;
            if(!enabled.current||abort.signal.aborted)return;
            const response=await api('/voice/transcribe',{method:'POST',headers:{'Content-Type':audio.type},body:audio,signal:abort.signal});
            const result=await response.json();if(version===captureVersion.current&&!abort.signal.aborted&&enabled.current&&mounted.current&&result.text?.trim())latest.current.onTranscript(result.text,{recognition_ms:Math.round(performance.now()-recognitionStarted),endpoint_ms:750});
          }catch(error){if(enabled.current&&!abort.signal.aborted)latest.current.onError(error instanceof Error?error.message:'Transcrição indisponível.');}
          finally{if(version===captureVersion.current){processing.current=false;if(mounted.current)setTranscribing(false);}}
        };
        recorder.start(500);
      };
      setRecording(true);setStarting(false);
      resources.current.timer=setInterval(()=>{
        if(!enabled.current)return;
        const recorder=resources.current.recorder;
        if(latest.current.blocked||processing.current){resumeAfter.current=performance.now()+250;audioLevelSource.current=0;if(recorder?.state==='recording'){discard=true;recorder.stop();}return;}
        if(performance.now()<resumeAfter.current)return;
        if(!recorder){begin();return;}if(recorder.state!=='recording')return;
        meter.getByteTimeDomainData(values);let sum=0;for(const value of values)sum+=((value-128)/128)**2;
        gain.gain.value=latest.current.preferences?.microphone_gain??2;
        const rms=Math.sqrt(sum/values.length),now=performance.now();audioLevelSource.current=Math.min(1,rms*4);
        const sensitivity=(latest.current.preferences?.microphone_sensitivity??70)/100;
        if(rms>Math.max(.0015,.006-sensitivity*.005)){if(!heard)setCapturing(true);heard=true;lastSpeech=now;}
        if((heard&&now-lastSpeech>750)||(now-started>(heard?58000:3000)))recorder.stop();
      },80);
    }catch(error){stop();latest.current.onError(error instanceof Error?error.message:'Não foi possível abrir o microfone.');}
    finally{opening.current=false;if(mounted.current)setStarting(false);}
  },[stop]);
  const toggle=useCallback(()=>{if(enabled.current){stop();return Promise.resolve();}return start();},[start,stop]);
  useEffect(()=>()=>{mounted.current=false;stop();},[stop]);
  return {recording,capturing,starting,transcribing,audioLevelSource,toggle,start,stop,cancelCapture};
}
