import React,{useCallback,useEffect,useRef,useState} from 'react';
import {api,jsonApi} from '../api';
import {Mic,Pause,Play,Save,Volume2} from 'lucide-react';

type WakeConfig={activation_phrase:string;pause_phrase:string;resume_phrase:string;start_with_windows:boolean};
type WakeStatus={windows_available:boolean;model_installed:boolean;dependencies_installed:boolean;state:string;paused:boolean;settings:WakeConfig;reason?:string};
const defaults:WakeConfig={activation_phrase:'cronos',pause_phrase:'pausar cronos',resume_phrase:'retomar cronos',start_with_windows:false};

export function WakeSettings({onPrepare}:{onPrepare:()=>void}){
 const [data,setData]=useState<WakeStatus|null>(null),[draft,setDraft]=useState(defaults),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),dirty=useRef(false);
 const refresh=useCallback(async()=>{try{const response=await api('/wake/status');const value=await response.json() as WakeStatus;setData(value);if(!dirty.current)setDraft(value.settings||defaults);}catch{/* O painel permanece utilizável quando o backend desconecta. */}},[]);
 useEffect(()=>{void refresh();const timer=window.setInterval(()=>void refresh(),5000);return()=>window.clearInterval(timer);},[refresh]);
 const run=async(fn:()=>Promise<unknown>,success:string)=>{setBusy(true);setMessage('');try{await fn();setMessage(success);await refresh();}catch(error){setMessage(error instanceof Error?error.message:'Não foi possível concluir a ação.');}finally{setBusy(false);}};
 const save=()=>run(async()=>{const result=await jsonApi('/wake/settings',draft);setDraft(result.settings||draft);dirty.current=false;},'Frases salvas. O ouvinte aplica a alteração sem reiniciar.');
 const toggleStartup=()=>run(async()=>{await jsonApi('/wake/settings',draft);await jsonApi('/wake/startup',{enabled:!draft.start_with_windows});dirty.current=false;},draft.start_with_windows?'Inicialização automática desativada.':'Inicialização automática ativada.');
 const listening=data?.state==='listening'||data?.state==='paused';
 return <section className="wake-settings panel-box" aria-label="Comando de voz em segundo plano">
  <h3><Mic/> COMANDO DE VOZ EM SEGUNDO PLANO <small>{data?.state==='listening'?'ATIVO':data?.state==='paused'?'PAUSADO':'DESATIVADO'}</small></h3>
  <p>Depois de iniciar, o ouvinte funciona no notebook inteiro: pode estar no navegador, em outro aplicativo ou com a janela do Cronos fechada. O reconhecimento da frase ocorre localmente. Escolha as palavras que quiser; a pausa continua até o comando de retomada, sem cronômetro obrigatório.</p>
  <div className="wake-phrases">
   {([['activation_phrase','Frase para chamar o Cronos'],['pause_phrase','Frase para pausar a escuta'],['resume_phrase','Frase para retomar a escuta']] as const).map(([key,label])=><label key={key}>{label}<input value={draft[key]} maxLength={80} onChange={event=>{dirty.current=true;setDraft(value=>({...value,[key]:event.target.value}));}}/></label>)}
  </div>
  <div className="wake-actions">
   <button disabled={busy} onClick={()=>void save()}><Save/>SALVAR FRASES</button>
   {data?.windows_available&&!data?.model_installed&&<button disabled={busy} onClick={onPrepare}><Volume2/>PREPARAR MODELO LOCAL</button>}
   <button disabled={busy||!data?.windows_available||!data?.model_installed||!data?.dependencies_installed} onClick={()=>void run(()=>jsonApi(listening?'/wake/stop':'/wake/start',{}),listening?'Escuta local encerrada.':'Escuta local iniciada.')}>
    {listening?<><Pause/>PARAR OUVINTE</>:<><Play/>INICIAR OUVINTE</>}
   </button>
   <button disabled={busy||!data?.windows_available||!data?.model_installed||!data?.dependencies_installed} onClick={()=>void toggleStartup()} aria-pressed={Boolean(draft.start_with_windows)}><Volume2/>{draft.start_with_windows?'DESATIVAR INÍCIO COM WINDOWS':'INICIAR COM WINDOWS'}</button>
  </div>
  {(!data?.model_installed||!data?.dependencies_installed)&&<small>Antes de iniciar a escuta global, prepare o modelo local. As dependências de áudio vêm com a instalação completa do Cronos.</small>}
  {data?.reason&&<small>O ouvinte parou por uma falha local ({data.reason}).</small>}
  {message&&<p role="status" className="wake-message">{message}</p>}
 </section>;
}
