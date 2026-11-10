import {useEffect,useState,type CSSProperties} from 'react';
import {Battery,ChevronLeft,ChevronRight,Cpu,HardDrive,MemoryStick,Monitor,Settings,Thermometer,Wifi,X,Share2,ChartNoAxesCombined} from 'lucide-react';
import {api} from '../api';
import {modules} from '../panels/modules';
import {capability,type CapabilityId} from '../capabilities';
import './home-dashboard.css';

type Metrics={cpu_percent:number|null;ram_percent:number|null;ram_used_bytes:number|null;ram_total_bytes:number|null;disk_percent:number|null;disk_used_bytes:number|null;disk_total_bytes:number|null;network_bytes_per_second:number|null;temperature_celsius:number|null;battery_percent:number|null;battery_plugged:boolean|null};
type Props={connected:boolean;preferences:any;onPreferences:(value:any)=>void;panelOpenRequest:number;menuOpen:boolean;onMenuClose:()=>void;section:CapabilityId|null;onSection:(value:CapabilityId|null)=>void;graphTotal:number;provider?:string;providerConfigured?:boolean;onModule:(index:number)=>void;onStudy:()=>void;onStudio:()=>void;onEye:()=>void;onChat:()=>void;onScreen:()=>void;onImage:()=>void;onDocument:()=>void;onMicrophone:()=>void;microphoneOn:boolean};
const labels=['Sistema','Memória','Conexões','Análise','Configurações'];
const icons=[Monitor,Cpu,Share2,ChartNoAxesCombined,Settings];
const sections:CapabilityId[]=['system','memory','connections','analysis','settings'];
const size=(bytes:number|null|undefined)=>bytes==null?'—':`${(bytes/1073741824).toFixed(1)} GB`;
const percent=(value:number|null|undefined)=>value==null?'—':`${Math.round(value)}%`;

