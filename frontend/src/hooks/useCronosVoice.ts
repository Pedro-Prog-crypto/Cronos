import {useCallback, useEffect, useRef, useState} from 'react';
import {api,getToken} from '../api';
import {routeVoiceOutput} from '../audio/outputDevice';
import {playPCM} from '../audio/playPCM';
import {spokenText} from '../audio/spokenText';
import captureWorkletUrl from '../audio/capture.worklet.js?worker&url';
import vadWasmUrl from '@echogarden/fvad-wasm/fvad.wasm?url';
import {createSpeechDetector} from '../audio/speechDetector.js';

let vadBinary:Promise<ArrayBuffer>|null=null;
function loadVad(){return vadBinary||=(fetch(vadWasmUrl).then(response=>{if(!response.ok)throw new Error('Detector local de voz indisponível.');return response.arrayBuffer();}).catch(error=>{vadBinary=null;throw error;}));}

function pcmWav(samples:Int16Array,rate=16000){
  const bytes=new ArrayBuffer(44),view=new DataView(bytes);
  const write=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
  write(0,'RIFF');view.setUint32(4,36+samples.length*2,true);write(8,'WAVE');write(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);write(36,'data');view.setUint32(40,samples.length*2,true);
  return new Blob([bytes,samples.buffer as ArrayBuffer],{type:'audio/wav'});
}

export function speechChunks(text:string,firstLimit=80):string[]{
  const chunks:string[]=[];let remaining=text;
  while(remaining.length){
    const limit=chunks.length?360:firstLimit;
    if(remaining.length<=limit){chunks.push(remaining);break;}
    const prefix=remaining.slice(0,limit),sentences=[...prefix.matchAll(/[.!?](?:[\s]|$)/g)];
    let cut=sentences.length?sentences[chunks.length?sentences.length-1:0].index!+1:prefix.lastIndexOf(' ');
    if(cut<20)cut=prefix.lastIndexOf(' ');
    if(cut<1)cut=limit;
    chunks.push(remaining.slice(0,cut));remaining=remaining.slice(cut);
  }
  return chunks.filter(chunk=>chunk.trim());
}

