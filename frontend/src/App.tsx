import {UpdateNotice} from './components/UpdateNotice';
/** @license SPDX-License-Identifier: Apache-2.0 */
import React,{Suspense,lazy,useCallback,useEffect,useRef,useState} from 'react';
import {Mic,X,Send,ImagePlus,FileArchive,Code2} from 'lucide-react';
import {IntegratedNeuralStage} from './components/IntegratedNeuralStage';
import {useCronosVoice,useMicrophone} from './hooks/useCronosVoice';
import {api,jsonApi,getToken,onConnection,ApiError,streamChat} from './api';

import {MemorySpiral,MemoryGraph} from './components/MemorySpiral';
import {AnalysisPanel,AnalysisKind} from './components/AnalysisPanel';
import {AnswerCards,HolographicCard,MovableCardFrame} from './components/HolographicCards';
import {localCommand} from './commands';
import {cardRequest,cardDisplayCommand} from './cardRequests';
import {cardPositionCommand,CardLayout} from './cardLayout';
import {stremioCommand,StremioRequest} from './stremioCommands';
const StremioPanel=lazy(()=>import('./components/StremioPanel'));
import {prospectCommand} from './prospectCommands';
import {studioCommand} from './studioCommands';
import type {SiteStudioHandle} from './components/SiteStudio';
const SiteStudio=lazy(()=>import('./components/SiteStudio'));
const ProspectPanel=lazy(()=>import('./components/ProspectPanel'));
import {MusicPlayer,MusicHandle} from './components/MusicPlayer';
const WorldMap=lazy(()=>import('./components/WorldMap'));
const ModulePanel=lazy(()=>import('./panels/ModulePanel'));

const moduleIds=['processing','vision','voice','language','planning','tools','integrations','database','internet','devices','security','monitoring'];
const moduleNames=['Processamento','Visão computacional','Síntese de voz','Entendimento de linguagem','Planejamento','Ferramentas','Integrações','Banco de dados','Internet','Dispositivos','Segurança','Monitoramento'];
type ToolResult={name:string;status:string;approval_id?:string;session_id?:string;arguments?:unknown;result?:unknown;error?:string};

