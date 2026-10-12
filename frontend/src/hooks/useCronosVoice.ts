import {useCallback, useEffect, useRef, useState} from 'react';
import {api} from '../api';

interface VoiceProps { onSpeechStart?: () => void; onSpeechEnd?: () => void; onError?: (message: string) => void; }
export function useCronosVoice({onSpeechStart,onSpeechEnd,onError}: VoiceProps = {}) {
  const [isSpeaking,setIsSpeaking]=useState(false), [audioLevel,setAudioLevel]=useState(0), [isGenerating,setIsGenerating]=useState(false);
  const callbacks=useRef({onSpeechStart,onSpeechEnd,onError});
  callbacks.current={onSpeechStart,onSpeechEnd,onError};
  const context=useRef<AudioContext|null>(null), audio=useRef<HTMLAudioElement|null>(null);
  const frame=useRef(0), url=useRef(''), pending=useRef<AbortController|null>(null);
  const source=useRef<MediaElementAudioSourceNode|null>(null), analyser=useRef<AnalyserNode|null>(null);
  const generation=useRef(0);
  const prepare=useCallback(()=>{
    context.current ||= new AudioContext();
    if(context.current.state==='suspended')void context.current.resume().catch(()=>{});
  },[]);
  const stop=useCallback(()=>{
    generation.current++; pending.current?.abort();pending.current=null;
    audio.current?.pause(); if(audio.current)audio.current.removeAttribute('src');
    source.current?.disconnect();source.current=null;analyser.current?.disconnect();analyser.current=null;
    cancelAnimationFrame(frame.current);if(url.current)URL.revokeObjectURL(url.current);url.current='';
    setAudioLevel(0);setIsSpeaking(false);setIsGenerating(false);callbacks.current.onSpeechEnd?.();
  },[]);
  const speak=useCallback(async(text:string)=>{
    stop();const current=generation.current;setIsGenerating(true);
    try {
      // Web Audio ativado no gesto do usuário; nunca simular fala se houver falha.
      context.current ||= new AudioContext(); await context.current.resume();
      const controller=new AbortController();pending.current=controller;
      const response=await api('/voice/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),signal:controller.signal});
      const blob=await response.blob();if(current!==generation.current)return;
      url.current=URL.createObjectURL(blob);const player=new Audio(url.current);audio.current=player;
      const meter=context.current.createAnalyser();meter.fftSize=256;analyser.current=meter;
      source.current=context.current.createMediaElementSource(player);source.current.connect(meter);meter.connect(context.current.destination);
      const values=new Uint8Array(meter.fftSize);let last=0;
      const measure=(time:number)=>{
        if(current!==generation.current)return;
        if(time-last>50){meter.getByteTimeDomainData(values);let sum=0;for(const value of values)sum+=((value-128)/128)**2;setAudioLevel(Math.min(1,Math.sqrt(sum/values.length)*4));last=time;}
        frame.current=requestAnimationFrame(measure);
      };
      player.onplaying=()=>{setIsGenerating(false);setIsSpeaking(true);callbacks.current.onSpeechStart?.();frame.current=requestAnimationFrame(measure);};
      player.onended=stop;
      player.onerror=()=>{stop();callbacks.current.onError?.('O áudio recebido não pôde ser reproduzido. A resposta escrita continua disponível.');};
      await player.play();
    } catch(error) {
      if(current!==generation.current)return;
      stop();callbacks.current.onError?.(error instanceof Error?error.message:'Não foi possível gerar ou reproduzir a voz.');
    }
  },[stop]);
  useEffect(()=>()=>{generation.current++;pending.current?.abort();audio.current?.pause();cancelAnimationFrame(frame.current);if(url.current)URL.revokeObjectURL(url.current);source.current?.disconnect();context.current?.close();},[]);
  return {isSpeaking,isGenerating,audioLevel,speak,stop,prepare};
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

export function useMicrophone(onTranscript:(text:string)=>void,onError:(message:string)=>void,local=false) {
  const [recording,setRecording]=useState(false),[transcribing,setTranscribing]=useState(false),[level,setLevel]=useState(0);
  const refs=useRef<{recorder?:MediaRecorder;stream?:MediaStream;context?:AudioContext;timer?:ReturnType<typeof setTimeout>;frame?:number;abort?:AbortController}>({});
  const mounted=useRef(true), requesting=useRef(false);
  const release=useCallback(()=>{const r=refs.current;r.stream?.getTracks().forEach(track=>track.stop());r.context?.close();if(r.frame)cancelAnimationFrame(r.frame);if(r.timer)clearTimeout(r.timer);r.stream=undefined;r.context=undefined;setLevel(0);},[]);
  const toggle=useCallback(async()=>{
    const r=refs.current;
    if(r.recorder?.state==='recording'){r.recorder.stop();return;}
    if(requesting.current||transcribing)return;
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){onError('Microfone não disponível nesta janela. Use texto ou arquivo de áudio no módulo Voz.');return;}
    requesting.current=true;
    try {
      r.stream=await navigator.mediaDevices.getUserMedia({audio:true});
      if(!mounted.current){r.stream.getTracks().forEach(track=>track.stop());return;}
      const type=['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'].find(type=>MediaRecorder.isTypeSupported(type));
      const recorder=new MediaRecorder(r.stream,type?{mimeType:type}:undefined);r.recorder=recorder;
      const parts:BlobPart[]=[];let size=0,failed=false;
      r.context=new AudioContext();const meter=r.context.createAnalyser();meter.fftSize=256;r.context.createMediaStreamSource(r.stream).connect(meter);
      const values=new Uint8Array(256);let last=0,lastSpeech=performance.now(),heardSpeech=false;const started=lastSpeech;
      const measure=(time:number)=>{if(recorder.state!=='recording')return;if(time-last>50){meter.getByteTimeDomainData(values);let sum=0;for(const value of values)sum+=((value-128)/128)**2;const rms=Math.sqrt(sum/values.length);setLevel(Math.min(1,rms*4));last=time;
        if(rms>.012){heardSpeech=true;lastSpeech=time;}
        if(!heardSpeech&&time-started>8000){failed=true;onError('Não detectei fala no microfone. Tente novamente ou confira o dispositivo de entrada.');recorder.stop();return;}
        if(heardSpeech&&time-lastSpeech>1400&&time-started>1000){recorder.stop();return;}}r.frame=requestAnimationFrame(measure);};
      recorder.ondataavailable=event=>{parts.push(event.data);size+=event.data.size;if(size>10*1024*1024&&recorder.state==='recording')recorder.stop();};
      recorder.onerror=()=>{failed=true;release();setRecording(false);onError('Falha na gravação do microfone.');};
      recorder.onstop=async()=>{
        release();r.recorder=undefined;if(!mounted.current)return;setRecording(false);if(failed)return;
        if(size>10*1024*1024){onError('A gravação ultrapassou 10 MiB. Grave um trecho menor.');return;}
        if(!size){onError('A gravação não contém áudio.');return;}
        setTranscribing(true);const abort=new AbortController();r.abort=abort;
        try {const original=new Blob(parts,{type:recorder.mimeType});const audio=local?await localWave(original):original;if(!mounted.current||abort.signal.aborted)return;const response=await api('/voice/transcribe',{method:'POST',headers:{'Content-Type':audio.type},body:audio,signal:abort.signal});const result=await response.json();if(mounted.current)onTranscript(result.text);}
        catch(error){if(mounted.current&&!abort.signal.aborted)onError(error instanceof Error?error.message:'Transcrição indisponível.');}
        finally{if(mounted.current)setTranscribing(false);}
      };
      recorder.start(1000);setRecording(true);r.frame=requestAnimationFrame(measure);r.timer=setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},60000);
    } catch(error){release();onError(error instanceof Error?error.message:'Não foi possível acessar o microfone.');}
    finally{requesting.current=false;}
  },[onTranscript,onError,release,transcribing,local]);
  useEffect(()=>()=>{mounted.current=false;refs.current.abort?.abort();if(refs.current.recorder?.state==='recording')refs.current.recorder.stop();refs.current.stream?.getTracks().forEach(track=>track.stop());refs.current.context?.close();if(refs.current.frame)cancelAnimationFrame(refs.current.frame);if(refs.current.timer)clearTimeout(refs.current.timer);},[]);
  return {recording,transcribing,level,toggle};
}