interface VoiceProps { preferences?: any; streaming?:boolean; onSpeechStart?: (metrics?:{speech_request_ms:number;playback_ms:number;turn_id?:string}) => void; onSpeechChunk?: (text:string,index:number,turnId?:string) => void; onSpeechEnd?: () => void; onError?: (message: string) => void; }
export function useCronosVoice({preferences,streaming,onSpeechStart,onSpeechChunk,onSpeechEnd,onError}: VoiceProps = {}) {
  const [isSpeaking,setIsSpeaking]=useState(false), [isGenerating,setIsGenerating]=useState(false);
  const audioLevelSource=useRef(0);
  const prefs=useRef(preferences);prefs.current=preferences;
  const callbacks=useRef({streaming,onSpeechStart,onSpeechChunk,onSpeechEnd,onError});
  callbacks.current={streaming,onSpeechStart,onSpeechChunk,onSpeechEnd,onError};
  const context=useRef<AudioContext|null>(null), audio=useRef<HTMLAudioElement|null>(null);
  const frame=useRef(0), url=useRef(''), pending=useRef<AbortController|null>(null);
  const source=useRef<MediaElementAudioSourceNode|null>(null), analyser=useRef<AnalyserNode|null>(null);
  const outputGain=useRef<GainNode|null>(null),renderedSpeed=useRef(1);
  useEffect(()=>{if(outputGain.current)outputGain.current.gain.value=preferences?.voice_volume??1;if(audio.current)audio.current.playbackRate=2**(((preferences?.voice_pitch??.5)-.5)*.7)*(preferences?.voice_speed??renderedSpeed.current)/renderedSpeed.current;},[preferences?.voice_volume,preferences?.voice_pitch,preferences?.voice_speed]);
  const outputWarning=useRef('');
  const configureOutput=async()=>routeVoiceOutput(context.current!,prefs.current?.output_label,message=>{if(outputWarning.current!==message){outputWarning.current=message;callbacks.current.onError?.(message);}});
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
  const speak=useCallback(async(text:string,turn_id?:string,continuation?:Promise<string>,completeFile=false)=>{
    text=spokenText(text);stop();if(!text)return;const current=generation.current;setIsGenerating(true);
    try {
      if((prefs.current?.voice_volume??1)<=0)throw new Error('O volume da voz está em zero. Aumente no painel Síntese de voz e tente novamente.');
      // Web Audio ativado no gesto do usuário; nunca simular fala se houver falha.
      context.current ||= new AudioContext(); await context.current.resume();
      const controller=new AbortController();pending.current=controller;const pcm=Boolean(callbacks.current.streaming&&!completeFile);
      const chunks=speechChunks(text);
      const fetchChunk=async(part:string)=>{
        const speed=prefs.current?.voice_speed,started=performance.now();
        try{const response=await api(pcm?'/voice/pcm':'/voice/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:part,...(speed!==undefined?{speed}:{})}),signal:controller.signal});return {response:pcm?response:null,blob:pcm?null:await response.blob(),error:null,speed,elapsed:performance.now()-started};}
        catch(error){return {response:null,blob:null,error,speed,elapsed:performance.now()-started};}
      };
      // Start the next synthesis as soon as the final reply arrives, while
      // the introduction is still playing. Keep one playback/cancellation session.
      let tail=continuation?.then(rest=>{
        const parts=speechChunks(spokenText(rest),360);
        return {parts,first:parts.length?fetchChunk(parts[0]):null};
      });
      const waitTail=async()=>{
        if(!tail||controller.signal.aborted)return null;
        let cancelled=()=>{};
        const aborted=new Promise<null>(resolve=>{cancelled=()=>resolve(null);controller.signal.addEventListener('abort',cancelled,{once:true});});
        try{return await Promise.race([tail,aborted]);}
        finally{controller.signal.removeEventListener('abort',cancelled);}
      };
      // Only the current chunk and one look-ahead are retained. No voice/model changes.
      let next=fetchChunk(chunks[0]||text);
      for(let index=0;index<chunks.length;index++){
        const received=await next;if(current!==generation.current)return;
        if(received.error)throw received.error;
        if(index+1<chunks.length)next=fetchChunk(chunks[index+1]);
        if(received.response){
          await configureOutput();
          cancelAnimationFrame(frame.current);audio.current=null;renderedSpeed.current=received.speed??1;
          await playPCM(received.response,context.current,controller.signal,{
            rate:()=>2**(((prefs.current?.voice_pitch??.5)-.5)*.7)*(prefs.current?.voice_speed??renderedSpeed.current)/renderedSpeed.current,volume:()=>prefs.current?.voice_volume??1,
            onNodes:(meter,gain)=>{analyser.current=meter;outputGain.current=gain;const values=new Uint8Array(meter.fftSize);let last=0;const measure=(now:number)=>{if(current!==generation.current)return;if(now-last>50){meter.getByteTimeDomainData(values);let sum=0;for(const v of values)sum+=((v-128)/128)**2;audioLevelSource.current=Math.min(1,Math.sqrt(sum/values.length)*4);last=now;}frame.current=requestAnimationFrame(measure);};frame.current=requestAnimationFrame(measure);},
            onStart:(bytesMs,playbackMs)=>{setIsGenerating(false);setIsSpeaking(true);callbacks.current.onSpeechChunk?.(chunks[index]||'',index,turn_id);if(!index)callbacks.current.onSpeechStart?.({turn_id,speech_request_ms:Math.round(received.elapsed+bytesMs),playback_ms:Math.round(playbackMs)});}
          });
          cancelAnimationFrame(frame.current);
        }else{
        if(url.current)URL.revokeObjectURL(url.current);
        source.current?.disconnect();analyser.current?.disconnect();cancelAnimationFrame(frame.current);
        const receivedAt=performance.now();url.current=URL.createObjectURL(received.blob!);const player=new Audio(url.current);audio.current=player;
        renderedSpeed.current=received.speed??1;player.playbackRate=2**(((prefs.current?.voice_pitch??.5)-.5)*.7)*(prefs.current?.voice_speed??renderedSpeed.current)/renderedSpeed.current;player.preservesPitch=false;
        await configureOutput();
        const meter=context.current.createAnalyser();meter.fftSize=256;analyser.current=meter;
        source.current=context.current.createMediaElementSource(player);source.current.connect(meter);outputGain.current?.disconnect();const gain=context.current.createGain();outputGain.current=gain;gain.gain.value=prefs.current?.voice_volume??1;meter.connect(gain);gain.connect(context.current.destination);
        const values=new Uint8Array(meter.fftSize);let last=0;
        const measure=(time:number)=>{if(current!==generation.current)return;if(time-last>50){meter.getByteTimeDomainData(values);let sum=0;for(const value of values)sum+=((value-128)/128)**2;audioLevelSource.current=Math.min(1,Math.sqrt(sum/values.length)*4);last=time;}frame.current=requestAnimationFrame(measure);};
        player.onplaying=()=>{setIsGenerating(false);setIsSpeaking(true);callbacks.current.onSpeechChunk?.(chunks[index]||'',index,turn_id);if(!index)callbacks.current.onSpeechStart?.({turn_id,speech_request_ms:Math.round(received.elapsed),playback_ms:Math.round(performance.now()-receivedAt)});frame.current=requestAnimationFrame(measure);};
        await new Promise<void>((resolve,reject)=>{
          const aborted=()=>{player.pause();resolve();};controller.signal.addEventListener('abort',aborted,{once:true});
          const cleanup=()=>controller.signal.removeEventListener('abort',aborted);
          player.onended=()=>{cleanup();resolve();};player.onerror=()=>{cleanup();reject(new Error('O áudio recebido não pôde ser reproduzido.'));};
          player.play().catch(error=>{cleanup();reject(error);});
        });
        }
        if(current!==generation.current)return;
        if(index===chunks.length-1&&tail){
          const remaining=await waitTail();tail=undefined;
          if(current!==generation.current)return;
          if(remaining?.parts.length){chunks.push(...remaining.parts);next=remaining.first!;}
        }
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

export function useMicrophone(onTranscript:(text:string,metrics?:{recognition_ms:number;endpoint_ms:number})=>void,onError:(message:string)=>void,local=false,blocked=false,preferences?:any,onAudio?:(audio:Blob,metrics:{recognition_ms:number;endpoint_ms:number})=>Promise<void>,interrupt?:{active:boolean;onKeyword:()=>void;wakeOnly?:boolean}) {
  const [recording,setRecording]=useState(false),[capturing,setCapturing]=useState(false),[starting,setStarting]=useState(false),[transcribing,setTranscribing]=useState(false);
  const audioLevelSource=useRef(0),enabled=useRef(false),opening=useRef(false),processing=useRef(false),mounted=useRef(true);
  const latest=useRef({onTranscript,onError,local,blocked,preferences,onAudio,interrupt});latest.current={onTranscript,onError,local,blocked,preferences,onAudio,interrupt};
  const keywordSocket=useRef<WebSocket|null>(null),keywordReady=useRef(false),keywordError=useRef(false);
  const [wakeOpen,setWakeOpen]=useState(false),wakeUntil=useRef(0);
  const captureVersion=useRef(0),resumeAfter=useRef(0);
  const resources=useRef<{stream?:MediaStream;recorded?:MediaStream;context?:AudioContext;recorder?:MediaRecorder;node?:AudioWorkletNode;timer?:ReturnType<typeof setInterval>;abort?:AbortController;vad?:Awaited<ReturnType<typeof createSpeechDetector>>}>({});
  const cancelCapture=useCallback(()=>{captureVersion.current++;processing.current=false;wakeUntil.current=0;resumeAfter.current=performance.now()+250;resources.current.abort?.abort();resources.current.node?.port.postMessage({blocked:true});if(resources.current.recorder?.state==='recording')resources.current.recorder.stop();audioLevelSource.current=0;if(mounted.current){setWakeOpen(false);setCapturing(false);setTranscribing(false);}},[]);
  const stop=useCallback(()=>{
    enabled.current=false;captureVersion.current++;processing.current=false;resources.current.abort?.abort();
    wakeUntil.current=0;if(mounted.current)setWakeOpen(false);resources.current.vad?.dispose();resources.current.vad=undefined;
    if(resources.current.timer)clearInterval(resources.current.timer);
    const recorder=resources.current.recorder;if(recorder?.state==='recording')recorder.stop();
    if(resources.current.node){resources.current.node.port.onmessage=null;try{resources.current.node.disconnect();}catch{}resources.current.node=undefined;}
    resources.current.recorded?.getTracks().forEach(track=>track.stop());resources.current.recorded=undefined;
    resources.current.stream?.getTracks().forEach(track=>{track.onended=null;track.stop();});const closing=resources.current.context;if(closing&&closing.state!=='closed')void closing.close().catch(()=>{});
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
      resources.current.stream=stream;stream.getAudioTracks().forEach(track=>{track.onended=()=>{if(enabled.current){stop();latest.current.onError('O microfone foi desconectado. Clique para reconectar, sem recarregar a página.');}};});const context=new AudioContext({sampleRate:16000});resources.current.context=context;await context.resume();if(!enabled.current||!mounted.current)return;
      const meter=context.createAnalyser();meter.fftSize=256;context.createMediaStreamSource(stream).connect(meter);
      if(context.audioWorklet){
        await context.audioWorklet.addModule(captureWorkletUrl);if(!enabled.current||!mounted.current)return;
        const node=new AudioWorkletNode(context,'cronos-capture');resources.current.node=node;
        context.createMediaStreamSource(stream).connect(node);node.connect(context.destination);
        const values=new Uint8Array(256);
        let initialize:(error?:Error)=>void=()=>{};
        node.port.onmessage=async event=>{
          if(event.data.vadReady){initialize();return;}if(event.data.vadError){initialize(new Error('Não foi possível iniciar a detecção local de voz.'));return;}
          if(event.data.keywordPre){const socket=keywordSocket.current,frames=event.data.keywordPre as Int16Array;if(keywordReady.current&&socket?.readyState===WebSocket.OPEN&&socket.bufferedAmount<12800)for(let offset=0;offset<frames.length;offset+=1600)socket.send(frames.slice(offset,offset+1600).buffer);return;}
          if(event.data.keyword){const socket=keywordSocket.current;if(keywordReady.current&&socket?.readyState===WebSocket.OPEN&&socket.bufferedAmount<12800)socket.send(event.data.keyword.buffer);return;}
          if(typeof event.data.active==='boolean'){if(mounted.current)setCapturing(event.data.active&&(!latest.current.interrupt?.wakeOnly||wakeUntil.current>performance.now()));return;}
          if(!enabled.current||latest.current.blocked||processing.current)return;
          if(latest.current.interrupt?.wakeOnly&&wakeUntil.current<performance.now())return;
          const samples=event.data.samples as Int16Array,rate=event.data.rate as number;
          if(rate!==16000||samples.length>61*rate)return;
          processing.current=true;setTranscribing(true);node.port.postMessage({blocked:true});
          wakeUntil.current=0;setWakeOpen(false);
          const version=captureVersion.current;
          const abort=new AbortController();resources.current.abort=abort;const recognitionStarted=performance.now();
          try{
            const audio=pcmWav(samples,rate);
            if(latest.current.onAudio){await latest.current.onAudio(audio,{recognition_ms:0,endpoint_ms:750});return;}
            const response=await api('/voice/transcribe',{method:'POST',headers:{'Content-Type':'audio/wav'},body:audio,signal:abort.signal});
            const result=await response.json();if(version===captureVersion.current&&!abort.signal.aborted&&enabled.current&&mounted.current){if(result.text?.trim())latest.current.onTranscript(result.text,{recognition_ms:Math.round(performance.now()-recognitionStarted),endpoint_ms:750});else latest.current.onError('Não consegui transcrever sua fala. O microfone continua ligado; repita a frase ou confira o dispositivo de entrada.');}
          }catch(error){if(enabled.current&&!abort.signal.aborted)latest.current.onError(error instanceof Error?error.message:'Transcrição indisponível.');}
          finally{if(version===captureVersion.current){processing.current=false;resumeAfter.current=performance.now()+250;if(mounted.current)setTranscribing(false);}}
        };
        const binary=(await loadVad()).slice(0);
        await new Promise<void>((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error('O detector de voz não iniciou. Atualize o WebView2 e reabra o Kronos.')),4000);initialize=error=>{clearTimeout(timeout);error?reject(error):resolve();};node.port.postMessage({vadBinary:binary},[binary]);});
        if(!enabled.current||!mounted.current)return;
        node.port.postMessage({waiting:Boolean(latest.current.interrupt?.wakeOnly)});
        setRecording(true);setStarting(false);
        resources.current.timer=setInterval(()=>{
          if(latest.current.blocked||processing.current)resumeAfter.current=performance.now()+250;
          const blocked=latest.current.blocked||processing.current||performance.now()<resumeAfter.current;
          node.port.postMessage({blocked,waiting:Boolean(latest.current.interrupt?.wakeOnly&&wakeUntil.current<performance.now()),keyword:keywordReady.current,sensitivity:latest.current.preferences?.microphone_sensitivity??70,gain:latest.current.preferences?.microphone_gain??2});meter.getByteTimeDomainData(values);let sum=0;for(const value of values)sum+=((value-128)/128)**2;audioLevelSource.current=blocked?0:Math.min(1,Math.sqrt(sum/values.length)*4);
        },80);
        return;
      }
      const vad=await createSpeechDetector(await loadVad());if(!enabled.current||!mounted.current){vad.dispose();return;}resources.current.vad=vad;
      const recorded=context.createMediaStreamDestination(),gain=context.createGain();recorded.channelCount=1;resources.current.recorded=recorded.stream;context.createMediaStreamSource(stream).connect(gain);gain.connect(recorded);
      meter.fftSize=512;const values=new Float32Array(512),vadSamples=new Int16Array(320);let heard=false,lastSpeech=0,started=0,discard=false,speechRun=0,voiceReference=0,voiceLevel=0,energyMean=0,energyVariance=0;
      const begin=()=>{
        const version=captureVersion.current;
        const type=['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'].find(type=>MediaRecorder.isTypeSupported(type));
        const recorder=new MediaRecorder(recorded.stream,type?{mimeType:type}:undefined);resources.current.recorder=recorder;
        const parts:BlobPart[]=[];let bytes=0;heard=false;discard=false;speechRun=0;voiceReference=0;voiceLevel=0;energyMean=0;energyVariance=0;started=performance.now();lastSpeech=started;
        recorder.ondataavailable=event=>{parts.push(event.data);bytes+=event.data.size;if(bytes>10*1024*1024){discard=true;recorder.stop();}};
        recorder.onerror=()=>{discard=true;latest.current.onError('Falha na gravação do microfone.');stop();};
        recorder.onstop=async()=>{
          if(resources.current.recorder===recorder)resources.current.recorder=undefined;if(mounted.current)setCapturing(false);
          if(version!==captureVersion.current||!enabled.current||!mounted.current||discard||!heard||!bytes)return;
          wakeUntil.current=0;setWakeOpen(false);
          processing.current=true;setTranscribing(true);const abort=new AbortController();resources.current.abort=abort;const recognitionStarted=performance.now();
          try{
            const blob=new Blob(parts,{type:recorder.mimeType}),audio=latest.current.local?await localWave(blob):blob;
            if(!enabled.current||abort.signal.aborted)return;
            if(latest.current.onAudio){await latest.current.onAudio(audio,{recognition_ms:0,endpoint_ms:750});return;}
            const response=await api('/voice/transcribe',{method:'POST',headers:{'Content-Type':audio.type},body:audio,signal:abort.signal});
            const result=await response.json();if(version===captureVersion.current&&!abort.signal.aborted&&enabled.current&&mounted.current){if(result.text?.trim())latest.current.onTranscript(result.text,{recognition_ms:Math.round(performance.now()-recognitionStarted),endpoint_ms:750});else latest.current.onError('Não consegui transcrever sua fala. O microfone continua ligado; repita a frase ou confira o dispositivo de entrada.');}
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
        meter.getFloatTimeDomainData(values);let sum=0;for(const value of values)sum+=value*value;
        gain.gain.value=latest.current.preferences?.microphone_gain??2;
        const rms=Math.sqrt(sum/values.length),now=performance.now();audioLevelSource.current=Math.min(1,rms*4);
        const sensitivity=latest.current.preferences?.microphone_sensitivity??70;vad.mode(sensitivity>=80?1:sensitivity>=40?2:3);
        for(let i=0;i<320;i++)vadSamples[i]=Math.max(-32767,Math.min(32767,values[i]*32767*(latest.current.preferences?.microphone_gain??2)));
        const delta=rms-energyMean;energyMean=energyMean?energyMean*.5+rms*.5:rms;energyVariance=energyVariance*.5+delta*delta*.5;voiceReference*=.99;
        const speech=vad.process(vadSamples)&&rms>.0001&&(rms>voiceReference*.18||Math.sqrt(energyVariance)>energyMean*.25);
        if(speech){voiceLevel=voiceLevel?voiceLevel*.8+rms*.2:rms;voiceReference=Math.max(voiceReference,voiceLevel);}
        speechRun=speech?speechRun+80:0;
        if(speechRun>=160){if(!heard)setCapturing(!latest.current.interrupt?.wakeOnly||wakeUntil.current>now);heard=true;lastSpeech=now;}
        if((heard&&now-lastSpeech>750)||(now-started>(heard?58000:3000)))recorder.stop();
      },80);
    }catch(error){const cancelled=!enabled.current;stop();if(!cancelled){const name=error instanceof DOMException?error.name:'';latest.current.onError(name==='NotAllowedError'||name==='SecurityError'?'Permita o microfone para o Cronos no navegador e tente novamente.':name==='NotReadableError'?'O Windows não liberou o microfone. Feche o aplicativo que está usando o dispositivo e tente novamente.':name==='NotFoundError'?'Nenhum microfone foi encontrado. Conecte um dispositivo e tente novamente.':error instanceof Error?error.message.slice(0,220):'Não foi possível abrir o microfone.');}}
    finally{opening.current=false;if(mounted.current)setStarting(false);}
  },[stop]);
  const toggle=useCallback(()=>{if(enabled.current&&resources.current.context?.state==='suspended'){return resources.current.context.resume().catch(()=>{stop();latest.current.onError('Clique novamente para reconectar o microfone.');});}if(enabled.current){stop();return Promise.resolve();}return start();},[start,stop]);
  const keywordActive=Boolean(interrupt?.active||(interrupt?.wakeOnly&&!blocked&&!wakeOpen));
  useEffect(()=>{if(!wakeOpen)return;const timeout=setTimeout(()=>{wakeUntil.current=0;setWakeOpen(false);setCapturing(false);},65000);return()=>clearTimeout(timeout);},[wakeOpen]);
  useEffect(()=>{
    if(!recording||!keywordActive)return;
    if(!resources.current.node){if(!keywordError.current){keywordError.current=true;latest.current.onError('Este WebView não oferece escuta de interrupção. Use ESC ou atualize o WebView2.');}return;}
    const url=new URL('/voice/interrupt',location.href);url.protocol=location.protocol==='https:'?'wss:':'ws:';
    let alive=true,attempts=0;let socket:WebSocket|null=null,retry:ReturnType<typeof setTimeout>|undefined;
    const open=()=>{
      socket=new WebSocket(url);const current=socket;keywordSocket.current=current;
      current.onopen=()=>current.send(JSON.stringify({token:getToken()}));
      current.onmessage=event=>{if(!alive)return;try{const data=JSON.parse(event.data);if(data.type==='ready'){keywordReady.current=true;keywordError.current=false;}if(data.type==='keyword'){if(latest.current.interrupt?.active)latest.current.interrupt.onKeyword();else if(latest.current.interrupt?.wakeOnly&&!latest.current.blocked){wakeUntil.current=performance.now()+65000;resources.current.node?.port.postMessage({arm:true});setWakeOpen(true);setCapturing(true);}}if(data.type==='unavailable'&&!keywordError.current){keywordError.current=true;latest.current.onError(data.message);}}catch{/* Ignore unrelated or malformed keyword events. */}};
      current.onclose=event=>{if(keywordSocket.current===current){keywordReady.current=false;resources.current.node?.port.postMessage({keyword:false});}if(alive&&[1006,1013].includes(event.code)&&attempts++<2)retry=setTimeout(open,300);};
    };open();
    return()=>{alive=false;clearTimeout(retry);keywordReady.current=false;if(keywordSocket.current===socket)keywordSocket.current=null;resources.current.node?.port.postMessage({keyword:false});socket?.close();};
  },[recording,keywordActive,wakeOpen,interrupt?.active]);
  useEffect(()=>()=>{mounted.current=false;stop();},[stop]);
  return {recording,capturing,starting,transcribing,audioLevelSource,toggle,start,stop,cancelCapture};
}