export default function App(){
  const [panelPrefs,setPanelPrefs]=useState<any>(null),[pageHidden,setPageHidden]=useState(document.hidden);
  const prefsRef=useRef(panelPrefs);prefsRef.current=panelPrefs;
  useEffect(()=>{document.documentElement.dataset.cronosEconomy=panelPrefs?.processing_mode==='economy'?'true':'false';},[panelPrefs?.processing_mode]);
  const updatePreferences=useCallback((value:any)=>setPanelPrefs(value),[]);
  useEffect(()=>{const update=()=>setPageHidden(document.hidden);document.addEventListener('visibilitychange',update);return()=>document.removeEventListener('visibilitychange',update);},[]);
  const [updateBusy,setUpdateBusy]=useState(false);
  const [analyses,setAnalyses]=useState<AnalysisKind[]>([]),[analysisTasks,setAnalysisTasks]=useState<AnalysisKind[]>([]);
  const analysisBusy=analysisTasks.length>0;
  const analysisSpeechQueue=useRef<string[]>([]),[analysisSpeechRevision,setAnalysisSpeechRevision]=useState(0);
  const [connected,setConnected]=useState(false),[config,setConfig]=useState<any>(null);
  const [notice,setNotice]=useState(''),[error,setError]=useState(false);
  const [chatOpen,setChatOpen]=useState(false),[module,setModule]=useState<string|null>(null);
  const [draft,setDraft]=useState(''),[busy,setBusy]=useState(false),[tools,setTools]=useState<ToolResult[]>([]);
  const [autoVoice,setAutoVoice]=useState(true),[announceAlerts,setAnnounceAlerts]=useState(false),[monitor,setMonitor]=useState<any>(null);
  const [eyeOpen,setEyeOpen]=useState(false),[placeQuery,setPlaceQuery]=useState(''),[graph,setGraph]=useState<MemoryGraph>({nodes:[],edges:[],total:0}),[graphRevision,setGraphRevision]=useState(0),[note,setNote]=useState<{path:string;content:string}|null>(null);
  const [showSpokenCards,setShowSpokenCards]=useState(false),[cardLayout,setCardLayout]=useState<CardLayout>('orbit');
  const spokenCards=useRef(false);
  const applyCardRequest=(text:string,typed=false)=>{const requested=cardRequest(text);if(requested!==null)spokenCards.current=requested;setShowSpokenCards(requested===false?false:typed||spokenCards.current);};
  const [displayTurn,setDisplayTurn]=useState<{question:string;source:'text'|'transcription';reply:string}|null>(null);
  const lastAnswer=useRef<{question:string;source:'text'|'transcription';reply:string}|null>(null);
  const sendRef=useRef<(text:string,audio?:Blob)=>Promise<void>>(async()=>{});
  const commandRef=useRef<(text:string)=>boolean>(()=>false),eyeAnnouncement=useRef(false);
  const music=useRef<MusicHandle>(null);
  const [stremio,setStremio]=useState<StremioRequest|null>(null);
  const studioHandle=useRef<SiteStudioHandle>(null);
  const [studio,setStudio]=useState<{brief:string;request:number}|null>(null);
  const [prospect,setProspect]=useState<{city:string;category:string;report?:any}|null>(null);
  const pendingAlerts=useRef(new Map<number,any>());
  const chatAbort=useRef<AbortController|null>(null),turnVersion=useRef(0),interrupt=useRef(()=>{}),bargeIn=useRef(()=>{});
  const session=useRef<string|null>(null),iframe=useRef<HTMLIFrameElement|null>(null),cursor=useRef(0),inFlight=useRef(false);
  const activity=useRef<'IDLE'|'LISTENING'|'SPEAKING'>('IDLE');const [moduleActivity,setModuleActivity]=useState(activity.current);
  const recognition=useRef<any>(null),latency=useRef<any>(null);
  const saveLatency=useCallback((value:any)=>{const {started,armed,...metrics}=value;void jsonApi('/panels/latency',metrics).catch(()=>{});},[]);
  const tell=useCallback((message:string,isError=false)=>{setNotice(message);setError(isError);},[]);
  const voice=useCronosVoice({preferences:panelPrefs,streaming:Boolean(config?.fish_pcm_streaming),onSpeechStart:metrics=>{const current=latency.current;if(current?.armed&&metrics?.turn_id===current.turn_id){current.armed=false;saveLatency({...current,...metrics,first_audio_ms:Math.round(performance.now()-current.started)});}},onError:message=>{if(latency.current)latency.current.armed=false;tell(message,true);}});
  const microphone=useMicrophone(useCallback((text,metrics)=>{recognition.current=metrics;if(!text.trim()){tell('Não consegui entender a fala. Tente novamente.',true);return;}if(commandRef.current(text))return;if(prefsRef.current?.called_only&&!/\b(?:cronos|kronos|chronos)\b/i.test(text))return;setChatOpen(false);void sendRef.current(text);},[tell]),useCallback(message=>tell(message,true),[tell]),Boolean(config?.direct_audio_chat)||config?.transcription_provider==='vosk',busy||analysisBusy||updateBusy||voice.isSpeaking||voice.isGenerating||(pageHidden&&panelPrefs?.background_processing===false),panelPrefs,config?.direct_audio_chat?async(audio,metrics)=>{recognition.current=metrics;await sendRef.current('Pergunta por voz',audio);}:undefined,config?.local_voice_interrupt?{active:busy||voice.isSpeaking||voice.isGenerating,onKeyword:()=>bargeIn.current(),wakeOnly:Boolean(panelPrefs?.called_only)}:undefined);
  const state=voice.isSpeaking?'SPEAKING':microphone.capturing?'LISTENING':moduleActivity;
  const audioLevelSource=voice.isSpeaking?voice.audioLevelSource:microphone.audioLevelSource;
  const live=useRef({busy:false,recording:false,transcribing:false,speaking:false,generating:false,module:null as string|null,announce:false,fish:false});
  live.current={busy,recording:microphone.capturing||microphone.starting,transcribing:microphone.transcribing,speaking:voice.isSpeaking,generating:voice.isGenerating,module,announce:announceAlerts,fish:Boolean(config?.fish_configured)};
  const voiceRef=useRef(voice);voiceRef.current=voice;
  useEffect(()=>{
    if(busy||updateBusy||voice.isSpeaking||voice.isGenerating||!analysisSpeechQueue.current.length)return;
    const reply=analysisSpeechQueue.current.shift()!;voiceRef.current.prepare();void voiceRef.current.speak(reply);
  },[analysisSpeechRevision,busy,updateBusy,voice.isSpeaking,voice.isGenerating]);
  useEffect(()=>{if(!announceAlerts)pendingAlerts.current.clear();},[announceAlerts]);

  const connectBackend=useCallback(async()=>{
    setConnected(false);
    try{
      const status=await jsonApi('/status');setConfig(status);try{const panel=await jsonApi('/panels');updatePreferences(panel.preferences);}catch{/* Older backend keeps the existing defaults. */}setConnected(true);if(status.privacy_mode!=='local'&&!status.fish_speech_configured)tell('A voz não está configurada nesta instalação. Feche o Cronos, abra Importar-Voz-Original.bat nesta pasta e selecione o .env da versão em que a voz funcionava. Depois reabra o Cronos.',true);else setNotice('');

      // Compartilha só com a bancada da própria origem, nunca por URL/storage.
      iframe.current?.contentWindow?.postMessage({type:'cronos:connect',token:getToken()},window.location.origin);
    }catch(error){tell('Não consegui iniciar a conexão automática. Feche e abra o Kronos novamente.',true);}
  },[tell]);
  useEffect(()=>{const remove=onConnection(()=>{void connectBackend();});if(getToken())void connectBackend();return remove;},[connectBackend]);

  useEffect(()=>{
    const receive=(event:MessageEvent)=>{
      if(event.origin!==window.location.origin||event.source!==iframe.current?.contentWindow)return;
      if(event.data?.type==='cronos:interrupt'){interrupt.current();return;}
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
  useEffect(()=>{if(!connected)return;const timer=setInterval(()=>{if(prefsRef.current?.auto_index!==false&&!document.hidden&&!live.current.busy&&!live.current.recording&&!live.current.transcribing)setGraphRevision(value=>value+1);},60000);return()=>clearInterval(timer);},[connected]);
  const openAnalysis=(kind:AnalysisKind)=>{if(autoVoice&&config?.fish_speech_configured)voice.prepare();setAnalyses(previous=>previous.includes(kind)?previous:[...previous,kind]);setEyeOpen(false);setModule(null);setChatOpen(false);};
  const runCommand=(text:string)=>{
    if(studio&&studioHandle.current?.handle(text))return true;
    const site=studioCommand(text);if(site){setStudio({brief:site.brief,request:Date.now()});setEyeOpen(false);setModule(null);setChatOpen(false);return true;}
    const attachment=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    if(/\b(?:analis\w*|examin\w*|abr\w*|envi\w*|carreg\w*)\b/.test(attachment)&&/\b(?:imagem|foto|fotografia|arquivo|zip|codigo)\b/.test(attachment)){
      openAnalysis(/\b(?:imagem|foto|fotografia)\b/.test(attachment)?'image':'document');return true;
    }
    const film=stremioCommand(text);if(film){if(config?.privacy_mode==='local'){tell('Stremio online desativado no modo local.',true);return true;}voice.stop();setStremio(film);setModule(null);setChatOpen(false);return true;}
    const leadCommand=prospectCommand(text);if(leadCommand){if(config?.privacy_mode==='local'){tell('Prospecção online desativada no modo local.',true);return true;}voice.stop();setProspect(leadCommand);setModule(null);setChatOpen(false);return true;}
    if(music.current?.handle(text)){setChatOpen(false);voice.stop();return true;}
    const position=cardPositionCommand(text);if(position&&(showSpokenCards||/cards?|cart[õo]es|textos?/i.test(text))){setCardLayout(position);setShowSpokenCards(true);setChatOpen(false);return true;}
    const cards=cardDisplayCommand(text);if(cards!==null){spokenCards.current=cards;setShowSpokenCards(cards);setChatOpen(false);if(cards){if(lastAnswer.current)setDisplayTurn(lastAnswer.current);else if(!displayTurn?.reply)tell('Ainda não há uma resposta para mostrar. Faça uma pergunta e peça a explicação em cards.',true);setModule(null);setEyeOpen(false);setNote(null);}return true;}
    const command=localCommand(text,eyeOpen);if(!command)return false;latency.current=null;
    if(command.type==='presence'){
      if(connected&&config?.fish_speech_configured){voice.prepare();void voice.speak('Estou na escuta.');}
      else tell('A conversa ainda não está conectada ou a voz não está configurada.',true);
      return true;
    }
    if((command.type==='eye'||command.type==='place')&&config?.privacy_mode==='local'){tell('O mapa mundial está desativado em modo local.',true);return true;}
    if(command.type==='eye'){setAnalyses([]);voice.prepare();eyeAnnouncement.current=true;setEyeOpen(true);setChatOpen(false);setModule(null);setNote(null);}
    else if(command.type==='memory'){setEyeOpen(false);setShowSpokenCards(false);setChatOpen(false);setGraphRevision(value=>value+1);}
    else if(command.type==='panel')setChatOpen(true);
    else if(command.type==='place'){setPlaceQuery(command.query);setEyeOpen(true);setChatOpen(false);}
    return true;
  };commandRef.current=runCommand;
  const selectNote=useCallback(async(path:string)=>{if(eyeOpen){setEyeOpen(false);return;}try{setNote(await jsonApi(`/memory/note?path=${encodeURIComponent(path)}`));}catch(error){tell('Não foi possível abrir essa nota.',true);}},[eyeOpen,tell]);
  const worldReady=()=>{if(eyeAnnouncement.current){eyeAnnouncement.current=false;if(config?.fish_speech_configured)void voice.speak('Ampliando sua perspectiva. Olho de Deus aberto.');}};
  interrupt.current=()=>{if(studio)studioHandle.current?.handle('fechar estúdio de sites');analysisSpeechQueue.current=[];setAnalyses([]);spokenCards.current=false;setStremio(null);setProspect(null);music.current?.stop();latency.current=null;turnVersion.current++;chatAbort.current?.abort();voice.stop();microphone.cancelCapture();eyeAnnouncement.current=false;pendingAlerts.current.clear();setBusy(false);inFlight.current=false;setModule(null);setEyeOpen(false);setNote(null);setChatOpen(false);setShowSpokenCards(false);setNotice('');};
  bargeIn.current=()=>{analysisSpeechQueue.current=[];latency.current=null;turnVersion.current++;chatAbort.current?.abort();voice.stop();microphone.cancelCapture();pendingAlerts.current.clear();setBusy(false);inFlight.current=false;setNotice('');};
  useEffect(()=>{const key=(event:KeyboardEvent)=>{if(event.key==='F4'&&!event.altKey&&!event.ctrlKey&&!event.metaKey){event.preventDefault();if(!event.repeat)handlers.current.mic();return;}if(event.key==='Escape'){if(!live.current.speaking&&!live.current.generating&&!live.current.busy&&music.current?.exitView()){event.preventDefault();return;}event.preventDefault();interrupt.current();}};window.addEventListener('keydown',key);return()=>{window.removeEventListener('keydown',key);chatAbort.current?.abort();};},[]);
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),8000);return()=>clearTimeout(timer);},[notice]);

  const autoMic=useRef(false);
  useEffect(()=>{if(connected&&!autoMic.current){autoMic.current=true;if(prefsRef.current?.device_auto_connect!==false)void microphone.start();}},[connected,microphone.start]);
  const handleMic=()=>{
    if(!connected){tell('A conexão automática ainda não está disponível.',true);return;}
    setChatOpen(false);setShowSpokenCards(false);void microphone.toggle();
  };
  const sendText=async(value:string,source:'text'|'transcription'='text',audio?:Blob)=>{
    const text=value.trim();if(!text||inFlight.current)return;if(!audio&&runCommand(text)){setDraft('');return;}
    if(!connected){tell('A conexão automática ainda não está disponível. Feche e abra o Kronos novamente.',true);return;}
    applyCardRequest(text,source==='text');if(!audio)setDisplayTurn({question:text,source,reply:''});setChatOpen(false);
    analysisSpeechQueue.current=[];inFlight.current=true;setBusy(true);voice.stop();if(autoVoice)voice.prepare();setDraft('');tell('Cronos está processando sua mensagem…');
    latency.current={turn_id:crypto.randomUUID(),source:source==='transcription'?'voice':'text',started:performance.now(),armed:false,chat_ms:0,...(source==='transcription'?recognition.current:{})};
    const turnLatency=latency.current;
    const version=++turnVersion.current,controller=new AbortController();chatAbort.current=controller;
    try{
      let question=text;let previewIntro='';let voiced=false,introText='',replyDelivered=false,voiceAllowed=!audio||!prefsRef.current?.called_only;let finishSpeech:((text:string)=>void)|null=null;
      const intro=(reply:string)=>{
        if(version!==turnVersion.current||controller.signal.aborted||!voiceAllowed)return;previewIntro=reply;if(!audio||question!==text)setDisplayTurn({question,source,reply});
        if(version!==turnVersion.current||controller.signal.aborted||!voiceAllowed||voiced||!autoVoice||!config?.fish_speech_configured)return;
        introText=reply;voiced=true;turnLatency.chat_ms=Math.round(performance.now()-turnLatency.started);latency.current=turnLatency;turnLatency.armed=true;saveLatency(turnLatency);const continuation=new Promise<string>(resolve=>{finishSpeech=resolve;});void voice.speak(reply,turnLatency.turn_id,continuation);
      };
      const ready=(reply:string)=>{
        if(version!==turnVersion.current||controller.signal.aborted)return;
        if(!voiceAllowed||replyDelivered)return;replyDelivered=true;
        if(!audio||question!==text)lastAnswer.current={question,source,reply};setDisplayTurn({question,source,reply});setNotice('');
        if(introText){
          if(!reply.startsWith(introText))throw new ApiError('A resposta inicial divergiu da resposta completa.',502);
          const rest=reply.slice(introText.length);
          finishSpeech?.(rest);
        }
        if(autoVoice&&config?.fish_speech_configured&&!voiced){
          voiced=true;turnLatency.chat_ms=Math.round(performance.now()-turnLatency.started);
          latency.current=turnLatency;turnLatency.armed=true;saveLatency(turnLatency);
          void voice.speak(reply,turnLatency.turn_id);
        }
      };
      const result=await streamChat({message:text,session_id:session.current},controller.signal,ready,intro,recognized=>{
        if(version!==turnVersion.current||controller.signal.aborted)return;
        if(stremioCommand(recognized)){controller.abort();runCommand(recognized);return;}if(music.current?.handle(recognized)){controller.abort();voice.stop();setChatOpen(false);return;}if(prefsRef.current?.called_only&&!/\b(?:cronos|kronos|chronos)\b/i.test(recognized)){controller.abort();voice.stop();setDisplayTurn(null);setNotice('');return;}
        voiceAllowed=true;if(audio)turnLatency.recognition_ms=Math.round(performance.now()-turnLatency.started);
        if(runCommand(recognized)){controller.abort();return;}
        applyCardRequest(recognized);question=recognized;setDisplayTurn({question,source,reply:previewIntro});
      },audio);if(version!==turnVersion.current||controller.signal.aborted)return;if(result.ignored){setDisplayTurn(null);setNotice('');return;}if(!voiced)turnLatency.chat_ms=Math.round(performance.now()-turnLatency.started);saveLatency(turnLatency);session.current=result.session_id;lastAnswer.current={question:result.recognized_text||text,source,reply:result.reply};if(result.recognized_text)applyCardRequest(result.recognized_text);setDisplayTurn({question:result.recognized_text||text,source,reply:result.reply});setGraphRevision(value=>value+1);
      setTools(old=>[...old,...(result.tool_results||[])]);
      const filmResult=result.tool_results?.find((r:any)=>r.name==='stremio_search'&&r.status==='completed');if(filmResult?.result){setStremio(filmResult.result);setModule(null);setChatOpen(false);}
      const mediaResult=result.tool_results?.find((r:any)=>r.name==='music_search'&&r.status==='completed');if(mediaResult?.result){music.current?.load(mediaResult.result);}
      const leadResult=result.tool_results?.find((r:any)=>r.name==='prospect_restaurants'&&r.status==='completed');if(leadResult?.result){setProspect({city:leadResult.result.city,category:leadResult.result.category,report:leadResult.result});setModule(null);setChatOpen(false);}
      if(result.warnings?.length)tell(result.warnings.join('\n'),true);else setNotice('');
      if(autoVoice&&config?.fish_speech_configured){ready(result.reply);}
      else if(autoVoice)tell('A resposta está escrita, mas a voz não está configurada. Confira a configuração da voz no arquivo .env.',true);
    }catch(error){
      if(version!==turnVersion.current||controller.signal.aborted)return;
      controller.abort();voice.stop();
      if(error instanceof ApiError&&error.detail?.tool_results){session.current=error.detail.session_id;setTools(old=>[...old,...error.detail.tool_results]);}
      tell(error instanceof Error?error.message:'Não foi possível conversar.',true);
      setDraft(text); // Falha não elimina a pergunta; não repetir ações automaticamente.
    }finally{if(version===turnVersion.current){setBusy(false);inFlight.current=false;chatAbort.current=null;}}
  };
  sendRef.current=(text,audio)=>sendText(text,'transcription',audio);
  const send=(event:React.FormEvent)=>{event.preventDefault();void sendText(draft);};
  const approve=async(result:ToolResult,accepted:boolean)=>{
    if(inFlight.current)return;inFlight.current=true;setBusy(true);
    try{const outcome=await jsonApi(`/tools/approvals/${result.approval_id}`,{session_id:result.session_id||session.current,accepted});
      setTools(old=>old.map(item=>item===result?outcome:item));tell(outcome.status==='completed'?'Solicitação atendida; confira seu resultado.':outcome.error||outcome.status,outcome.status==='failed');
    }catch(error){tell(error instanceof Error?error.message:'Falha na confirmação.',true);}finally{setBusy(false);inFlight.current=false;}
  };
  const openModule=(index:number)=>{setAnalyses([]);setEyeOpen(false);setChatOpen(false);setNote(null);setModule(moduleIds[index]);setModuleActivity('IDLE');};
  useEffect(()=>{document.documentElement.dataset.cronosPanel=module||studio?'true':'false';return()=>{delete document.documentElement.dataset.cronosPanel;};},[module,studio]);
  const closeModule=()=>{(iframe.current?.contentWindow as (Window & {cronosPanelClose?:()=>void})|null)?.cronosPanelClose?.();setModule(null);setModuleActivity('IDLE');setGraphRevision(value=>value+1);if(connected)void jsonApi('/status').then(setConfig).catch(()=>{});};
  const handlers=useRef({mic:handleMic,module:openModule});handlers.current={mic:handleMic,module:openModule};
  const stageMic=useCallback(()=>handlers.current.mic(),[]);
  const stageModule=useCallback((index:number)=>handlers.current.module(index),[]);
  const activeAlerts=monitor?.alerts||[];
  const fresh=monitor?.checked_at&&Date.now()-Date.parse(monitor.checked_at)<45000;
  const diagnostic=!connected?'DESCONECTADO':!monitor||!fresh?'DIAGNÓSTICO INDISPONÍVEL':activeAlerts.length?`${activeAlerts.length} ALERTA(S)`:'SEM ALERTAS NOS SINAIS MONITORADOS';
  return <div className="relative h-screen w-screen overflow-hidden bg-black text-slate-100 flex flex-col select-none">
    <UpdateNotice connected={connected} enabled={panelPrefs?.proactive_suggestions!==false} idle={!studio&&!module&&!chatOpen&&!eyeOpen&&!busy&&!microphone.capturing&&!microphone.transcribing&&!voice.isSpeaking&&!voice.isGenerating} voiceEnabled={autoVoice&&Boolean(config?.fish_speech_configured)} onSpeak={text=>void voice.speak(text)} onBusy={setUpdateBusy}/>

    {!eyeOpen&&<main className={`absolute inset-0 ${module?'scene-under-panel':''}`}><IntegratedNeuralStage state={state} audioLevelSource={audioLevelSource} onOrbClick={stageMic} onMicToggle={stageMic} onModuleClick={stageModule}/></main>}
    {!eyeOpen&&<div className={`memory-slot ${eyeOpen?'small':''}`}><MemorySpiral graph={graph} small={eyeOpen} onSelect={selectNote}/></div>}
    {eyeOpen&&<div className="eye-slot expanded">
      <button className="eye-close" aria-label="Fechar Olho de Deus" title="Fechar Olho de Deus · F4 controla o microfone" onClick={()=>{eyeAnnouncement.current=false;setEyeOpen(false);}}><X size={20}/></button>
      <Suspense fallback={<div className="panel-loading">Abrindo Olho de Deus…</div>}><WorldMap query={placeQuery} onError={message=>tell(message,true)} onReady={worldReady}/></Suspense>
    </div>}
    {!eyeOpen&&!module&&<><button className="reference-attachment" aria-label="Analisar imagem" title="Analisar imagem" onClick={()=>openAnalysis('image')}><ImagePlus size={16}/></button><button className="reference-attachment files" aria-label="Analisar ZIP ou código" title="Analisar ZIP ou código" onClick={()=>openAnalysis('document')}><FileArchive size={16}/></button></>}
    {!eyeOpen&&!module&&analyses.map(kind=><AnalysisPanel key={kind} kind={kind} onClose={()=>setAnalyses(previous=>previous.filter(item=>item!==kind))} onBusy={active=>setAnalysisTasks(previous=>active?[...previous.filter(item=>item!==kind),kind]:previous.filter(item=>item!==kind))} onResult={reply=>{lastAnswer.current={question:kind==='image'?'Análise de imagem':'Análise de arquivo',source:'text',reply};if(autoVoice&&config?.fish_speech_configured){analysisSpeechQueue.current.push(reply);setAnalysisSpeechRevision(value=>value+1);}}}/>)}
    <button className={`reference-mic ${microphone.starting?'starting':microphone.transcribing?'transcribing':busy?'thinking':voice.isGenerating?'generating':voice.isSpeaking?'speaking':microphone.recording?'recording':''}`} aria-pressed={microphone.recording} title={microphone.starting?'Abrindo microfone':microphone.transcribing?'Transcrevendo':busy?'Aguardando Gemini':voice.isGenerating?'Preparando voz':voice.isSpeaking?'Falando — diga Cronos para interromper':microphone.recording?'Microfone ligado':'Microfone desligado'} aria-label={microphone.recording?'Desligar microfone':'Ligar microfone'} onClick={handleMic} ><Mic size={16}/></button>
    {!studio&&!eyeOpen&&!module&&<button className="studio-entry" onClick={()=>setStudio({brief:'',request:Date.now()})}><Code2 size={15}/>ESTÚDIO DE SITES</button>}
    {studio&&<Suspense fallback={<div className="panel-loading">Abrindo Estúdio de Sites…</div>}><SiteStudio ref={studioHandle} initial={studio} onClose={()=>setStudio(null)} onSpeak={text=>{if(autoVoice&&config?.fish_speech_configured){analysisSpeechQueue.current.push(text);setAnalysisSpeechRevision(v=>v+1);}}}/></Suspense>}
    {stremio&&<Suspense fallback={<div className="panel-loading">Abrindo Stremio…</div>}><StremioPanel key={JSON.stringify(stremio)} initial={stremio} onClose={()=>setStremio(null)}/></Suspense>}
    {prospect&&<Suspense fallback={<div className="panel-loading">Abrindo prospecção…</div>}><ProspectPanel key={prospect.city+'|'+prospect.category+'|'+(prospect.report?.id||'')} initial={prospect} onClose={()=>setProspect(null)} onAsk={text=>{setProspect(null);void sendText(text);}}/></Suspense>}
    <MusicPlayer ref={music} onTalk={async()=>{voice.stop();microphone.cancelCapture();await microphone.start();}} local={config?.privacy_mode==='local'} onError={message=>tell(message,true)}/>
    {notice&&error&&<div className="scene-notice" role="status">{notice}</div>}
    {note&&<section className="note-window" aria-label="Nota Obsidian"><button onClick={()=>setNote(null)} aria-label="Fechar nota"><X size={18}/></button><pre>{note.content}</pre></section>}
    {displayTurn?.reply&&showSpokenCards&&!chatOpen&&!module&&!eyeOpen&&<AnswerCards reply={displayTurn.reply} layout={cardLayout}/>}
    {displayTurn&&displayTurn.source==='text'&&showSpokenCards&&!chatOpen&&!module&&!eyeOpen&&<MovableCardFrame className="spoken-question"><HolographicCard title="PERGUNTA" variant="ribbon" movable><p className="holo-text">{displayTurn.question}</p></HolographicCard></MovableCardFrame>}
    {chatOpen&&<section className="card-composer" aria-label="Escrever para Kronos"><HolographicCard title="PERGUNTA" variant="layered">
      <button className="holo-close" onClick={()=>setChatOpen(false)} aria-label="Fechar conversa"><X size={17}/></button>
      <form onSubmit={send}><label htmlFor="chat-input">O que você quer perguntar?</label><textarea id="chat-input" value={draft} onChange={event=>{setDraft(event.target.value);event.target.style.height='auto';event.target.style.height=Math.min(260,event.target.scrollHeight)+'px';}} maxLength={16000} rows={2}/>
        <div className="footer-actions"><button type="submit" disabled={busy||microphone.transcribing||!draft.trim()}><Send size={15}/>Enviar mensagem</button></div>
      </form>
    </HolographicCard></section>}
    {tools.some(result=>result.status==='pending_confirmation')&&<section className="holo-tool-deck" aria-label="Ações pendentes">{tools.filter(result=>result.status==='pending_confirmation').map((result,index)=><HolographicCard key={index} title={result.name} variant="layered"><pre>{JSON.stringify(result.arguments,null,2)}</pre><div className="footer-actions"><button disabled={busy} onClick={()=>approve(result,true)}>Confirmar ação</button><button disabled={busy} onClick={()=>approve(result,false)}>Cancelar</button></div></HolographicCard>)}</section>}
    {module&&<Suspense fallback={<div className="panel-loading">Abrindo painel…</div>}><ModulePanel id={module} onSelect={openModule} onClose={closeModule} graph={graph} onSync={()=>setGraphRevision(v=>v+1)} onNote={path=>{closeModule();void selectNote(path);}} preferences={panelPrefs} onPreferences={updatePreferences} voice={voice} microphone={microphone} lastTurn={displayTurn} busy={busy} onComposer={()=>{closeModule();setChatOpen(true);}} onEye={()=>{closeModule();voice.prepare();eyeAnnouncement.current=true;setEyeOpen(true);}} onAsk={text=>void sendText(text)}/></Suspense>}


  </div>;
}