export function HomeDashboard({connected,preferences,onPreferences,panelOpenRequest,menuOpen,onMenuClose,section,onSection,graphTotal,provider,providerConfigured,onModule,onStudy,onStudio,onEye,onChat,onScreen,onImage,onDocument,onMicrophone,microphoneOn}:Props){
 const [narrow,setNarrow]=useState(()=>window.matchMedia('(max-width:700px)').matches);
 const [mobileLeftOpen,setMobileLeftOpen]=useState(false);
 const [mobileRightOpen,setMobileRightOpen]=useState(false);
 const [leftClosed,setLeftClosed]=useState(Boolean(preferences?.home_left_closed));
 const [rightClosed,setRightClosed]=useState(Boolean(preferences?.home_right_closed));
 const [rightCompact,setRightCompact]=useState(Boolean(preferences?.home_right_compact));
 const [metrics,setMetrics]=useState<Metrics|null>(null);
 const [status,setStatus]=useState('Aguardando conexão');
 const [providers,setProviders]=useState<Array<{id:string;configured:boolean}>>([]);
 const persist=(key:'home_left_closed'|'home_right_closed'|'home_right_compact',value:boolean)=>{if(!connected)return;void api('/panels/preferences',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({[key]:value})}).then(response=>response.json()).then(data=>onPreferences(data.preferences)).catch(()=>setStatus('Não foi possível salvar a posição dos painéis'));};
 const toggleLeft=()=>{if(narrow){setMobileLeftOpen(value=>!value);return;}setLeftClosed(value=>!value);persist('home_left_closed',!leftClosed);};
 const toggleRight=()=>{if(narrow){setMobileRightOpen(value=>!value);return;}setRightClosed(value=>!value);persist('home_right_closed',!rightClosed);};
 const toggleCompact=()=>{setRightCompact(value=>!value);persist('home_right_compact',!rightCompact);};
 useEffect(()=>{if(!preferences)return;setLeftClosed(Boolean(preferences.home_left_closed));setRightClosed(Boolean(preferences.home_right_closed));setRightCompact(Boolean(preferences.home_right_compact));},[preferences?.home_left_closed,preferences?.home_right_closed,preferences?.home_right_compact]);
 useEffect(()=>{const query=window.matchMedia('(max-width:700px)');const update=()=>setNarrow(query.matches);query.addEventListener('change',update);return()=>query.removeEventListener('change',update);},[]);
 useEffect(()=>{if(panelOpenRequest){setRightClosed(false);persist('home_right_closed',false);}},[panelOpenRequest]);
 useEffect(()=>{
   if(!connected){setMetrics(null);setStatus('Sem conexão');return;}
   let alive=true;
   const poll=()=>{void api('/system/metrics').then(response=>response.json()).then((data:Metrics)=>{if(alive){setMetrics(data);setStatus('Atualizado agora');}}).catch(()=>{if(alive)setStatus('Medição indisponível');});};
   poll();const timer=window.setInterval(poll,8000);
   return()=>{alive=false;window.clearInterval(timer);};
 },[connected]);
 useEffect(()=>{if(!connected||section!=='connections')return;let alive=true;void api('/providers').then(response=>response.json()).then(data=>{if(alive)setProviders(Array.isArray(data.providers)?data.providers:[]);}).catch(()=>{if(alive)setProviders([]);});return()=>{alive=false;};},[connected,section]);
 const measured=metrics?[metrics.cpu_percent,metrics.ram_percent,metrics.disk_percent].filter((value):value is number=>value!=null):[];
 const leftVisible=!leftClosed&&(!narrow||mobileLeftOpen),rightVisible=!rightClosed&&(!narrow||mobileRightOpen);
 const usage=measured.length?Math.round(measured.reduce((sum,value)=>sum+value,0)/measured.length):null;
 const cards=[
   {label:'CPU',value:percent(metrics?.cpu_percent),detail:'Processador',icon:Cpu,bar:metrics?.cpu_percent,onClick:()=>onModule(11)},
   {label:'Memória RAM',value:percent(metrics?.ram_percent),detail:`${size(metrics?.ram_used_bytes)} de ${size(metrics?.ram_total_bytes)}`,icon:MemoryStick,bar:metrics?.ram_percent,onClick:()=>onModule(11)},
   {label:'Armazenamento',value:percent(metrics?.disk_percent),detail:`${size(metrics?.disk_used_bytes)} de ${size(metrics?.disk_total_bytes)}`,icon:HardDrive,bar:metrics?.disk_percent,onClick:()=>onModule(7)},
   {label:'Internet',value:metrics?.network_bytes_per_second==null?'Indisponível':`${(metrics.network_bytes_per_second/1048576).toFixed(2)} MB/s`,detail:'Tráfego atual',icon:Wifi,bar:null,onClick:()=>onModule(8)},
   {label:'Temperatura',value:metrics?.temperature_celsius==null?'Indisponível':`${Math.round(metrics.temperature_celsius)} °C`,detail:'Sensor do sistema',icon:Thermometer,bar:null,onClick:()=>onModule(11)},
   {label:'Bateria',value:metrics?.battery_percent==null?'Indisponível':percent(metrics.battery_percent),detail:metrics?.battery_percent==null?'Sem medição':metrics.battery_plugged?'Carregando':'Energia restante',icon:Battery,bar:metrics?.battery_percent,onClick:()=>onModule(10)},
 ];
 return <div className="cronos-home-hud">
   <header className="home-brand"><span className="home-brand-mark" aria-hidden="true">◌</span><span>CRONOS</span><span className="home-brand-line"/></header>
   <aside className={`home-nav ${leftVisible?'':'closed'}`} aria-label="Navegação principal">
     <button className="home-collapse" onClick={toggleLeft} aria-label={leftVisible?'Recolher menu esquerdo':'Expandir menu esquerdo'} title={leftVisible?'Recolher':'Expandir'}>{leftVisible?<ChevronLeft size={17}/>:<ChevronRight size={17}/>}</button>
     {labels.map((label,index)=>{const Icon=icons[index];return <button key={label} className={section===sections[index]||(!section&&index===0)?'selected':''} onClick={()=>onSection(section===sections[index]?null:sections[index])} title={label} aria-label={label}><Icon size={19}/><span>{label}</span></button>;})}
   </aside>
   <aside className={`home-stats ${rightVisible?'':'closed'} ${rightCompact?'compact':''}`} aria-label="Indicadores do sistema">
     <div className="home-stats-header"><span>SISTEMA · AGORA</span><div><button onClick={toggleCompact} aria-label={rightCompact?'Expandir indicadores':'Compactar indicadores'} title={rightCompact?'Expandir':'Compactar'}><Settings size={15}/></button><button onClick={toggleRight} aria-label={rightVisible?'Recolher indicadores':'Abrir indicadores'} title={rightVisible?'Recolher':'Abrir'}>{rightVisible?<ChevronRight size={18}/>:<ChevronLeft size={18}/>}</button></div></div>
     {rightVisible&&<><div className="home-usage" style={{'--usage':`${usage??0}%`} as CSSProperties}><div><strong>{percent(usage)}</strong><small>USO MÉDIO</small></div></div><span className="home-status">{status}</span><div className="home-stat-list">{cards.map(card=>{const Icon=card.icon;return <button key={card.label} onClick={card.onClick} title={`${card.label}: ${card.value}. ${card.detail}`}><Icon size={19}/><span><b>{card.label}</b><small>{card.detail}</small>{card.bar!=null&&<i style={{width:`${Math.max(0,Math.min(100,card.bar))}%`}}/>}</span><strong>{card.value}</strong><ChevronRight size={14}/></button>;})}</div></>}
   </aside>
   {section&&<section className="home-inspector" role="dialog" aria-label={`Painel ${capability(section).label}`}><header><div><small>CRONOS / {capability(section).category.toUpperCase()}</small><h2>{capability(section).label}</h2></div><button aria-label="Fechar painel" onClick={()=>onSection(null)}><X size={18}/></button></header>
     {section==='system'&&<><p>Indicadores medidos pelo computador. {status}.</p><div className="home-inspector-list">{cards.map(card=><div key={card.label}><span>{card.label}</span><strong>{card.value}</strong></div>)}</div><button onClick={()=>onModule(11)}>Abrir monitoramento completo</button></>}
     {section==='memory'&&<><p>{connected?`${graphTotal} notas indexadas na memória local.`:'Memória indisponível sem conexão.'}</p><button onClick={()=>onModule(7)}>Abrir memória e notas</button><button onClick={onStudy}>Abrir área de estudos</button></>}
     {section==='connections'&&<><p>Provedor ativo: {provider||'Indisponível'} · {providerConfigured?'configurado':'sem configuração confirmada'}.</p><div className="home-inspector-list">{providers.map(item=><div key={item.id}><span>{item.id}</span><strong>{item.configured?'Configurado':'Não configurado'}</strong></div>)}</div><button onClick={()=>onModule(6)}>Abrir integrações</button></>}
     {section==='analysis'&&<><p>Envie um arquivo ou uma imagem para os analisadores existentes.</p><button onClick={onDocument}>Analisar arquivo</button><button onClick={onImage}>Analisar imagem</button><button onClick={onScreen}>Ver minha tela</button><button onClick={()=>onModule(0)}>Abrir processamento</button></>}
     {section==='settings'&&<><p>Preferências salvas no CRONOS.</p><label><input type="checkbox" checked={preferences?.device_auto_connect!==false} onChange={e=>{void api('/panels/preferences',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_auto_connect:e.target.checked})}).then(r=>r.json()).then(data=>onPreferences(data.preferences)).catch(()=>setStatus('Não foi possível salvar a preferência'));}}/>Conectar microfone automaticamente</label><label><input type="checkbox" checked={preferences?.proactive_suggestions!==false} onChange={e=>{void api('/panels/preferences',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({proactive_suggestions:e.target.checked})}).then(r=>r.json()).then(data=>onPreferences(data.preferences)).catch(()=>setStatus('Não foi possível salvar a preferência'));}}/>Sugestões proativas</label><button onClick={()=>onModule(3)}>Ajustar linguagem e transcrição</button><button onClick={()=>onModule(2)}>Ajustar voz</button></>}
     <small className="home-inspector-foot">{capability(section).description}</small>
   </section>}
   {menuOpen&&<section className="home-gear-menu" aria-label="Funções e configurações"><header><div><small>CRONOS</small><h2>Funções</h2></div><button onClick={onMenuClose} aria-label="Fechar funções"><X size={18}/></button></header><div className="home-gear-grid">{modules.map((item,index)=>{const Icon=item.icon;return <button key={item.id} onClick={()=>{onModule(index);onMenuClose();}}><Icon size={19}/><span>{item.name}</span></button>;})}</div><div className="home-gear-tools"><h3>Acesso rápido</h3><button onClick={onStudy}>Área de estudos</button><button onClick={onStudio}>Estúdio de Sites</button><button onClick={onEye}>Olho de Deus</button><button onClick={onChat}>Digitar mensagem</button><button onClick={onScreen}>Ver minha tela</button><button onClick={onImage}>Analisar imagem</button><button onClick={onDocument}>Analisar arquivo</button><button onClick={onMicrophone}>{microphoneOn?'Desligar microfone':'Ligar microfone'}</button></div></section>}
 </div>;
}
