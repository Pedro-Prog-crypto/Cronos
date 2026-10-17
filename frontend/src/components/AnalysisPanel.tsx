import React,{useEffect,useRef,useState} from 'react';
import {ImagePlus,FileArchive,X,Upload,ScanLine,MonitorUp,Camera,Square} from 'lucide-react';
import {api} from '../api';
import {useMovable,useDragScroll} from '../hooks/useMovable';
import './analysis-panel.css';
export type AnalysisKind='image'|'document'|'screen';
export function AnalysisPanel({kind,onClose,onBusy,onResult,sessionId}:{kind:AnalysisKind;onClose:()=>void;onBusy:(busy:boolean)=>void;onResult:(reply:string,result?:any)=>void;sessionId?:string|null}){
 const movement=useMovable(),scroll=useDragScroll();
 const [name,setName]=useState(''),[preview,setPreview]=useState(''),[payload,setPayload]=useState('');
 const [files,setFiles]=useState<{name:string;truncated:boolean}[]>([]),[skipped,setSkipped]=useState(0),[truncated,setTruncated]=useState(false);
 const [prompt,setPrompt]=useState(''),[phase,setPhase]=useState<'empty'|'loading'|'ready'|'analyzing'|'done'|'error'>('empty'),[error,setError]=useState(''),[reply,setReply]=useState('');
 const controller=useRef<AbortController|null>(null),fileInput=useRef<HTMLInputElement>(null),objectUrl=useRef('');
 const video=useRef<HTMLVideoElement>(null),stream=useRef<MediaStream|null>(null),alive=useRef(true);
 const [sharing,setSharing]=useState(false);
 const stopSharing=()=>{stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;if(video.current)video.current.srcObject=null;if(alive.current)setSharing(false);};
 const busyCallback=useRef(onBusy);busyCallback.current=onBusy;
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;stopSharing();controller.current?.abort();if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);busyCallback.current(false);};},[]);
 const capture=async()=>{
  setError('');try{
   if(!stream.current){
    if(!navigator.mediaDevices?.getDisplayMedia)throw Error('Este navegador não oferece compartilhamento. Envie uma captura PNG/JPEG.');
    const media=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:2,max:2}},audio:false});
    if(!alive.current){media.getTracks().forEach(t=>t.stop());return;}
    stream.current=media;media.getVideoTracks()[0].addEventListener('ended',stopSharing,{once:true});
    video.current!.srcObject=media;await video.current!.play();if(!alive.current)return;setSharing(true);
   }
   const element=video.current!;if(!element.videoWidth)throw Error('Aguarde a janela compartilhada ficar visível e capture novamente.');
   const scale=Math.min(1,1600/Math.max(element.videoWidth,element.videoHeight));const canvas=document.createElement('canvas');canvas.width=Math.round(element.videoWidth*scale);canvas.height=Math.round(element.videoHeight*scale);canvas.getContext('2d')!.drawImage(element,0,0,canvas.width,canvas.height);
   const data=canvas.toDataURL('image/jpeg',.85);setPreview(data);setPayload(data.split(',')[1]);setName('Captura da tela');setReply('');setPhase('ready');
  }catch(e){if(alive.current)setError(e instanceof DOMException&&e.name==='NotAllowedError'?'Compartilhamento cancelado. Pode tentar de novo ou enviar uma captura.':e instanceof Error?e.message:'Não foi possível capturar a tela.');}
 };
 const choose=async(file?:File)=>{
  if(!file)return;controller.current?.abort();const request=new AbortController();controller.current=request;
  setError('');setReply('');setPayload('');setFiles([]);setName(file.name);setPhase('loading');
  if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);objectUrl.current='';setPreview('');
  try{
   if(kind!=='document'&&!['image/png','image/jpeg'].includes(file.type))throw new Error('Escolha uma imagem PNG ou JPEG.');
   if(file.size>30*1024*1024)throw new Error('Escolha um arquivo de até 30 MiB.');
   let bytes:Blob=file;
   if(kind!=='document'){
    bytes=await(await api('/vision/preview',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file,signal:request.signal})).blob();
    if(request.signal.aborted)return;objectUrl.current=URL.createObjectURL(bytes);setPreview(objectUrl.current);
   }
   const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('Não foi possível ler o arquivo.'));reader.readAsDataURL(bytes);});
   if(request.signal.aborted)return;
   if(kind==='document'){
    const result=await(await api('/documents/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:file.name,data_base64:data}),signal:request.signal})).json();
    if(request.signal.aborted)return;setFiles(result.files);setSkipped(result.skipped.length);setTruncated(result.truncated);
   }
   setPayload(data);setPhase('ready');
  }catch(e){if(!request.signal.aborted){setError(e instanceof Error?e.message:'Falha ao ler arquivo.');setPhase('error');}}
 };
 const analyze=async()=>{
  if(!payload)return;controller.current?.abort();const request=new AbortController();controller.current=request;
  setPhase('analyzing');setReply('');setError('');onBusy(true);
  try{
   const path=kind!=='document'?'/vision/analyze':'/documents/analyze';
   const body=kind!=='document'?{image_base64:payload,consent:true,source:kind==='screen'?'screen':'image',...(sessionId?{session_id:sessionId}:{})}:{name,data_base64:payload,consent:true};
   const result=await(await api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,...(prompt.trim()?{prompt:prompt.trim()}:{})}),signal:request.signal})).json();
   if(request.signal.aborted)return;setReply(result.reply);setPhase('done');onResult(result.reply,result);
  }catch(e){if(!request.signal.aborted){setError(e instanceof Error?e.message:'A análise falhou.');setPhase('error');}}
  finally{if(controller.current===request)onBusy(false);}
 };
 const active=phase==='analyzing';
 return <section ref={movement.ref} onPointerDown={e=>{movement.onPointerDown(e);scroll.onPointerDown(e);}} onPointerMove={e=>{movement.onPointerMove(e);scroll.onPointerMove(e);}} onPointerUp={e=>{movement.onPointerUp(e);scroll.onPointerUp(e);}} onPointerCancel={e=>{movement.onPointerCancel(e);scroll.onPointerCancel(e);}} onKeyDown={movement.onKeyDown} className={`analysis-panel kind-${kind} movable-surface ${active?'is-scanning':''}`} role="region" aria-label={kind==='screen'?'Ver minha tela':kind==='image'?'Análise de imagem':'Análise de arquivo'}>
  <header data-drag-handle tabIndex={0} title="Arraste para mover o painel"><ScanLine size={16}/><strong>{active?'ANALISANDO':phase==='done'?'ANÁLISE CONCLUÍDA':kind==='screen'?'VER MINHA TELA':kind==='image'?'ANÁLISE DE IMAGEM':'ANÁLISE DE ARQUIVO'}</strong><button onClick={onClose} aria-label="Fechar análise"><X size={16}/></button></header>
  {kind==='screen'&&<><video ref={video} muted playsInline style={{display:'none'}}/><p className="analysis-consent">Escolha uma janela ou aba. Só a captura enviada será analisada, sem áudio nem envio contínuo. Depois pode conversar sobre ela.</p><div className="analysis-actions"><button disabled={active} onClick={()=>void capture()}>{sharing?<Camera size={16}/>:<MonitorUp size={16}/>} {sharing?'Atualizar captura':'Compartilhar tela'}</button>{sharing&&<button onClick={stopSharing}><Square size={16}/>Parar</button>}</div></>}
  <div className="analysis-viewport">
   {preview?<img src={preview} alt={`Imagem selecionada: ${name}`}/>:files.length?<div className="analysis-file-list"><FileArchive size={30}/><b>{name}</b>{files.map(file=><span key={file.name}>{file.name}{file.truncated?' · trecho':''}</span>)}{skipped>0&&<small>{skipped} arquivo(s) ignorado(s), incluindo binários e configurações privadas.</small>}{truncated&&<small>Análise limitada a trechos: até 24 mil caracteres.</small>}</div>:<button className="analysis-pick" onClick={()=>fileInput.current?.click()}>{kind==='image'?<ImagePlus size={35}/>:<FileArchive size={35}/>}<span>{phase==='loading'?'LENDO ARQUIVO…':kind!=='document'?'Escolher imagem':'Escolher ZIP ou código'}</span><small>Até 30 MiB</small></button>}
   {active&&<div className="analysis-scan" aria-hidden="true"/>}
   <i className="analysis-corner top-left"/><i className="analysis-corner bottom-right"/>
  </div>
  <input ref={fileInput} type="file" hidden aria-label={kind!=='document'?'Selecionar imagem':'Selecionar ZIP ou código'} accept={kind!=='document'?'image/png,image/jpeg':'.zip,.txt,.md,.py,.js,.ts,.tsx,.jsx,.json,.html,.css,.csv,.xml,.yaml,.yml,.toml,.sql,.sh,.bat,.ps1,.c,.cpp,.h,.java,.rs,.go'} onChange={e=>{void choose(e.target.files?.[0]);e.target.value='';}}/>
  {payload&&<><label className="analysis-question">O que você quer entender?<textarea aria-label="Pergunta sobre o arquivo" rows={2} maxLength={3000} value={prompt} onChange={e=>{setPrompt(e.target.value);e.target.style.height='auto';e.target.style.height=Math.min(170,e.target.scrollHeight)+'px';}} placeholder="Descreva, explique ou encontre um problema…"/></label><p className="analysis-consent">Ao analisar, {kind!=='document'?'a captura será enviada à integração de visão disponível':'os trechos legíveis serão enviados à IA selecionada'}. Nenhum arquivo será executado.</p><div className="analysis-actions"><button disabled={active} onClick={()=>fileInput.current?.click()} aria-label="Trocar arquivo"><Upload size={14}/></button><button disabled={active} onClick={()=>void analyze()}>{active?'Analisando…':'Analisar'}</button></div></>}
  {error&&<p className="analysis-error" role="alert">{error}</p>}
  {reply&&<div className="analysis-result" tabIndex={0}>{reply}</div>}
 </section>;
}
