/** @license SPDX-License-Identifier: Apache-2.0 */
import React,{Suspense,lazy,useCallback,useEffect,useRef,useState} from 'react';
import {Mic,X,Send} from 'lucide-react';
import {IntegratedNeuralStage} from './components/IntegratedNeuralStage';
import {useCronosVoice,useMicrophone} from './hooks/useCronosVoice';
import {api,jsonApi,getToken,onConnection,ApiError} from './api';

import {MemorySpiral,MemoryGraph} from './components/MemorySpiral';
import {HolographicGlobe} from './components/HolographicGlobe';
import {localCommand} from './commands';
const WorldMap=lazy(()=>import('./components/WorldMap'));

const moduleIds=['processing','vision','voice','language','planning','tools','integrations','database','internet','devices','security','monitoring'];
const moduleNames=['Processamento','Visão computacional','Síntese de voz','Entendimento de linguagem','Planejamento','Ferramentas','Integrações','Banco de dados','Internet','Dispositivos','Segurança','Monitoramento'];
type Message={role:string;content:string};
type ToolResult={name:string;status:string;approval_id?:string;session_id?:string;arguments?:unknown;result?:unknown;error?:string};

export default function App(){
  const [connected,setConnected]=useState(false),[config,setConfig]=useState<any>(null);
  const [notice,setNotice]=useState(''),[error,setError]=useState(false);
  const [chatOpen,setChatOpen]=useState(false),[module,setModule]=useState<string|null>(null);
  const [draft,setDraft]=useState(''),[messages,setMessages]=useState<Message[]>([]),[busy,setBusy]=useState(false),[tools,setTools]=useState<ToolResult[]>([]);
  const [autoVoice,setAutoVoice]=useState(true),[announceAlerts,setAnnounceAlerts]=useState(false),[monitor,setMonitor]=useState<any>(null);
  const [eyeOpen,setEyeOpen]=useState(false),[placeQuery,setPlaceQuery]=useState(''),[graph,setGraph]=useState<MemoryGraph>({nodes:[],edges:[],total:0}),[graphRevision,setGraphRevision]=useState(0),[note,setNote]=useState<{path:string;content:string}|null>(null);
  const sendRef=useRef<(text:string)=>Promise<void>>(async()=>{});
  const commandRef=useRef<(text:string)=>boolean>(()=>false),eyeAnnouncement=useRef(false);
  const pendingAlerts=useRef(new Map<number,any>());
  const session=useRef<string|null>(null),iframe=useRef<HTMLIFrameElement|null>(null),cursor=useRef(0),inFlight=useRef(false);
  const activity=useRef<'IDLE'|'LISTENING'|'SPEAKING'>('IDLE');const [moduleActivity,setModuleActivity]=useState(activity.current);
  const tell=useCallback((message:string,isError=false)=>{setNotice(message);setError(isError);},[]);
  const voice=useCronosVoice({onError:message=>tell(message,true)});
  const microphone=useMicrophone(useCallback(text=>{if(!text.trim()){tell('Não consegui entender a fala. Tente novamente.',true);return;}if(commandRef.current(text))return;setChatOpen(false);void sendRef.current(text);},[tell]),useCallback(message=>tell(message,true),[tell]),config?.transcription_provider==='vosk');
  const state=voice.isSpeaking?'SPEAKING':microphone.recording?'LISTENING':moduleActivity;
  const audioLevelSource=voice.isSpeaking?voice.audioLevelSource:microphone.audioLevelSource;
  const live=useRef({busy:false,recording:false,transcribing:false,speaking:false,generating:false,module:null as string|null,announce:false,fish:false});
  live.current={busy,recording:microphone.recording,transcribing:microphone.transcribing,speaking:voice.isSpeaking,generating:voice.isGenerating,module,announce:announceAlerts,fish:Boolean(config?.fish_configured)};
  const voiceRef=useRef(voice);voiceRef.current=voice;
  useEffect(()=>{if(!announceAlerts)pendingAlerts.current.clear();},[announceAlerts]);

  const connectBackend=useCallback(async()=>{
    setConnected(false);
    try{
      const status=await jsonApi('/status');setConfig(status);setConnected(true);setNotice('');

      // Compartilha só com a bancada da própria origem, nunca por URL/storage.
      iframe.current?.contentWindow?.postMessage({type:'cronos:connect',token:getToken()},window.location.origin);
    }catch(error){tell('Não consegui iniciar a conexão automática. Feche e abra o Kronos novamente.',true);}
  },[tell]);
  useEffect(()=>{const remove=onConnection(()=>{void connectBackend();});if(getToken())void connectBackend();return remove;},[connectBackend]);

  useEffect(()=>{
    const receive=(event:MessageEvent)=>{
      if(event.origin!==window.location.origin||event.source!==iframe.current?.contentWindow)return;
      if(event.data?.type==='cronos:activity'&&['IDLE','LISTENING','SPEAKING'].includes(event.data.state))setModuleActivity(event.data.state);
    };
    window.addEventListener('message',receive);return()=>window.removeEventListener('message',receive);
  },[]);
  useEffect(()=>{
    if(!connected)return;
    let alive=true;let polling=false;let controller:AbortController|null=null;
    const poll=async()=>{
      if(polling)return;polling=true;controller=new AbortController();const timeout=setTimeout(()=>controller?.abort(),5000);
      try{
        const result=await(await api(`/monitor?after=${cursor.current}`,{signal:controller.signal})).json();if(!alive)return;
        if(result.cursor<cursor.current)cursor.current=0;
        if(live.current.announce&&live.current.fish){
          for(const event of result.events||[])if(event.id>cursor.current&&event.status==='active'&&event.code!=='service_voice')pendingAlerts.current.set(event.id,event);
        }
        cursor.current=result.cursor;setMonitor(result);
        for(const id of pendingAlerts.current.keys())if(!result.alerts.some((alert:any)=>alert.id===id&&!alert.acknowledged))pendingAlerts.current.delete(id);
        const current=live.current;
        if(current.announce&&current.fish&&!current.busy&&!current.recording&&!current.transcribing&&!current.speaking&&!current.generating&&!current.module){
          const alerts=[...pendingAlerts.current.values()].sort((a,b)=>Number(b.severity==='critical')-Number(a.severity==='critical'));
          if(alerts.length){pendingAlerts.current.delete(alerts[0].id);void voiceRef.current.speak(`Atenção. ${alerts[0].message} ${alerts[0].suggestion}`);}
        }
      }catch(error){if(alive){setMonitor(null);if(error instanceof ApiError&&[401,403].includes(error.status)){setConnected(false);}}}
      finally{clearTimeout(timeout);polling=false;}
    };
    void poll();const timer=setInterval(poll,5000);return()=>{alive=false;controller?.abort();clearInterval(timer);};
  },[connected]);

  useEffect(()=>{
    if(!connected)return;const controller=new AbortController();let alive=true;
    void(async()=>{try{
      await api('/memory/sync',{method:'POST',signal:controller.signal});
      const nodes:MemoryGraph['nodes']=[],edges:MemoryGraph['edges']=[];let offset:number|null=0;let total=0;
      while(offset!==null){const data=await(await api(`/memory/graph?offset=${offset}&limit=1000`,{signal:controller.signal})).json();nodes.push(...data.nodes);edges.push(...data.edges);total=data.total;offset=data.next_offset;}
      const unique=new Map(edges.map(edge=>[edge.source+'|'+edge.target,edge]));
      if(alive)setGraph({nodes,edges:[...unique.values()],total});
    }catch(error){if(alive)tell('Não consegui carregar as notas da memória.',true);}})();
    return()=>{alive=false;controller.abort();};
  },[connected,graphRevision,tell]);
  useEffect(()=>{if(!connected)return;const timer=setInterval(()=>{if(!document.hidden&&!live.current.busy&&!live.current.recording&&!live.current.transcribing)setGraphRevision(value=>value+1);},60000);return()=>clearInterval(timer);},[connected]);
  const runCommand=(text:string)=>{
    const command=localCommand(text,eyeOpen);if(!command)return false;
    if((command.type==='eye'||command.type==='place')&&config?.privacy_mode==='local'){tell('O mapa mundial está desativado em modo local.',true);return true;}
    if(command.type==='eye'){voice.prepare();eyeAnnouncement.current=true;setEyeOpen(true);setChatOpen(false);setModule(null);setNote(null);}
    else if(command.type==='memory'){setEyeOpen(false);setGraphRevision(value=>value+1);}
    else if(command.type==='panel')setChatOpen(true);
    else if(command.type==='place'){setPlaceQuery(command.query);setEyeOpen(true);setChatOpen(false);}
    return true;
  };commandRef.current=runCommand;
  const selectNote=useCallback(async(path:string)=>{if(eyeOpen){setEyeOpen(false);return;}try{setNote(await jsonApi(`/memory/note?path=${encodeURIComponent(path)}`));}catch(error){tell('Não foi possível abrir essa nota.',true);}},[eyeOpen,tell]);
  const worldReady=()=>{if(eyeAnnouncement.current){eyeAnnouncement.current=false;if(config?.fish_speech_configured)void voice.speak('Ampliando sua perspectiva. Olho de Deus aberto.');}};
  useEffect(()=>{const key=(event:KeyboardEvent)=>{if(event.key==='Escape'){setEyeOpen(false);setNote(null);setChatOpen(false);}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[]);
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),8000);return()=>clearTimeout(timer);},[notice]);

  const handleMic=()=>{
    if(!connected){tell('A conexão automática ainda não está disponível. Feche e abra o Kronos novamente.',true);return;}
    if(microphone.recording){void microphone.toggle();return;}
    if(voice.isSpeaking||voice.isGenerating){voice.stop();return;}
    if(config?.transcription_provider!=='vosk'&&!config?.fish_configured){tell('Configure Fish Audio em modo online para transcrever voz. A conversa por texto continua disponível.',true);setModule('voice');return;}
    if(moduleActivity!=='IDLE'){
      (iframe.current?.contentWindow as (Window & {cronosPanelClose?:()=>void})|null)?.cronosPanelClose?.();
      setModuleActivity('IDLE');return;
    }
    if(busy||microphone.transcribing)return;
    if(autoVoice)voice.prepare();
    void microphone.toggle();
  };
  const sendText=async(value:string)=>{
    const text=value.trim();if(!text||inFlight.current)return;if(runCommand(text)){setDraft('');return;}
    if(!connected){tell('A conexão automática ainda não está disponível. Feche e abra o Kronos novamente.',true);return;}
    inFlight.current=true;setBusy(true);voice.stop();if(autoVoice)voice.prepare();setMessages(old=>[...old,{role:'user',content:text}]);setDraft('');tell('Cronos está processando sua mensagem…');
    try{
      const result=await jsonApi('/chat',{message:text,session_id:session.current});session.current=result.session_id;setGraphRevision(value=>value+1);
      setMessages(old=>[...old,{role:'assistant',content:result.reply}]);setTools(old=>[...old,...(result.tool_results||[])]);
      if(result.warnings?.length)tell(result.warnings.join('\n'),true);else setNotice('');
      if(autoVoice&&config?.fish_speech_configured)void voice.speak(result.reply);
      else if(autoVoice)tell('A resposta está escrita, mas a voz não está configurada. Confira a configuração da voz no arquivo .env.',true);
    }catch(error){
      if(error instanceof ApiError&&error.detail?.tool_results){session.current=error.detail.session_id;setTools(old=>[...old,...error.detail.tool_results]);}
      tell(error instanceof Error?error.message:'Não foi possível conversar.',true);
      setDraft(text); // Falha não elimina a pergunta; não repetir ações automaticamente.
    }finally{setBusy(false);inFlight.current=false;}
  };
  sendRef.current=sendText;
  const send=(event:React.FormEvent)=>{event.preventDefault();void sendText(draft);};
  const approve=async(result:ToolResult,accepted:boolean)=>{
    if(inFlight.current)return;inFlight.current=true;setBusy(true);
    try{const outcome=await jsonApi(`/tools/approvals/${result.approval_id}`,{session_id:result.session_id||session.current,accepted});
      setTools(old=>old.map(item=>item===result?outcome:item));tell(outcome.status==='completed'?'Solicitação atendida; confira seu resultado.':outcome.error||outcome.status,outcome.status==='failed');
    }catch(error){tell(error instanceof Error?error.message:'Falha na confirmação.',true);}finally{setBusy(false);inFlight.current=false;}
  };
  const openModule=(index:number)=>{if(index===7){setEyeOpen(false);setGraphRevision(value=>value+1);return;}if(index===3){setChatOpen(true);return;}setModule(moduleIds[index]);setModuleActivity('IDLE');};
  useEffect(()=>{document.documentElement.dataset.cronosPanel=module?'true':'false';return()=>{delete document.documentElement.dataset.cronosPanel;};},[module]);
  const closeModule=()=>{(iframe.current?.contentWindow as (Window & {cronosPanelClose?:()=>void})|null)?.cronosPanelClose?.();setModule(null);setModuleActivity('IDLE');setGraphRevision(value=>value+1);if(connected)void jsonApi('/status').then(setConfig).catch(()=>{});};
  const activeAlerts=monitor?.alerts||[];
  const fresh=monitor?.checked_at&&Date.now()-Date.parse(monitor.checked_at)<45000;
  const diagnostic=!connected?'DESCONECTADO':!monitor||!fresh?'DIAGNÓSTICO INDISPONÍVEL':activeAlerts.length?`${activeAlerts.length} ALERTA(S)`:'SEM ALERTAS NOS SINAIS MONITORADOS';
  const lastReply=[...messages].reverse().find(message=>message.role==='assistant')?.content;
  return <div className="relative h-screen w-screen overflow-hidden bg-black text-slate-100 flex flex-col select-none">
    <main className="absolute inset-0"><IntegratedNeuralStage state={state} audioLevelSource={audioLevelSource} onOrbClick={handleMic} onMicToggle={handleMic} onModuleClick={openModule}/></main>
    <div className={`memory-slot ${eyeOpen?'small':''}`}><MemorySpiral graph={graph} small={eyeOpen} onSelect={selectNote}/></div>
    <div className={`eye-slot ${eyeOpen?'expanded':''}`}>
      {eyeOpen?<Suspense fallback={<HolographicGlobe onOpen={()=>{}}/>}><WorldMap query={placeQuery} onError={message=>tell(message,true)} onReady={worldReady}/></Suspense>:<HolographicGlobe onOpen={()=>{if(config?.privacy_mode==='local'){tell('O mapa mundial usa serviços externos e está desativado em modo local.',true);return;}voice.prepare();eyeAnnouncement.current=true;setEyeOpen(true);setNote(null);}}/>}
    </div>
    <button className={`reference-mic ${microphone.recording?'recording':''}`} aria-label={microphone.recording?'Parar e transcrever':'Gravar pelo microfone'} onClick={handleMic} disabled={microphone.transcribing||(busy&&!microphone.recording)}><Mic size={16}/></button>
    {notice&&error&&<div className="scene-notice" role="status">{notice}</div>}
    {note&&<section className="note-window" aria-label="Nota Obsidian"><button onClick={()=>setNote(null)} aria-label="Fechar nota"><X size={18}/></button><pre>{note.content}</pre></section>}
    {chatOpen&&<section className="conversation-drawer" aria-label="Conversa com Cronos">
      <div className="drawer-heading"><h2>Conversa / Cronos</h2><button onClick={()=>setChatOpen(false)} aria-label="Fechar conversa"><X size={19}/></button></div>
      <div className="chat-history" role="log" aria-live="polite">{!messages.length&&<p>Faça sua pergunta. A personalidade e a memória vêm do backend.</p>}
        {messages.map((message,index)=><article key={index} className={`chat-message ${message.role}`}><strong>{message.role==='user'?'VOCÊ':'CRONOS'}</strong><p>{message.content}</p></article>)}
        {tools.map((result,index)=><article className="tool-result" key={index}><strong>{result.name} · {result.status}</strong>
          <pre>{JSON.stringify(result.arguments||result.result||result.error,null,2)}</pre>
          {result.status==='pending_confirmation'&&<div className="footer-actions"><button disabled={busy} onClick={()=>approve(result,true)}>Confirmar ação</button><button disabled={busy} onClick={()=>approve(result,false)}>Cancelar</button></div>}
        </article>)}
      </div>
      <form onSubmit={send}><label htmlFor="chat-input">Sua mensagem ou transcrição para revisar</label><textarea id="chat-input" value={draft} onChange={event=>setDraft(event.target.value)} maxLength={16000} rows={3}/>
        <div className="footer-actions"><button type="submit" disabled={busy||microphone.recording||microphone.transcribing||!draft.trim()}><Send size={15}/>Enviar mensagem</button>{lastReply&&<button type="button" onClick={()=>void voice.speak(lastReply)} disabled={!connected}>Ouvir resposta</button>}
          <button type="button" disabled={busy} onClick={()=>{session.current=null;setMessages([]);setTools([]);setDraft('');voice.stop();}}>Nova conversa</button></div>
      </form><p className="small-note">Áudio e texto enviados aos provedores podem consumir cota. Gravação limitada a 60 segundos; ao terminar uma fala, a transcrição é enviada à conversa. Ações sensíveis continuam exigindo confirmação.</p>
    </section>}
    {module&&<section className="module-window" role="dialog" aria-label={moduleNames[moduleIds.indexOf(module)]}>
      <div className="drawer-heading"><h2>{moduleNames[moduleIds.indexOf(module)]}</h2><button onClick={closeModule} aria-label="Fechar módulo"><X size={19}/></button></div>
      <iframe ref={iframe} title={`Módulo ${module}`} src={`/tests#module=${module}`} onLoad={()=>{if(connected)iframe.current?.contentWindow?.postMessage({type:'cronos:connect',token:getToken()},window.location.origin);}}/>
    </section>}

  </div>;
}
