import {UpdateNotice} from './components/UpdateNotice';
/** @license SPDX-License-Identifier: Apache-2.0 */
import React,{Suspense,lazy,useCallback,useEffect,useRef,useState} from 'react';
import {Mic,X,Send,ImagePlus,FileArchive,MonitorUp,BookOpen} from 'lucide-react';
import {IntegratedNeuralStage} from './components/IntegratedNeuralStage';
import {useCronosVoice,useMicrophone} from './hooks/useCronosVoice';
import {api,jsonApi,getToken,onConnection,ApiError,streamChat} from './api';

import {MemorySpiral,MemoryGraph} from './components/MemorySpiral';
import {ScreenMonitor,type ScreenMonitorHandle} from './components/ScreenMonitor';
import {screenCommand} from './screenCommands';
import {AnalysisPanel,AnalysisKind} from './components/AnalysisPanel';
import {AnswerCards,HolographicCard,MovableCardFrame} from './components/HolographicCards';
import {localCommand} from './commands';
import {cardRequest,cardDisplayCommand} from './cardRequests';
import {cardPositionCommand,CardLayout} from './cardLayout';
import {isStudyQuestion,studyPanelTitle} from './studyIntent';
import {stremioCommand,StremioRequest} from './stremioCommands';
const StremioPanel=lazy(()=>import('./components/StremioPanel'));
import {prospectCommand} from './prospectCommands';
import {studioCommand} from './studioCommands';
import type {SiteStudioHandle} from './components/SiteStudio';
const SiteStudio=lazy(()=>import('./components/SiteStudio'));
const ProspectPanel=lazy(()=>import('./components/ProspectPanel'));
import {MusicPlayer,MusicHandle,type MusicWindow} from './components/MusicPlayer';
import {WindowSurface,WindowShelf,MinimizeWindow,type ShelfItem} from './components/WindowShelf';
const WorldMap=lazy(()=>import('./components/WorldMap'));
const ModulePanel=lazy(()=>import('./panels/ModulePanel'));
const StudyWorkspace=lazy(()=>import('./components/StudyWorkspace'));
import {StudyExplanationPanel,type StudyPanelItem} from './components/StudyExplanationPanel';
import {HandControl} from './components/HandControl';

