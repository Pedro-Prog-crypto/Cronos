import React,{useEffect,useRef,useState} from 'react';
import {ImagePlus,FileArchive,X,Upload,ScanLine} from 'lucide-react';
import {api} from '../api';
import './analysis-panel.css';
export type AnalysisKind='image'|'document';
export function AnalysisPanel({kind,onClose,onBusy,onResult}:{kind:AnalysisKind;onClose:()=>void;onBusy:(busy:boolean)=>void;onResult:(reply:string)=>void}){
 const [name,setName]=useState(''),[preview,setPreview]=useState(''),[payload,setPayload]=useState('');
 const [files,setFiles]=useState<{name:string;truncated:boolean}[]>([]),[skipped,setSkipped]=useState(0),[truncated,setTruncated]=useState(false);
 const [prompt,setPrompt]=useState(''),[phase,setPhase]=useState<'empty'|'loading'|'ready'|'analyzing'|'done'|'error'>('empty'),[error,setError]=useState(''),[reply,setReply]=useState('');
 const controller=useRef<AbortController|null>(null),fileInput=useRef<HTMLInputElement>(null),objectUrl=useRef('');
 const busyCallback=useRef(onBusy);busyCallback.current=onBusy;
 useEffect(()=>()=>{controller.current?.abort();if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);busyCallback.current(false);},[]);
 const choose=async(file?:File)=>{
  if(!file)return;controller.current?.abort();const request=new AbortController();controller.current=request;
  setError('');setReply('');setPayload('');setFiles([]);setName(file.name);setPhase('loading');
  if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);objectUrl.current='';setPreview('');
  try{
   if(kind==='image'&&!['image/png','image/jpeg'].includes(file.type))throw new Error('Escolha uma imagem PNG ou JPEG.');
   if(file.size>2*1024*1024)throw new Error('Escolha um arquivo de até 2 MiB.');
   let bytes:Blob=file;
   if(kind==='image'){
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
   const path=kind==='image'?'/vision/analyze':'/documents/analyze';
   const body=kind==='image'?{image_base64:payload,consent:true}:{name,data_base64:payload,consent:true};
   const result=await(await api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,...(prompt.trim()?{prompt:prompt.trim()}:{})}),signal:request.signal})).json();
   if(request.signal.aborted)return;setReply(result.reply);setPhase('done');onResult(result.reply);
  }catch(e){if(!request.signal.aborted){setError(e instanceof Error?e.message:'A análise falhou.');setPhase('error');}}
  finally{if(controller.current===request)onBusy(false);}
 };
 const active=phase==='analyzing';
 return <section className={`analysis-panel ${active?'is-scanning':''}`} role="region" aria-label={kind==='image'?'Análise de imagem':'Análise de arquivo'}>
  <header><ScanLine size={16}/><strong>{active?'ANALISANDO':phase==='done'?'ANÁLISE CONCLUÍDA':kind==='image'?'ANÁLISE DE IMAGEM':'ANÁLISE DE ARQUIVO'}</strong><button onClick={onClose} aria-label="Fechar análise"><X size={16}/></button></header>
  <div className="analysis-viewport">
   {preview?<img src={preview} alt={`Imagem selecionada: ${name}`}/>:files.length?<div className="analysis-file-list"><FileArchive size={30}/><b>{name}</b>{files.map(file=><span key={file.name}>{file.name}{file.truncated?' · trecho':''}</span>)}{skipped>0&&<small>{skipped} arquivo(s) ignorado(s), incluindo binários e configurações privadas.</small>}{truncated&&<small>Análise limitada a trechos: até 24 mil caracteres.</small>}</div>:<button className="analysis-pick" onClick={()=>fileInput.current?.click()}>{kind==='image'?<ImagePlus size={35}/>:<FileArchive size={35}/>}<span>{phase==='loading'?'LENDO ARQUIVO…':kind==='image'?'Escolher imagem':'Escolher ZIP ou código'}</span><small>Até 2 MiB</small></button>}
   {active&&<div className="analysis-scan" aria-hidden="true"/>}
   <i className="analysis-corner top-left"/><i className="analysis-corner bottom-right"/>
  </div>
  <input ref={fileInput} type="file" hidden aria-label={kind==='image'?'Selecionar imagem':'Selecionar ZIP ou código'} accept={kind==='image'?'image/png,image/jpeg':'.zip,.txt,.md,.py,.js,.ts,.tsx,.jsx,.json,.html,.css,.csv,.xml,.yaml,.yml,.toml,.sql,.sh,.bat,.ps1,.c,.cpp,.h,.java,.rs,.go'} onChange={e=>{void choose(e.target.files?.[0]);e.target.value='';}}/>
  {payload&&<><label className="analysis-question">O que você quer entender?<textarea aria-label="Pergunta sobre o arquivo" rows={2} maxLength={3000} value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Descreva, explique ou encontre um problema…"/></label><p className="analysis-consent">Ao analisar, {kind==='image'?'a imagem será enviada ao Gemini':'os trechos legíveis serão enviados à IA selecionada'}. Nenhum arquivo será executado.</p><div className="analysis-actions"><button disabled={active} onClick={()=>fileInput.current?.click()} aria-label="Trocar arquivo"><Upload size={14}/></button><button disabled={active} onClick={()=>void analyze()}>{active?'Analisando…':'Analisar'}</button></div></>}
  {error&&<p className="analysis-error" role="alert">{error}</p>}
  {reply&&<div className="analysis-result" tabIndex={0}>{reply}</div>}
 </section>;
}
