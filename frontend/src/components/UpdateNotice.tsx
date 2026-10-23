import React,{useEffect,useRef,useState} from 'react';
import {X} from 'lucide-react';
import {api,jsonApi,getToken} from '../api';
import './UpdateNotice.css';

type Props={connected:boolean;enabled:boolean;idle:boolean;voiceEnabled:boolean;onSpeak:(text:string)=>void;onBusy:(busy:boolean)=>void};
const running=new Set(['downloading','validating','generating','queued','installing','testing']);
export function UpdateNotice({connected,enabled,idle,voiceEnabled,onSpeak,onBusy}:Props){
 const [proposal,setProposal]=useState<any>(null),[report,setReport]=useState<any>(null),[error,setError]=useState(''),[working,setWorking]=useState(false),[dismissed,setDismissed]=useState(new Set<string>());
 const announcement=useRef<string|null>(null),cached=useRef<HTMLAudioElement|null>(null),spoken=useRef(new Set<string>()),latest=useRef({idle,onSpeak,voiceEnabled});latest.current={idle,onSpeak,voiceEnabled};
 const state=report?.state||{},updating=running.has(state.phase),available=report?.release?.available;
 useEffect(()=>setProposal(null),[state.id]);
 useEffect(()=>{onBusy(['queued','installing','testing'].includes(state.phase));},[state.phase,onBusy]);
 useEffect(()=>{
  if(!connected)return;let alive=true,timer:ReturnType<typeof setTimeout>,controller:AbortController|null=null;
  const poll=async()=>{
   controller=new AbortController();const timeout=setTimeout(()=>controller?.abort(),4500);
   try{const result=await(await api('/updates',{signal:controller.signal})).json();if(alive){setReport(result);setDismissed(new Set<string>(result.dismissed||[]));setError('');}}
   catch{/* Preserve the banner through the expected server restart. */}
   finally{clearTimeout(timeout);if(alive)timer=setTimeout(poll,running.has(state.phase)?2000:30000);}
  };
  void poll();return()=>{alive=false;controller?.abort();clearTimeout(timer);};
 },[connected,updating]);
 useEffect(()=>{
  if(!enabled||!idle||!voiceEnabled||updating||!['idle',undefined].includes(state.phase))return;
  const suggestion=report?.suggestions?.find((s:any)=>!dismissed.has(s.id)&&!dismissed.has(`spoken:${s.id}`)&&!spoken.current.has(s.id));
  const revision=report?.release?.revision;
  const id=available?`release-${revision}`:suggestion?.id;
  if(!id||dismissed.has(id)||dismissed.has(`spoken:${id}`)||spoken.current.has(id))return;
  spoken.current.add(id);void jsonApi('/updates/dismiss',{key:`spoken:${id}`}).catch(()=>{});
  onSpeak(available?'Senhor, existe uma atualização publicada. Posso preparar a cópia para você avaliar.':`Senhor, tenho uma sugestão de melhoria: ${suggestion.title}`);
 },[report,enabled,idle,voiceEnabled,updating,dismissed]);
 useEffect(()=>()=>{cached.current?.pause();if(announcement.current)URL.revokeObjectURL(announcement.current);},[]);
 const request=async(work:()=>Promise<void>)=>{setWorking(true);setError('');try{await work();try{setReport(await jsonApi('/updates'));}catch{/* A queued installation may already be restarting the server. */}}catch(e){setError(e instanceof Error?e.message:'Não foi possível concluir.');}finally{setWorking(false);}};
 const dismissNotice=()=>{const id=state.id||key;if(id){setDismissed(old=>new Set([...old,id]));void jsonApi('/updates/dismiss',{key:id}).catch(()=>{});}};
 const apply=()=>request(async()=>{
  if(state.origin==='ai'&&proposal?.id!==state.id){setProposal(await jsonApi(`/updates/proposal/${state.id}`));throw new Error('Leia a proposta gerada por IA e o plano de testes antes de autorizar.');}
  if(!window.confirm('Autorizar backup e instalação desta cópia? O servidor será reiniciado. Se a inicialização falhar, o supervisor tentará restaurar o código anterior.'))return;
  if(voiceEnabled&&!cached.current){
   // Cache the existing Jarvis voice BEFORE taking the server offline. No fallback voice.
   const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
   try{const response=await api('/voice/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'Senhor, estou instalando uma atualização. Aguarde a verificação. Quando terminar, recarregue a página.'}),signal:controller.signal});announcement.current=URL.createObjectURL(await response.blob());cached.current=new Audio(announcement.current);void cached.current.play().catch(()=>{});}catch{/* Lack of voice must not bypass or block backup checks. */}finally{clearTimeout(timeout);}
  }
  await jsonApi('/updates/install',{id:state.id});
  setReport((r:any)=>({...r,state:{...r.state,phase:'queued',progress:50,message:'Backup concluído. Aguardando instalação pelo supervisor.'}}));onBusy(true);
 });
 const suggestion=report?.suggestions?.find((s:any)=>!dismissed.has(s.id));
 const key=available?`release-${report?.release?.revision}`:suggestion?.id;
 const show=updating||(['ready','completed','restored','failed','recovery_failed'].includes(state.phase)&&!dismissed.has(state.id))||(enabled&&(available||suggestion)&&!dismissed.has(key));
 if(!show&&!error)return null;
 return <aside className="update-notice" aria-label="Atualizações do Cronos"><div><header className="update-notice-heading"><strong>{updating?'ATUALIZANDO CRONOS':state.phase==='ready'?'ATUALIZAÇÃO PREPARADA':'EVOLUÇÃO DO CRONOS'}</strong>{!updating&&<button className="update-notice-close" type="button" aria-label="Fechar aviso de atualização" title="Fechar aviso" onClick={dismissNotice}><X size={18}/></button>}</header><p>{updating||state.phase==='ready'||['completed','restored','failed','recovery_failed'].includes(state.phase)?state.message:available?`Atualização publicada: ${report.release.summary||report.release.revision}`:suggestion?.title}</p>
 {updating&&<progress aria-label="Progresso da atualização" max={100} value={state.progress||0}/>}
 {error&&<p role="alert">{error}</p>}
 {proposal&&<details open><summary>Proposta: {proposal.summary}</summary><p>Código gerado por IA pode conter erros. Verificações iniciais não substituem teste funcional. O backup não desfaz ações fora do Cronos.</p><p>Plano sugerido, ainda não executado: {proposal.test_plan}</p>{proposal.diffs.map((d:any)=><details key={d.path}><summary>{d.path}</summary><pre>{d.diff}</pre></details>)}</details>}
 <div className="update-notice-actions">
 {available&&!updating&&state.phase!=='ready'&&<button disabled={working} onClick={()=>void request(async()=>{await jsonApi('/updates/prepare',{revision:report.release.revision});})}>Preparar cópia</button>}
 {state.phase==='ready'&&<button disabled={working} onClick={()=>void request(async()=>{setProposal(await jsonApi(`/updates/proposal/${state.id}`));})}>Revisar alterações</button>}
 {state.phase==='ready'&&<button disabled={working||!report.managed} onClick={()=>void apply()}>Autorizar backup e instalar</button>}
 {state.phase==='ready'&&!report.managed&&<small>Reabra pelo Iniciar-Cronos-Web.bat atualizado para ativar o supervisor.</small>}
 {report?.can_rollback&&<button disabled={working} onClick={()=>void request(async()=>{await jsonApi('/updates/rollback',{id:state.id});})}>Preparar retorno à versão anterior</button>}
 {['completed','restored'].includes(state.phase)&&<button onClick={()=>{location.hash=new URLSearchParams({'cronos-session':getToken()}).toString();location.reload();}}>Recarregar página</button>}
 {updating&&cached.current&&<button onClick={()=>{if(cached.current){cached.current.currentTime=0;void cached.current.play().catch(()=>{});}}}>Ouvir aviso local</button>}
 {!updating&&state.phase!=='ready'&&<button onClick={()=>{setDismissed(old=>new Set([...old,key]));void jsonApi('/updates/dismiss',{key:state.id||key}).catch(()=>{});setReport((r:any)=>({...r,state:{phase:'idle'}}));}}>Depois</button>}
 </div></div></aside>;
}
