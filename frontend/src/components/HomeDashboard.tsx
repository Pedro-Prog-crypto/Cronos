import {useEffect,useState,type CSSProperties} from 'react';
import {Activity,Battery,ChevronLeft,ChevronRight,Cpu,Database,HardDrive,MemoryStick,Monitor,Network,Settings2,Thermometer,Wifi,X} from 'lucide-react';
import {api} from '../api';
import {modules} from '../panels/modules';
import './home-dashboard.css';

type Metrics={cpu_percent:number|null;ram_percent:number|null;ram_used_bytes:number|null;ram_total_bytes:number|null;disk_percent:number|null;disk_used_bytes:number|null;disk_total_bytes:number|null;network_bytes_per_second:number|null;temperature_celsius:number|null;battery_percent:number|null;battery_plugged:boolean|null};
type Props={connected:boolean;preferences:any;onPreferences:(value:any)=>void;panelOpenRequest:number;menuOpen:boolean;onMenuClose:()=>void;onModule:(index:number)=>void;onStudy:()=>void;onStudio:()=>void;onEye:()=>void;onChat:()=>void;onScreen:()=>void;onImage:()=>void;onDocument:()=>void;onMicrophone:()=>void;microphoneOn:boolean};
const labels=['Sistema','Memória','Conexões','Análise','Configurações'];
const icons=[Monitor,Database,Network,Activity,Settings2];
const destinations=[11,7,6,0,5];
const size=(bytes:number|null|undefined)=>bytes==null?'—':`${(bytes/1073741824).toFixed(1)} GB`;
const percent=(value:number|null|undefined)=>value==null?'—':`${Math.round(value)}%`;

