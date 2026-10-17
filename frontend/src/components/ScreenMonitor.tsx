import React,{forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {MonitorUp,Square,ChevronDown,ChevronUp} from 'lucide-react';
import {api,jsonApi,ApiError} from '../api';
import './screen-monitor.css';
export type ScreenMonitorHandle={start:()=>void;stop:()=>void};
export const ScreenMonitor=forwardRef<ScreenMonitorHandle,{sessionId:()=>string|null;onSession:(id:string)=>void}>(({sessionId,onSession},ref)=>{
 const [state,setState]=useState<'off'|'starting'|'local'|'browser'>('off'),[error,setError]=useState(''),[expanded,setExpanded]=useState(false),[preview,setPreview]=useState('');
 const active=useRef(false),owner=useRef<string|null>(null),mode=useRef(''),stream=useRef<MediaStream|null>(null),video=useRef<HTMLVideoElement|null>(null),generation=useRef(0),alive=useRef(true),timer=useRef<ReturnType<typeof setTimeout>|null>(null),heartbeat=useRef<ReturnType<typeof setInterval>|null>(null),url=useRef(''),expandedRef=useRef(false);
 expandedRef.current=expanded;
 const clean=()=>{if(timer.current)clearTimeout(timer.current);if(heartbeat.current)clearInterval(heartbeat.current);timer.current=null;heartbeat.current=null;stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;if(video.current){video.current.srcObject=null;video.current=null;}if(url.current)URL.revokeObjectURL(url.current);url.current='';};
 const stop=async()=>{
  generation.current++;active.current=false;clean();if(alive.current){setState('off');setPreview('');setError('');setExpanded(false);}
  const id=owner.current;owner.current=null;if(id)try{await jsonApi('/vision/live/stop',{session_id:id});}catch{if(alive.current)setError('Não consegui confirmar a parada no servidor. Feche o Cronos local se a conexão não voltar; a captura termina ao expirar a conexão.');}
 };
 const loop=async(version:number)=>{
  if(!active.current||version!==generation.current||!owner.current)return;
  try{
   if(mode.current==='browser'){
    const element=video.current;if(!element?.videoWidth)throw Error('A tela compartilhada ainda não está disponível.');
    const scale=Math.min(1,1600/Math.max(element.videoWidth,element.videoHeight)),canvas=document.createElement('canvas');canvas.width=Math.round(element.videoWidth*scale);canvas.height=Math.round(element.videoHeight*scale);canvas.getContext('2d')!.drawImage(element,0,0,canvas.width,canvas.height);
    const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(Error('Captura indisponível.')),'image/jpeg',.8));
    if(!active.current||version!==generation.current)return;
    await api('/vision/live/frame?session_id='+owner.current,{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob});
    if(expandedRef.current){if(url.current)URL.revokeObjectURL(url.current);url.current=URL.createObjectURL(blob);setPreview(url.current);}
   }else if(expandedRef.current){
    const blob=await(await api('/vision/live/frame?session_id='+owner.current)).blob();
    if(!active.current||version!==generation.current)return;
    if(url.current)URL.revokeObjectURL(url.current);url.current=URL.createObjectURL(blob);setPreview(url.current);
   }
   if(alive.current)setError('');
  }catch(e){if(alive.current&&active.current)setError(e instanceof Error?e.message:'Captura temporariamente indisponível.');}
  finally{if(active.current&&version===generation.current)timer.current=setTimeout(()=>void loop(version),1500);}
 };
 const connect=async(source:'local'|'browser',version:number)=>{
  const result=await jsonApi('/vision/live/start',{session_id:sessionId()||undefined,consent:true,source});
  if(version!==generation.current||!alive.current){await jsonApi('/vision/live/stop',{session_id:result.session_id});return;}
  owner.current=result.session_id;onSession(result.session_id);mode.current=source;active.current=true;setState(source);setError('');
  heartbeat.current=setInterval(()=>{if(owner.current)void jsonApi('/vision/live/keepalive',{session_id:owner.current}).catch((error)=>{if(alive.current){if(error instanceof ApiError&&error.status===409){active.current=false;clean();setState('off');owner.current=null;setError('O acompanhamento terminou porque a conexão ficou inativa. Peça para ver a tela novamente.');}else setError('A conexão do acompanhamento precisa ser restabelecida.');}});},20000);
  void loop(version);
 };
 const start=async()=>{
  if(active.current){setExpanded(v=>!v);return;}
  if(state==='starting')return;
  const version=++generation.current;setState('starting');setError('');
  try{await connect('local',version);}catch(e){if(alive.current&&version===generation.current){setState('off');setError(e instanceof Error?e.message:'A captura local não está disponível. Use Compartilhar tela inteira.');}}
 };
 const share=async()=>{
  const version=++generation.current;setState('starting');setError('');
  try{
   if(!navigator.mediaDevices?.getDisplayMedia)throw Error('Este navegador não permite compartilhar tela. Use o Cronos instalado no Windows.');
   const media=await navigator.mediaDevices.getDisplayMedia({video:{displaySurface:'monitor',frameRate:{ideal:1,max:1}},audio:false});
   if(version!==generation.current||!alive.current){media.getTracks().forEach(track=>track.stop());return;}
   const track=media.getVideoTracks()[0];
   if(track.getSettings().displaySurface&&track.getSettings().displaySurface!=='monitor'){media.getTracks().forEach(t=>t.stop());throw Error('Selecione Tela inteira para acompanhar todos os programas, em vez de uma janela ou aba.');}
   stream.current=media;track.addEventListener('ended',()=>{if(active.current)void stop();},{once:true});
   video.current=document.createElement('video');video.current.muted=true;video.current.playsInline=true;video.current.srcObject=media;await video.current.play();
   await connect('browser',version);
  }catch(e){if(version===generation.current&&alive.current){clean();setState('off');setError(e instanceof Error?e.message:'Compartilhamento cancelado.');}}
 };
 useImperativeHandle(ref,()=>({start:()=>void start(),stop:()=>void stop()}));
 useEffect(()=>{
  alive.current=true;
  const leave=()=>{const id=owner.current;generation.current++;active.current=false;clean();owner.current=null;setState('off');setPreview('');if(id)void api('/vision/live/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:id}),keepalive:true}).catch(()=>{});};
  window.addEventListener('pagehide',leave);
  return()=>{window.removeEventListener('pagehide',leave);alive.current=false;void stop();};
 },[]);
 if(state==='off'&&!error)return null;
 return <aside className="screen-monitor" aria-label="Acompanhamento da tela" role="region"><header><MonitorUp size={16}/><b>{state==='starting'?'INICIANDO VISÃO DA TELA':state==='off'?'VISÃO DA TELA':'TELA INTEIRA · AO VIVO'}</b>{state!=='off'&&state!=='starting'&&<button aria-label={expanded?'Recolher visão da tela':'Mostrar tela acompanhada'} onClick={()=>setExpanded(v=>!v)}>{expanded?<ChevronDown size={16}/>:<ChevronUp size={16}/>}</button>}<button aria-label="Parar de ver a tela" onClick={()=>void stop()}><Square size={15}/></button></header>{expanded&&preview&&<img src={preview} alt="Última captura da tela inteira acompanhada"/>}{expanded&&state!=='off'&&<p>Sem narração automática. Diga “pare de ver minha tela” para desligar. Capturas atualizadas; áudio não é capturado.</p>}{error&&<p role="alert">{error}</p>}{state==='off'&&error&&<button onClick={()=>void share()}>Compartilhar tela inteira</button>}</aside>;
});
ScreenMonitor.displayName='ScreenMonitor';