const moduleIds=['processing','vision','voice','language','planning','tools','integrations','database','internet','devices','security','monitoring'];
const moduleNames=['Processamento','Visão computacional','Síntese de voz','Entendimento de linguagem','Planejamento','Ferramentas','Integrações','Banco de dados','Internet','Dispositivos','Segurança','Monitoramento'];
type ToolResult={name:string;status:string;approval_id?:string;session_id?:string;arguments?:unknown;result?:unknown;error?:string};
function studyReferences(items:ToolResult[]=[]){
  const output:Array<{title:string;url:string;excerpt?:string}>=[];
  const add=(item:any)=>{const url=typeof item?.url==='string'?item.url:typeof item?.href==='string'?item.href:'';if(!/^https?:\/\//i.test(url))return;try{const parsed=new URL(url);if(!['http:','https:'].includes(parsed.protocol)||parsed.username||parsed.password)return;output.push({title:String(item.title||parsed.hostname).slice(0,180),url:parsed.href,excerpt:String(item.body||item.excerpt||'').slice(0,400)});}catch{/* Ignore malformed source URLs. */}};
  for(const event of items){if(!['web_search','web_news','browser_search'].includes(event.name)||event.status!=='completed')continue;const data:any=event.result;if(Array.isArray(data))data.forEach(add);else if(Array.isArray(data?.articles))data.articles.forEach(add);else if(Array.isArray(data?.results))data.results.forEach(add);}
  return [...new Map(output.map(item=>[item.url,item])).values()].slice(0,6);
}

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
  const applyCardRequest=(text:string,_typed=false)=>{const requested=cardRequest(text);spokenCards.current=requested===true;setShowSpokenCards(requested===true);};
  const [displayTurn,setDisplayTurn]=useState<{question:string;source:'text'|'transcription';reply:string}|null>(null);
  const lastAnswer=useRef<{question:string;source:'text'|'transcription';reply:string}|null>(null);
  const sendRef=useRef<(text:string,audio?:Blob)=>Promise<void>>(async()=>{});
  const commandRef=useRef<(text:string)=>boolean>(()=>false),eyeAnnouncement=useRef(false);
  const screenMonitor=useRef<ScreenMonitorHandle>(null);
  const music=useRef<MusicHandle>(null);
  const [musicPlaying,setMusicPlaying]=useState(false),[filmPlaying,setFilmPlaying]=useState(false);
  const mediaPlaying=musicPlaying||filmPlaying;
  const [stremio,setStremio]=useState<StremioRequest|null>(null);
  const studioHandle=useRef<SiteStudioHandle>(null);
  const [studio,setStudio]=useState<{brief:string;request:number}|null>(null);
  const [studyOpen,setStudyOpen]=useState(false);
  const [focusedStudyPanel,setFocusedStudyPanel]=useState<string|null>(null);
  const [studyPanels,setStudyPanels]=useState<StudyPanelItem[]>([]);
  const studyPanelsRef=useRef<StudyPanelItem[]>([]);
  const activeStudyPanel=useRef<string|null>(null),expectedStudyTurn=useRef<string|null>(null);
  const changeStudyPanels=(update:(items:StudyPanelItem[])=>StudyPanelItem[])=>{const next=update(studyPanelsRef.current);studyPanelsRef.current=next;setStudyPanels(next);};
  const addStudyPanel=(question:string,reply='')=>{
    const current=studyPanelsRef.current;
    const visible=current.filter(panel=>!panel.minimized);
    let available=[0,1,2].find(slot=>!visible.some(panel=>panel.slot===slot));
    let minimized=false;
    if(available===undefined){
      const replaceable=visible.filter(panel=>!panel.locked).sort((a,b)=>a.createdAt-b.createdAt)[0];
      if(replaceable){available=replaceable.slot;changeStudyPanels(items=>items.map(panel=>panel.id===replaceable.id?{...panel,minimized:true}:panel));}
      else {minimized=true;available=0;tell('Os três painéis visíveis estão fixados; deixei a nova explicação minimizada para preservar todos.',false);}
    }
    const slot=available??0;
    const id=crypto.randomUUID();
    const item:StudyPanelItem={id,title:studyPanelTitle(question,reply),reply,slot,locked:false,minimized,createdAt:Date.now()};
    activeStudyPanel.current=id;
    setFocusedStudyPanel(id);
    changeStudyPanels(items=>[...items,item].sort((a,b)=>a.slot-b.slot));
    return id;
  };
  const updateStudyPanel=(id:string,question:string,reply:string)=>changeStudyPanels(items=>items.map(panel=>panel.id===id?{...panel,title:studyPanelTitle(question,reply),reply}:panel));
  const focusStudyPanel=(id:string|null)=>{activeStudyPanel.current=id;setFocusedStudyPanel(id);};
  const closeStudyPanel=(id:string)=>{const remaining=studyPanelsRef.current.filter(panel=>panel.id!==id&&!panel.minimized);if(activeStudyPanel.current===id)focusStudyPanel(remaining.at(-1)?.id||null);changeStudyPanels(items=>items.filter(panel=>panel.id!==id));};
  const minimizeStudyPanel=(id:string)=>{const remaining=studyPanelsRef.current.filter(panel=>panel.id!==id&&!panel.minimized);if(activeStudyPanel.current===id)focusStudyPanel(remaining.at(-1)?.id||null);changeStudyPanels(items=>items.map(panel=>panel.id===id?{...panel,minimized:true}:panel));};
  const restoreStudyPanel=(id:string)=>{
    const current=studyPanelsRef.current;
    const target=current.find(panel=>panel.id===id);if(!target)return;
    const visible=current.filter(panel=>!panel.minimized);
    let slot=target.slot;
    if(visible.length>=3){
      const replaceable=visible.filter(panel=>!panel.locked&&panel.id!==id).sort((a,b)=>a.createdAt-b.createdAt)[0];
      if(!replaceable){tell('Os três painéis visíveis estão fixados. Minimize ou desafixe um para restaurar este.',true);return;}
      slot=replaceable.slot;
      changeStudyPanels(items=>items.map(panel=>panel.id===replaceable.id?{...panel,minimized:true}:panel));
    }else if(visible.some(panel=>panel.slot===slot)){
      slot=[0,1,2].find(value=>!visible.some(panel=>panel.slot===value))??slot;
    }
    changeStudyPanels(items=>items.map(panel=>panel.id===id?{...panel,slot,minimized:false}:panel));
    focusStudyPanel(id);
  };
  const [prospect,setProspect]=useState<{city:string;category:string;report?:any}|null>(null);
  const [minimizedWindows,setMinimizedWindows]=useState<string[]>([]);
  const [musicWindow,setMusicWindow]=useState<MusicWindow>({visible:false,minimized:false,title:'Música',state:'Em espera'});
  const [studioWindow,setStudioWindow]=useState({title:'Estúdio de Sites',detail:'Pronto para continuar'});
  const minimizeWindow=(id:string)=>setMinimizedWindows(previous=>previous.includes(id)?previous:[...previous,id]);
  const restoreWindow=(id:string)=>setMinimizedWindows(previous=>{const next=previous.filter(item=>item!==id);for(const other of ['studio','module','eye','study'])if(id!==other&&(other==='studio'?Boolean(studio):other==='module'?Boolean(module):other==='eye'?eyeOpen:studyOpen)&&!next.includes(other))next.push(other);return next;});
  const studioActive=Boolean(studio&&!minimizedWindows.includes('studio'));
  const moduleActive=Boolean(module&&!minimizedWindows.includes('module'));
  const eyeActive=eyeOpen&&!minimizedWindows.includes('eye');
  const studyActive=studyOpen&&!minimizedWindows.includes('study');

  const pendingAlerts=useRef(new Map<number,any>());
  const chatAbort=useRef<AbortController|null>(null),turnVersion=useRef(0),interrupt=useRef(()=>{}),bargeIn=useRef(()=>{});
  const session=useRef<string|null>(null),iframe=useRef<HTMLIFrameElement|null>(null),cursor=useRef(0),inFlight=useRef(false);
  const activity=useRef<'IDLE'|'LISTENING'|'SPEAKING'>('IDLE');const [moduleActivity,setModuleActivity]=useState(activity.current);
  const recognition=useRef<any>(null),latency=useRef<any>(null);
  const saveLatency=useCallback((value:any)=>{const {started,armed,...metrics}=value;void jsonApi('/panels/latency',metrics).catch(()=>{});},[]);
  const tell=useCallback((message:string,isError=false)=>{setNotice(message);setError(isError);},[]);
  const voice=useCronosVoice({preferences:panelPrefs,streaming:Boolean(config?.fish_pcm_streaming),onSpeechStart:metrics=>{const current=latency.current;if(current?.armed&&metrics?.turn_id===current.turn_id){current.armed=false;saveLatency({...current,...metrics,first_audio_ms:Math.round(performance.now()-current.started)});}},onSpeechChunk:(spoken,_index,turnId)=>{if(!turnId||turnId!==expectedStudyTurn.current)return;const panelId=activeStudyPanel.current;if(panelId)changeStudyPanels(items=>items.map(panel=>panel.id===panelId?{...panel,spokenChunk:spoken}:panel));},onError:message=>{if(latency.current)latency.current.armed=false;tell(message,true);}});
  const microphone=useMicrophone(useCallback((text,metrics)=>{recognition.current=metrics;if(!text.trim()){tell('Não consegui entender a fala. Tente novamente.',true);return;}if(commandRef.current(text))return;if(prefsRef.current?.called_only&&!/\b(?:cronos|kronos|chronos)\b/i.test(text))return;setChatOpen(false);void sendRef.current(text);},[tell]),useCallback(message=>tell(message,true),[tell]),Boolean(config?.direct_audio_chat)||config?.transcription_provider==='vosk',busy||analysisBusy||updateBusy||mediaPlaying||voice.isSpeaking||voice.isGenerating||(pageHidden&&panelPrefs?.background_processing===false),panelPrefs,config?.direct_audio_chat?async(audio,metrics)=>{recognition.current=metrics;await sendRef.current('Pergunta por voz',audio);}:undefined,config?.local_voice_interrupt?{active:mediaPlaying||busy||voice.isSpeaking||voice.isGenerating,onKeyword:()=>bargeIn.current(),wakeOnly:Boolean(panelPrefs?.called_only)}:undefined);
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
  const openAnalysis=(kind:AnalysisKind)=>{restoreWindow('analysis:'+kind);if(autoVoice&&config?.fish_speech_configured)voice.prepare();setAnalyses(previous=>previous.includes(kind)?previous:[...previous,kind]);setEyeOpen(false);setModule(null);setChatOpen(false);};
  const runCommand=(text:string)=>{
    const normalizedCommand=text.trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/^(?:kronos|cronos)[,\s:]+/i,'').replace(/[.!?]+$/,'').toLowerCase().replace(/\s+/g,' ');
    if(/^(?:(?:abrir|abre|abra|mostrar|mostre|entrar em|ir para|vamos para|vamos pra|quero abrir)\s+)?(?:[oa]\s+)?(?:area de\s+)?(?:estudo(?:s)?|caderno de estudos|ambiente de estudos|sala de estudos)(?:\s+(?:agora|por favor))?$/.test(normalizedCommand)){
      restoreWindow('study');setStudyOpen(true);setEyeOpen(false);setModule(null);setChatOpen(false);setNote(null);return true;
    }
    if(/^(?:fechar|fecha|feche|ocultar|esconder)\s+(?:todos os\s+)?paineis? de estud(?:o|os)$/.test(normalizedCommand)){
      const closeAll=/\btodos os\b/.test(normalizedCommand);
      changeStudyPanels(items=>closeAll?[]:items.filter(panel=>panel.locked));
      return true;
    }
    if(/^(?:minimizar|minimize)\s+(?:todos os\s+)?paineis? de estud(?:o|os)$/.test(normalizedCommand)){
      changeStudyPanels(items=>items.map(panel=>({...panel,minimized:true})));return true;
    }
    const screenAction=screenCommand(text);if(screenAction){screenMonitor.current?.[screenAction]();return true;}
    if(studioActive&&studioHandle.current?.handle(text))return true;
    const site=studioCommand(text);if(site){restoreWindow('studio');if(!studio||site.brief)setStudio({brief:site.brief,request:Date.now()});setEyeOpen(false);setModule(null);setChatOpen(false);return true;}
    const attachment=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    if(/\b(?:analis\w*|examin\w*|abr\w*|envi\w*|carreg\w*)\b/.test(attachment)&&/\b(?:imagem|foto|fotografia|arquivo|zip|codigo)\b/.test(attachment)){
      openAnalysis(/\b(?:imagem|foto|fotografia)\b/.test(attachment)?'image':'document');return true;
    }
    const film=stremioCommand(text);if(film){if(config?.privacy_mode==='local'){tell('Stremio online desativado no modo local.',true);return true;}voice.stop();restoreWindow('stremio');setStremio(film);setModule(null);setChatOpen(false);return true;}
    const leadCommand=prospectCommand(text);if(leadCommand){if(config?.privacy_mode==='local'){tell('Prospecção online desativada no modo local.',true);return true;}voice.stop();restoreWindow('prospect');setProspect(leadCommand);setModule(null);setChatOpen(false);return true;}
    if(music.current?.handle(text)){if(studioActive)minimizeWindow('studio');setChatOpen(false);voice.stop();return true;}
    const position=cardPositionCommand(text);if(position&&(showSpokenCards||/cards?|cart[õo]es|textos?/i.test(text))){setCardLayout(position);setShowSpokenCards(true);setChatOpen(false);return true;}
    const cards=cardDisplayCommand(text);if(cards!==null){spokenCards.current=cards;setShowSpokenCards(cards);setChatOpen(false);if(cards){if(lastAnswer.current)setDisplayTurn(lastAnswer.current);else if(!displayTurn?.reply)tell('Ainda não há uma resposta para mostrar. Faça uma pergunta e peça a explicação em cards.',true);setModule(null);setEyeOpen(false);setNote(null);}return true;}
    const command=localCommand(text,eyeOpen);if(!command)return false;latency.current=null;
    if(command.type==='presence'){
      if(connected&&config?.fish_speech_configured){voice.prepare();void voice.speak('Estou na escuta.');}
      else tell('A conversa ainda não está conectada ou a voz não está configurada.',true);
      return true;
    }
    if((command.type==='eye'||command.type==='place')&&config?.privacy_mode==='local'){tell('O mapa mundial está desativado em modo local.',true);return true;}
    if(command.type==='eye'){restoreWindow('eye');setAnalyses([]);voice.prepare();eyeAnnouncement.current=true;setEyeOpen(true);setChatOpen(false);setModule(null);setNote(null);}
    else if(command.type==='memory'){setEyeOpen(false);setShowSpokenCards(false);setChatOpen(false);setGraphRevision(value=>value+1);}
    else if(command.type==='panel'){restoreWindow('chat');setChatOpen(true);}
    else if(command.type==='place'){restoreWindow('eye');setPlaceQuery(command.query);setEyeOpen(true);setChatOpen(false);}
    return true;
  };commandRef.current=runCommand;
  const selectNote=useCallback(async(path:string)=>{if(eyeOpen){setEyeOpen(false);return;}restoreWindow('note');try{setNote(await jsonApi(`/memory/note?path=${encodeURIComponent(path)}`));}catch(error){tell('Não foi possível abrir essa nota.',true);}},[eyeOpen,tell]);
  const worldReady=()=>{if(eyeAnnouncement.current){eyeAnnouncement.current=false;if(config?.fish_speech_configured)void voice.speak('Ampliando sua perspectiva. Olho de Deus aberto.');}};
  interrupt.current=()=>{if(studioActive)studioHandle.current?.handle('fechar estúdio de sites');analysisSpeechQueue.current=[];setAnalyses([]);spokenCards.current=false;setStremio(null);setProspect(null);music.current?.stop();latency.current=null;turnVersion.current++;chatAbort.current?.abort();voice.stop();microphone.cancelCapture();eyeAnnouncement.current=false;pendingAlerts.current.clear();setBusy(false);inFlight.current=false;setModule(null);setEyeOpen(false);setStudyOpen(false);setNote(null);setChatOpen(false);setShowSpokenCards(false);setNotice('');};
  bargeIn.current=()=>{music.current?.pause();window.dispatchEvent(new Event('cronos:listen'));analysisSpeechQueue.current=[];latency.current=null;turnVersion.current++;chatAbort.current?.abort();voice.stop();microphone.cancelCapture();pendingAlerts.current.clear();setBusy(false);inFlight.current=false;setNotice('');};
  useEffect(()=>{const key=(event:KeyboardEvent)=>{if(event.key==='F4'&&!event.altKey&&!event.ctrlKey&&!event.metaKey){event.preventDefault();if(!event.repeat)handlers.current.f4();return;}if(event.key==='Escape'){if(!live.current.speaking&&!live.current.generating&&!live.current.busy&&music.current?.exitView()){event.preventDefault();return;}event.preventDefault();interrupt.current();}};window.addEventListener('keydown',key);return()=>{window.removeEventListener('keydown',key);chatAbort.current?.abort();};},[]);
  useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),8000);return()=>clearTimeout(timer);},[notice]);

  const autoMic=useRef(false);
  useEffect(()=>{if(connected&&!autoMic.current){autoMic.current=true;if(prefsRef.current?.device_auto_connect!==false)void microphone.start();}},[connected,microphone.start]);
  const handleMic=()=>{
    if(!connected){tell('A conexão automática ainda não está disponível.',true);return;}
    setChatOpen(false);setShowSpokenCards(false);
    if(mediaPlaying){music.current?.pause();window.dispatchEvent(new Event('cronos:listen'));microphone.cancelCapture();void microphone.start();return;}
    if(!microphone.recording){music.current?.pause();window.dispatchEvent(new Event('cronos:listen'));}
    void microphone.toggle();
  };
  const sendText=async(value:string,source:'text'|'transcription'='text',audio?:Blob)=>{
    const text=value.trim();if(!text||inFlight.current)return;if(!audio&&runCommand(text)){setDraft('');return;}
    if(!connected){tell('A conexão automática ainda não está disponível. Feche e abra o Kronos novamente.',true);return;}
    let showStudyText=isStudyQuestion(text);if(!showStudyText)focusStudyPanel(null);let studyPanelId:string|null=showStudyText?addStudyPanel(text):null;
    applyCardRequest(text,source==='text');if(!audio)setDisplayTurn({question:text,source,reply:''});setChatOpen(false);
    analysisSpeechQueue.current=[];inFlight.current=true;setBusy(true);voice.stop();if(autoVoice)voice.prepare();setDraft('');tell('Cronos está processando sua mensagem…');
    latency.current={turn_id:crypto.randomUUID(),source:source==='transcription'?'voice':'text',started:performance.now(),armed:false,chat_ms:0,...(source==='transcription'?recognition.current:{})};
    const turnLatency=latency.current;
    expectedStudyTurn.current=turnLatency.turn_id;
    const version=++turnVersion.current,controller=new AbortController();chatAbort.current=controller;
    try{
      let question=text;let previewIntro='';let voiced=false,introText='',replyDelivered=false,voiceAllowed=!audio;let finishSpeech:((text:string)=>void)|null=null;
      const intro=(reply:string)=>{
        if(version!==turnVersion.current||controller.signal.aborted||!voiceAllowed)return;previewIntro=reply;if(!audio||question!==text)setDisplayTurn({question,source,reply});if(showStudyText){if(!studyPanelId)studyPanelId=addStudyPanel(question,reply);if(studyPanelId)updateStudyPanel(studyPanelId,question,reply);}
        if(version!==turnVersion.current||controller.signal.aborted||!voiceAllowed||voiced||!autoVoice||!config?.fish_speech_configured)return;
        introText=reply;voiced=true;turnLatency.chat_ms=Math.round(performance.now()-turnLatency.started);latency.current=turnLatency;turnLatency.armed=true;saveLatency(turnLatency);const continuation=new Promise<string>(resolve=>{finishSpeech=resolve;});void voice.speak(reply,turnLatency.turn_id,continuation);
      };
      const ready=(reply:string)=>{
        if(version!==turnVersion.current||controller.signal.aborted)return;
        if(!voiceAllowed||replyDelivered)return;replyDelivered=true;if(showStudyText){if(!studyPanelId)studyPanelId=addStudyPanel(question,reply);if(studyPanelId)updateStudyPanel(studyPanelId,question,reply);}
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
        // Do not abort here: the backend returns an explicit ignored result so
        // the UI can explain the wake-word preference instead of leaving silence.
        if(prefsRef.current?.called_only&&!/\b(?:cronos|kronos|chronos)\b/i.test(recognized))return;
        if(stremioCommand(recognized)){controller.abort();runCommand(recognized);return;}if(music.current?.handle(recognized)){controller.abort();voice.stop();setChatOpen(false);return;}
        voiceAllowed=true;if(audio)turnLatency.recognition_ms=Math.round(performance.now()-turnLatency.started);
        if(runCommand(recognized)){controller.abort();return;}
        applyCardRequest(recognized);question=recognized;showStudyText=isStudyQuestion(recognized);if(showStudyText){if(!studyPanelId)studyPanelId=addStudyPanel(question,previewIntro);if(studyPanelId)updateStudyPanel(studyPanelId,question,previewIntro);}else if(studyPanelId&&!studyPanelsRef.current.find(panel=>panel.id===studyPanelId)?.reply){closeStudyPanel(studyPanelId);studyPanelId=null;}setDisplayTurn({question,source,reply:previewIntro});
      },audio);if(version!==turnVersion.current||controller.signal.aborted)return;if(result.ignored){const heard=result.recognized_text||text;if(studyPanelId&&!studyPanelsRef.current.find(panel=>panel.id===studyPanelId)?.reply)closeStudyPanel(studyPanelId);setDisplayTurn({question:heard,source,reply:''});tell(prefsRef.current?.called_only?'Ouvi sua fala, mas “Responder só após ser chamado” está ligado. Comece a frase com “Cronos” ou desligue essa opção no painel de Entendimento de Linguagem.':'Ouvi a fala, mas não consegui concluir a resposta. Tente novamente.',true);return;}if(audio&&!voiceAllowed&&result.recognized_text){if(runCommand(result.recognized_text))return;voiceAllowed=true;}if(!voiced)turnLatency.chat_ms=Math.round(performance.now()-turnLatency.started);saveLatency(turnLatency);session.current=result.session_id;const finalQuestion=result.recognized_text||text;showStudyText=isStudyQuestion(finalQuestion);if(showStudyText){if(!studyPanelId)studyPanelId=addStudyPanel(finalQuestion,result.reply);if(studyPanelId)updateStudyPanel(studyPanelId,finalQuestion,result.reply);}else if(studyPanelId&&!studyPanelsRef.current.find(panel=>panel.id===studyPanelId)?.reply){closeStudyPanel(studyPanelId);studyPanelId=null;}lastAnswer.current={question:finalQuestion,source,reply:result.reply};if(result.recognized_text)applyCardRequest(result.recognized_text);setDisplayTurn({question:finalQuestion,source,reply:result.reply});setGraphRevision(value=>value+1);
      const turnTools:ToolResult[]=result.tool_results||[];setTools(old=>[...old,...turnTools]);
      if(showStudyText&&studyPanelId){const references=studyReferences(turnTools);if(references.length)changeStudyPanels(items=>items.map(panel=>panel.id===studyPanelId?{...panel,references}:panel));}
      const filmResult=result.tool_results?.find((r:any)=>r.name==='stremio_search'&&r.status==='completed');if(filmResult?.result){setStremio(filmResult.result);setModule(null);setChatOpen(false);}
      const mediaResult=result.tool_results?.find((r:any)=>r.name==='music_search'&&r.status==='completed');if(mediaResult?.result){music.current?.load(mediaResult.result);}
      const leadResult=result.tool_results?.find((r:any)=>r.name==='prospect_restaurants'&&r.status==='completed');if(leadResult?.result){setProspect({city:leadResult.result.city,category:leadResult.result.category,report:leadResult.result});setModule(null);setChatOpen(false);}
      if(result.warnings?.length)tell(result.warnings.join('\n'),true);
      else if(result.fallback_used)tell(`A integração principal não respondeu. Esta resposta veio da reserva ${result.provider_used}.`,false);
      else setNotice('');
      if(autoVoice&&config?.fish_speech_configured){ready(result.reply);}
      else if(autoVoice)tell('A resposta está escrita, mas a voz não está configurada. Confira a configuração da voz no arquivo .env.',true);
    }catch(error){
      if(version!==turnVersion.current||controller.signal.aborted)return;
      controller.abort();voice.stop();
      if(studyPanelId&&!studyPanelsRef.current.find(panel=>panel.id===studyPanelId)?.reply)closeStudyPanel(studyPanelId);
      if(error instanceof ApiError&&error.detail?.tool_results){session.current=error.detail.session_id;setTools(old=>[...old,...error.detail.tool_results]);}
      tell(`${error instanceof Error?error.message:'Não foi possível conversar.'}\nSua mensagem ficou guardada no campo para o senhor tentar novamente sem repetir.`,true);
      setDraft(text); // A pergunta permanece disponível; não repetir ações automaticamente.
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
  const openModule=(index:number)=>{restoreWindow('module');setAnalyses(previous=>previous.filter(kind=>minimizedWindows.includes('analysis:'+kind)));setEyeOpen(false);setChatOpen(false);setNote(null);setModule(moduleIds[index]);setModuleActivity('IDLE');};
  useEffect(()=>{document.documentElement.dataset.cronosPanel=moduleActive||studioActive?'true':'false';return()=>{delete document.documentElement.dataset.cronosPanel;};},[moduleActive,studioActive]);
  const closeModule=()=>{(iframe.current?.contentWindow as (Window & {cronosPanelClose?:()=>void})|null)?.cronosPanelClose?.();setModule(null);setModuleActivity('IDLE');setGraphRevision(value=>value+1);if(connected)void jsonApi('/status').then(setConfig).catch(()=>{});};
  const handlers=useRef({mic:handleMic,f4:()=>{},module:openModule});handlers.current={mic:handleMic,f4:()=>{if(microphone.recording)microphone.stop();else handleMic();},module:openModule};
  const stageMic=useCallback(()=>handlers.current.mic(),[]);
  const stageModule=useCallback((index:number)=>handlers.current.module(index),[]);
  const activeAlerts=monitor?.alerts||[];
  const fresh=monitor?.checked_at&&Date.now()-Date.parse(monitor.checked_at)<45000;
  const diagnostic=!connected?'DESCONECTADO':!monitor||!fresh?'DIAGNÓSTICO INDISPONÍVEL':activeAlerts.length?`${activeAlerts.length} ALERTA(S)`:'SEM ALERTAS NOS SINAIS MONITORADOS';
  const shelfItems:ShelfItem[]=[];
  const addWindow=(id:string,title:string,detail?:string)=>{if(minimizedWindows.includes(id))shelfItems.push({id,title,detail,onRestore:()=>restoreWindow(id)});};
  if(studio)addWindow('studio','Estúdio de Sites',studioWindow.title+' · '+studioWindow.detail);
  if(studyOpen)addWindow('study','Área de Estudos','Biblioteca local e explicações');
  if(module)addWindow('module',moduleNames[moduleIds.indexOf(module)]||'Painel');
  if(stremio)addWindow('stremio','Stremio',stremio.query);
  if(prospect)addWindow('prospect','Prospecção',prospect.city);
  if(eyeOpen)addWindow('eye','Olho de Deus');
  if(chatOpen)addWindow('chat','Conversa');
  if(note)addWindow('note','Nota',note.path);
  analyses.forEach(kind=>addWindow('analysis:'+kind,kind==='screen'?'Tela':kind==='image'?'Imagem':'Arquivo',analysisTasks.includes(kind)?'Analisando em segundo plano':'Análise aberta'));
  if(musicWindow.visible&&musicWindow.minimized)shelfItems.push({id:'music',title:'Música',detail:musicWindow.title+' · '+musicWindow.state,playing:musicPlaying,onRestore:()=>{restoreWindow('music');music.current?.restore();},onPlayback:()=>{if(musicPlaying)music.current?.pause();else void music.current?.resume();},onClose:()=>music.current?.stop()});
  return <div className="relative h-screen w-screen overflow-hidden bg-black text-slate-100 flex flex-col select-none">
    <WindowShelf items={shelfItems}/>
    <UpdateNotice connected={connected} enabled={panelPrefs?.proactive_suggestions!==false} idle={!studio&&!module&&!studyOpen&&!chatOpen&&!eyeOpen&&!busy&&!microphone.capturing&&!microphone.transcribing&&!voice.isSpeaking&&!voice.isGenerating} voiceEnabled={autoVoice&&Boolean(config?.fish_speech_configured)} onSpeak={text=>void voice.speak(text)} onBusy={setUpdateBusy}/>

    {!eyeActive&&<main className={`absolute inset-0 ${moduleActive?'scene-under-panel':''}`}><IntegratedNeuralStage state={state} audioLevelSource={audioLevelSource} onOrbClick={stageMic} onMicToggle={stageMic} onModuleClick={stageModule}/></main>}
    {!eyeActive&&<div className={`memory-slot ${eyeOpen?'small':''}`}><MemorySpiral graph={graph} small={eyeOpen} onSelect={selectNote}/></div>}
    {eyeOpen&&<WindowSurface minimized={!eyeActive}><div className="eye-slot expanded"><MinimizeWindow label="Olho de Deus" onClick={()=>minimizeWindow('eye')}/>
      <button className="eye-close" aria-label="Fechar Olho de Deus" title="Fechar Olho de Deus · F4 controla o microfone" onClick={()=>{eyeAnnouncement.current=false;setEyeOpen(false);}}><X size={20}/></button>
      <Suspense fallback={<div className="panel-loading">Abrindo Olho de Deus…</div>}><WorldMap query={placeQuery} onError={message=>tell(message,true)} onReady={worldReady}/></Suspense>
    </div></WindowSurface>}
    <div className="cronos-quick-actions" aria-label="Ações rápidas">
      {!eyeActive&&!moduleActive&&!studyActive&&<><button className="reference-attachment" aria-label="Abrir área de estudos" title="Abrir área de estudos" onClick={()=>{restoreWindow('study');setStudyOpen(true);setEyeOpen(false);setModule(null);setChatOpen(false);}}><BookOpen size={16}/></button><button className="reference-attachment" aria-label="Analisar imagem" title="Analisar imagem" onClick={()=>openAnalysis('image')}><ImagePlus size={16}/></button><button className="reference-attachment" aria-label="Analisar ZIP ou código" title="Analisar ZIP ou código" onClick={()=>openAnalysis('document')}><FileArchive size={16}/></button></>}
      <HandControl/>
      <button className={`reference-mic ${microphone.starting?'starting':microphone.transcribing?'transcribing':busy?'thinking':voice.isGenerating?'generating':voice.isSpeaking?'speaking':microphone.recording?'recording':''}`} aria-pressed={microphone.recording} title={microphone.starting?'Abrindo microfone':microphone.transcribing?'Transcrevendo':busy?'Aguardando Gemini':voice.isGenerating?'Preparando voz':voice.isSpeaking?'Falando — diga Cronos para interromper':microphone.recording?'Microfone ligado':'Microfone desligado'} aria-label={microphone.recording?'Desligar microfone':'Ligar microfone'} onClick={handleMic} ><Mic size={16}/></button>
      {!eyeActive&&!moduleActive&&<button className="reference-screen" aria-label="Ver minha tela" title="Ver minha tela" onClick={()=>screenMonitor.current?.start()}><MonitorUp size={16}/></button>}
    </div>
    <ScreenMonitor ref={screenMonitor} sessionId={()=>session.current} onSession={id=>{session.current=id;}}/>
    {analyses.map(kind=><WindowSurface key={kind} minimized={minimizedWindows.includes('analysis:'+kind)||eyeActive||moduleActive}><AnalysisPanel key={kind} kind={kind} onMinimize={()=>minimizeWindow('analysis:'+kind)} sessionId={session.current} onClose={()=>setAnalyses(previous=>previous.filter(item=>item!==kind))} onBusy={active=>setAnalysisTasks(previous=>active?[...previous.filter(item=>item!==kind),kind]:previous.filter(item=>item!==kind))} onResult={(reply,result)=>{if(result?.session_id)session.current=result.session_id;lastAnswer.current={question:kind==='screen'?'Captura da tela':kind==='image'?'Análise de imagem':'Análise de arquivo',source:'text',reply};if(autoVoice&&config?.fish_speech_configured){analysisSpeechQueue.current.push(reply);setAnalysisSpeechRevision(value=>value+1);}}}/></WindowSurface>)}
    {studio&&<WindowSurface minimized={!studioActive}><Suspense fallback={<div className="panel-loading">Abrindo Estúdio de Sites…</div>}><SiteStudio ref={studioHandle} initial={studio} active={studioActive} onWindowChange={setStudioWindow} onMinimize={()=>minimizeWindow('studio')} onClose={()=>setStudio(null)} onSpeak={text=>{if(autoVoice&&config?.fish_speech_configured){analysisSpeechQueue.current.push(text);setAnalysisSpeechRevision(v=>v+1);}}}/></Suspense></WindowSurface>}
    {studyOpen&&<WindowSurface minimized={!studyActive}><Suspense fallback={<div className="panel-loading">Abrindo Área de Estudos…</div>}><StudyWorkspace active={studyActive} onMinimize={()=>minimizeWindow('study')} onClose={()=>{setStudyOpen(false);setMinimizedWindows(items=>items.filter(item=>item!=='study'));}}/></Suspense></WindowSurface>}
    {stremio&&<WindowSurface minimized={minimizedWindows.includes('stremio')}><Suspense fallback={<div className="panel-loading">Abrindo Stremio…</div>}><StremioPanel key={JSON.stringify(stremio)} initial={stremio} onMinimize={()=>minimizeWindow('stremio')} onPlayback={setFilmPlaying} onClose={()=>setStremio(null)}/></Suspense></WindowSurface>}
    {prospect&&<WindowSurface minimized={minimizedWindows.includes('prospect')}><Suspense fallback={<div className="panel-loading">Abrindo prospecção…</div>}><ProspectPanel key={prospect.city+'|'+prospect.category+'|'+(prospect.report?.id||'')} initial={prospect} onMinimize={()=>minimizeWindow('prospect')} onClose={()=>setProspect(null)} onAsk={text=>{setProspect(null);void sendText(text);}}/></Suspense></WindowSurface>}
    <MusicPlayer ref={music} onWindowChange={setMusicWindow} onPlayback={setMusicPlaying} onTalk={async()=>{voice.stop();microphone.cancelCapture();await microphone.start();}} local={config?.privacy_mode==='local'} onError={message=>tell(message,true)}/>
    {notice&&error&&<div className="scene-notice" role="status">{notice}</div>}
    {note&&<WindowSurface minimized={minimizedWindows.includes('note')}><section className="note-window" aria-label="Nota Obsidian"><MinimizeWindow label="nota" onClick={()=>minimizeWindow('note')}/><button onClick={()=>setNote(null)} aria-label="Fechar nota"><X size={18}/></button><pre>{note.content}</pre></section></WindowSurface>}
    {studyPanels.length>0&&!chatOpen&&!moduleActive&&!eyeActive&&!studyActive&&!studioActive&&<StudyExplanationPanel panels={studyPanels} activeId={focusedStudyPanel} onActivate={id=>focusStudyPanel(id)} onMinimize={minimizeStudyPanel} onRestore={restoreStudyPanel} onClose={closeStudyPanel} onToggleLock={id=>changeStudyPanels(items=>items.map(panel=>panel.id===id?{...panel,locked:!panel.locked}:panel))}/>}
    {displayTurn?.reply&&showSpokenCards&&!chatOpen&&!module&&!eyeOpen&&<AnswerCards reply={displayTurn.reply} layout={cardLayout}/>}
    {displayTurn&&displayTurn.source==='text'&&showSpokenCards&&!chatOpen&&!module&&!eyeOpen&&<MovableCardFrame className="spoken-question"><HolographicCard title="PERGUNTA" variant="ribbon" movable><p className="holo-text">{displayTurn.question}</p></HolographicCard></MovableCardFrame>}
    {chatOpen&&<WindowSurface minimized={minimizedWindows.includes('chat')}><section className="card-composer" aria-label="Escrever para Kronos"><HolographicCard title="PERGUNTA" variant="layered">
      <MinimizeWindow label="conversa" onClick={()=>minimizeWindow('chat')}/><button className="holo-close" onClick={()=>setChatOpen(false)} aria-label="Fechar conversa"><X size={17}/></button>
      <form onSubmit={send}><label htmlFor="chat-input">O que você quer perguntar?</label><textarea id="chat-input" value={draft} onChange={event=>{setDraft(event.target.value);event.target.style.height='auto';event.target.style.height=Math.min(260,event.target.scrollHeight)+'px';}} maxLength={16000} rows={2}/>
        <div className="footer-actions"><button type="submit" disabled={busy||microphone.transcribing||!draft.trim()}><Send size={15}/>Enviar mensagem</button></div>
      </form>
    </HolographicCard></section></WindowSurface>}
    {tools.some(result=>result.status==='pending_confirmation')&&<section className="holo-tool-deck" aria-label="Ações pendentes">{tools.filter(result=>result.status==='pending_confirmation').map((result,index)=><HolographicCard key={index} title={result.name} variant="layered"><pre>{JSON.stringify(result.arguments,null,2)}</pre><div className="footer-actions"><button disabled={busy} onClick={()=>approve(result,true)}>Confirmar ação</button><button disabled={busy} onClick={()=>approve(result,false)}>Cancelar</button></div></HolographicCard>)}</section>}
    {module&&<WindowSurface minimized={!moduleActive}><Suspense fallback={<div className="panel-loading">Abrindo painel…</div>}><ModulePanel id={module} onMinimize={()=>minimizeWindow('module')} onSelect={openModule} onClose={closeModule} graph={graph} onSync={()=>setGraphRevision(v=>v+1)} onNote={path=>{closeModule();void selectNote(path);}} preferences={panelPrefs} onPreferences={updatePreferences} voice={voice} microphone={microphone} lastTurn={displayTurn} busy={busy} onComposer={()=>{closeModule();restoreWindow('chat');setChatOpen(true);}} onEye={()=>{closeModule();restoreWindow('eye');voice.prepare();eyeAnnouncement.current=true;setEyeOpen(true);}} onAsk={text=>void sendText(text)}/></Suspense></WindowSurface>}


  </div>;
}
