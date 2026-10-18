import React,{useState,useEffect} from 'react';
import {jsonApi} from '../api';

export default function EvolutionCenter(){
 const [report,setReport]=useState<any>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[selected,setSelected]=useState(''),[key,setKey]=useState(''),[models,setModels]=useState<string[]>([]),[alternatives,setAlternatives]=useState('');
 const load=async()=>{const r=await jsonApi('/evolution');setReport(r);setAlternatives(r.routing.routing.fallbacks.join(', '));};
 useEffect(()=>{let active=true;void jsonApi('/evolution').then(r=>{if(active){setReport(r);setAlternatives(r.routing.routing.fallbacks.join(', '));}}).catch(e=>{if(active)setMessage(e.message);});return()=>{active=false;};},[]);
 const run=async(work:()=>Promise<void>)=>{setBusy(true);setMessage('');try{await work();}catch(e){setMessage(e instanceof Error?e.message:'Operação não concluída.');}finally{setBusy(false);}};
 const action=async(name:string,args:any)=>{
  const r=await jsonApi('/tools/execute',{name,arguments:args});
  if(r.status==='failed')throw new Error(r.error);
  if(r.status==='pending_confirmation'){
   if(!window.confirm(`Confirmar ${name}?\n${JSON.stringify(args,null,2)}\nAlternativas podem receber seu contexto e consumir créditos.`)){
    await jsonApi(`/tools/approvals/${r.approval_id}`,{session_id:r.session_id,accepted:false});return;
   }
   const done=await jsonApi(`/tools/approvals/${r.approval_id}`,{session_id:r.session_id,accepted:true});
   if(done.status!=='completed')throw new Error(done.error||'Ação não concluída.');
  }
  await load();setMessage('Configuração salva.');
 };
 const authorizeConfiguredBackups=()=>void run(async()=>{
  const primary=report?.primary_provider;
  const ids=(report?.providers||[])
   .filter((provider:any)=>provider.configured&&provider.id!==primary&&provider.id!=='ollama')
   .map((provider:any)=>provider.id);
  if(!ids.length)throw new Error('Não há outra integração online configurada. Cadastre e configure uma chave primeiro.');
  setAlternatives(ids.join(', '));
  await action('integrations_routing',{enabled:true,fallbacks:ids});
 });
 return <div className="panel-box"><h3>EVOLUÇÃO E CONSELHO DE IAS</h3><p>Check-up sob demanda, sem manter modelos carregados no notebook.</p><button disabled={busy} onClick={()=>void run(load)}>ATUALIZAR CHECK-UP</button>
 <p>{report?.providers?.length??'—'} provedores registrados · alternativas {report?.routing?.routing?.enabled?'autorizadas':'desligadas'}</p>
 {(report?.proposals||[]).map((p:any,i:number)=><p key={i}>{p.title} · {p.evidence_ms} ms · proposta, sem alteração automática.</p>)}
 <label>Provedor<select aria-label="Provedor" value={selected} onChange={e=>{setSelected(e.target.value);setModels([]);setKey('');}}><option value="">Escolher integração</option>{report?.providers?.map((p:any)=><option key={p.id} value={p.id}>{p.id} · {p.model} · {p.configured?'configurado':'falta configuração'}</option>)}</select></label>
 <button disabled={busy||!selected} onClick={()=>void run(async()=>{const r=await jsonApi(`/providers/${encodeURIComponent(selected)}/models`);setModels(r.models);setMessage('Modelos anunciados pela API. Isso não comprova cota gratuita.');})}>CONSULTAR MODELOS DA API</button>
 {models.length>0&&<select aria-label="Modelos disponíveis" size={Math.min(8,models.length)}>{models.map(m=><option key={m}>{m}</option>)}</select>}
 {selected&&!['gemini','ollama'].includes(selected)&&<form onSubmit={e=>{e.preventDefault();void run(async()=>{try{await jsonApi('/evolution/credential',{provider_id:selected,key});await load();setMessage('Chave salva localmente; não enviada ao conselho de IAs.');}finally{setKey('');}});}}><label>Chave da integração<input type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)} maxLength={4096}/></label><small>Armazenada no .env local. Não é criptografada; mantenha sua conta Windows protegida.</small><button disabled={busy||!key}>SALVAR CHAVE LOCAL</button></form>}
 <label>Alternativas autorizadas, em ordem (IDs separados por vírgula)<input value={alternatives} onChange={e=>setAlternatives(e.target.value)}/></label><small>Conversas de texto apenas. Áudio Gemini Live e pedidos a uma IA específica preservam o provedor. As alternativas podem cobrar e receber o contexto da conversa.</small>
 <button disabled={busy||!report?.providers?.some((p:any)=>p.configured&&p.id!==report?.primary_provider&&p.id!=='ollama')} onClick={authorizeConfiguredBackups}>ATIVAR RESERVA COM PROVEDORES CONFIGURADOS</button>
 <button disabled={busy} onClick={()=>void run(()=>action('integrations_routing',{enabled:true,fallbacks:alternatives.split(',').map(v=>v.trim()).filter(Boolean)}))}>AUTORIZAR ALTERNATIVAS</button>
 <button disabled={busy} onClick={()=>void run(()=>action('integrations_routing',{enabled:false,fallbacks:[]}))}>DESLIGAR ALTERNATIVAS</button>
 <button disabled={busy||!report?.routing?.previous} onClick={()=>void run(()=>action('integrations_rollback',{}))}>RESTAURAR POLÍTICA ANTERIOR</button>
 <p>Novos provedores: peça “Cronos, pesquise novas IAs em fontes oficiais e compare custos e compatibilidade”. Registro exige confirmação; APIs diferentes podem precisar de um novo conector. Não baixa nem executa código de sites.</p>{message&&<p role="status">{message}</p>}</div>;
}