export function HomeDashboard({connected,preferences,onPreferences,panelOpenRequest,menuOpen,onMenuClose,onModule,onStudy,onStudio,onEye,onChat,onScreen,onImage,onDocument,onMicrophone,microphoneOn}:Props){
 const [leftClosed,setLeftClosed]=useState(Boolean(preferences?.home_left_closed));
 const [rightClosed,setRightClosed]=useState(Boolean(preferences?.home_right_closed));
 const [rightCompact,setRightCompact]=useState(Boolean(preferences?.home_right_compact));
 const [metrics,setMetrics]=useState<Metrics|null>(null);
 const [status,setStatus]=useState('Aguardando conexão');
 const persist=(key:'home_left_closed'|'home_right_closed'|'home_right_compact',value:boolean)=>{if(!connected)return;void api('/panels/preferences',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({[key]:value})}).then(response=>response.json()).then(data=>onPreferences(data.preferences)).catch(()=>setStatus('Não foi possível salvar a posição dos painéis'));};
 const toggleLeft=()=>{setLeftClosed(value=>!value);persist('home_left_closed',!leftClosed);};
 const toggleRight=()=>{setRightClosed(value=>!value);persist('home_right_closed',!rightClosed);};
 const toggleCompact=()=>{setRightCompact(value=>!value);persist('home_right_compact',!rightCompact);};
 useEffect(()=>{if(!preferences)return;setLeftClosed(Boolean(preferences.home_left_closed));setRightClosed(Boolean(preferences.home_right_closed));setRightCompact(Boolean(preferences.home_right_compact));},[preferences?.home_left_closed,preferences?.home_right_closed,preferences?.home_right_compact]);
 useEffect(()=>{if(panelOpenRequest){setRightClosed(false);persist('home_right_closed',false);}},[panelOpenRequest]);
 useEffect(()=>{
   if(!connected){setMetrics(null);setStatus('Sem conexão');return;}
   let alive=true;
   const poll=()=>{void api('/system/metrics').then(response=>response.json()).then((data:Metrics)=>{if(alive){setMetrics(data);setStatus('Atualizado agora');}}).catch(()=>{if(alive)setStatus('Medição indisponível');});};
   poll();const timer=window.setInterval(poll,8000);
   return()=>{alive=false;window.clearInterval(timer);};
 },[connected]);
 const measured=metrics?[metrics.cpu_percent,metrics.ram_percent,metrics.disk_percent].filter((value):value is number=>value!=null):[];
 const usage=measured.length?Math.round(measured.reduce((sum,value)=>sum+value,0)/measured.length):null;
 const cards=[
   {label:'CPU',value:percent(metrics?.cpu_percent),detail:'Processador',icon:Cpu,bar:metrics?.cpu_percent,onClick:()=>onModule(11)},
   {label:'Memória RAM',value:percent(metrics?.ram_percent),detail:`${size(metrics?.ram_used_bytes)} de ${size(metrics?.ram_total_bytes)}`,icon:MemoryStick,bar:metrics?.ram_percent,onClick:()=>onModule(11)},
   {label:'Armazenamento',value:percent(metrics?.disk_percent),detail:`${size(metrics?.disk_used_bytes)} de ${size(metrics?.disk_total_bytes)}`,icon:HardDrive,bar:metrics?.disk_percent,onClick:()=>onModule(7)},
   {label:'Internet',value:metrics?.network_bytes_per_second==null?'—':`${(metrics.network_bytes_per_second/1048576).toFixed(2)} MB/s`,detail:'Tráfego atual',icon:Wifi,bar:null,onClick:()=>onModule(8)},
   {label:'Temperatura',value:metrics?.temperature_celsius==null?'Indisponível':`${Math.round(metrics.temperature_celsius)} °C`,detail:'Sensor do sistema',icon:Thermometer,bar:null,onClick:()=>onModule(11)},
   {label:'Bateria',value:percent(metrics?.battery_percent),detail:metrics?.battery_plugged?'Carregando':'Energia restante',icon:Battery,bar:metrics?.battery_percent,onClick:()=>onModule(10)},
 ];
 return <div className="cronos-home-hud">
   <header className="home-brand"><span className="home-brand-mark" aria-hidden="true">◌</span><span>CRONOS</span><span className="home-brand-line"/></header>
   <aside className={`home-nav ${leftClosed?'closed':''}`} aria-label="Navegação principal">
     <button className="home-collapse" onClick={toggleLeft} aria-label={leftClosed?'Expandir menu esquerdo':'Recolher menu esquerdo'} title={leftClosed?'Expandir':'Recolher'}>{leftClosed?<ChevronRight size={17}/>:<ChevronLeft size={17}/>}</button>
     {labels.map((label,index)=>{const Icon=icons[index];return <button key={label} className={index===0?'selected':''} onClick={()=>onModule(destinations[index])} title={label} aria-label={label}><Icon size={19}/><span>{label}</span></button>;})}
   </aside>
   <aside className={`home-stats ${rightClosed?'closed':''} ${rightCompact?'compact':''}`} aria-label="Indicadores do sistema">
     <div className="home-stats-header"><span>SISTEMA · AGORA</span><div><button onClick={toggleCompact} aria-label={rightCompact?'Expandir indicadores':'Compactar indicadores'} title={rightCompact?'Expandir':'Compactar'}><Settings2 size={15}/></button><button onClick={toggleRight} aria-label={rightClosed?'Abrir indicadores':'Recolher indicadores'} title={rightClosed?'Abrir':'Recolher'}>{rightClosed?<ChevronLeft size={18}/>:<ChevronRight size={18}/>}</button></div></div>
     {!rightClosed&&<><div className="home-usage" style={{'--usage':`${usage??0}%`} as CSSProperties}><div><strong>{percent(usage)}</strong><small>USO MÉDIO</small></div></div><span className="home-status">{status}</span><div className="home-stat-list">{cards.map(card=>{const Icon=card.icon;return <button key={card.label} onClick={card.onClick} title={`${card.label}: ${card.value}. ${card.detail}`}><Icon size={19}/><span><b>{card.label}</b><small>{card.detail}</small>{card.bar!=null&&<i style={{width:`${Math.max(0,Math.min(100,card.bar))}%`}}/>}</span><strong>{card.value}</strong><ChevronRight size={14}/></button>;})}</div></>}
   </aside>
   {menuOpen&&<section className="home-gear-menu" aria-label="Funções e configurações"><header><div><small>CRONOS</small><h2>Funções</h2></div><button onClick={onMenuClose} aria-label="Fechar funções"><X size={18}/></button></header><div className="home-gear-grid">{modules.map((item,index)=>{const Icon=item.icon;return <button key={item.id} onClick={()=>{onModule(index);onMenuClose();}}><Icon size={19}/><span>{item.name}</span></button>;})}</div><div className="home-gear-tools"><h3>Acesso rápido</h3><button onClick={onStudy}>Área de estudos</button><button onClick={onStudio}>Estúdio de Sites</button><button onClick={onEye}>Olho de Deus</button><button onClick={onChat}>Digitar mensagem</button><button onClick={onScreen}>Ver minha tela</button><button onClick={onImage}>Analisar imagem</button><button onClick={onDocument}>Analisar arquivo</button><button onClick={onMicrophone}>{microphoneOn?'Desligar microfone':'Ligar microfone'}</button></div></section>}
 </div>;
}
