import type {CSSProperties,ReactNode} from 'react';
import {Activity,AudioLines,Battery,Brain,Cpu,Database,Fan,HardDrive,MemoryStick,Network,Thermometer,Wifi,Zap,ChevronRight} from 'lucide-react';
import './telemetry-detail.css';

export type Metrics={cpu_percent:number|null;cpu_frequency_ghz?:number|null;cpu_frequency_max_ghz?:number|null;cpu_temperature_celsius?:number|null;ram_percent:number|null;ram_used_bytes:number|null;ram_total_bytes:number|null;gpu_percent?:number|null;gpu_memory_used_bytes?:number|null;gpu_memory_total_bytes?:number|null;gpu_temperature_celsius?:number|null;disk_percent:number|null;disk_used_bytes:number|null;disk_total_bytes:number|null;network_bytes_per_second:number|null;network_download_bytes_per_second?:number|null;network_upload_bytes_per_second?:number|null;temperature_celsius:number|null;fan_rpm?:number|null;gpu_fan_percent?:number|null;battery_percent:number|null;battery_plugged:boolean|null};
type Props={metrics:Metrics|null;connected:boolean;microphoneOn:boolean;providerConfigured:boolean;graphTotal:number;cpuHistory:number[];ramHistory:number[];gpuHistory:number[];networkHistory:number[];onDetails:()=>void};
const percent=(value:number|null|undefined)=>value==null?'Indisponível':`${Math.round(value)}%`;
const gigabytes=(value:number|null|undefined)=>value==null?'Indisponível':`${(value/1073741824).toFixed(1)} GB`;
const megabitsPerSecond=(value:number|null|undefined)=>value==null?'—':`${(value*8/1000000).toFixed(2)} Mb/s`;
const status=(value:boolean)=>value?'Disponível':'Indisponível';

function Trend({values,color}:{values:number[];color:string}){
 if(values.length<2)return <span className="tt-no-history">Aguardando histórico de leituras</span>;
 const maximum=Math.max(1,...values),minimum=Math.min(0,...values);
 const points=values.map((value,index)=>`${index*100/(values.length-1)},${30-(value-minimum)*25/(maximum-minimum)}`).join(' ');
 return <svg className="tt-trend" viewBox="0 0 100 32" preserveAspectRatio="none" aria-label="Histórico medido"><path d="M0 8H100M0 16H100M0 24H100" stroke="#3b657c" strokeWidth=".2" opacity=".45"/><polygon points={`0,32 ${points} 100,32`} fill={color} opacity=".13"/><polyline points={points} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}

function ChipIllustration(){
 return <svg className="tt-chip-art" viewBox="0 0 280 220" fill="none" aria-hidden="true">
  <defs><linearGradient id="tt-chip-edge" x1="61" y1="60" x2="218" y2="178" gradientUnits="userSpaceOnUse"><stop stopColor="#52faff"/><stop offset=".48" stopColor="#087df5"/><stop offset="1" stopColor="#5efaff"/></linearGradient><linearGradient id="tt-chip-face" x1="126" y1="67" x2="194" y2="150" gradientUnits="userSpaceOnUse"><stop stopColor="#1052a9"/><stop offset="1" stopColor="#031733"/></linearGradient><filter id="tt-chip-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter></defs>
  <g stroke="#0c8ade" strokeWidth=".7" opacity=".53"><path d="M5 158 136 82 276 162M2 175 138 96 278 178M16 189 142 114 263 186M43 202 150 137 240 190M13 121 154 203M42 104 182 188M74 88 212 173M207 91 83 169M235 107 108 184M265 124 140 199"/></g>
  <g stroke="#19c9fc" strokeWidth="1" opacity=".8"><path d="M2 161 68 121 86 121M277 158 228 132 204 132M22 188 87 151M247 190 210 165M125 49V16M146 52V4M167 59V25M186 68V37M56 149V114M229 146V109"/></g>
  <g fill="#67f5ff" filter="url(#tt-chip-glow)"><circle cx="125" cy="16" r="3"/><circle cx="146" cy="4" r="3"/><circle cx="167" cy="25" r="2.5"/><circle cx="186" cy="37" r="2.5"/><circle cx="56" cy="114" r="2.5"/><circle cx="229" cy="109" r="2.5"/></g>
  <path d="m43 115 92-53 104 57-95 55-101-59Z" fill="#0a4a8b" stroke="#2ad6ff" strokeWidth="2" filter="url(#tt-chip-glow)"/>
  <path d="m43 115 92-53 104 57-95 55-101-59Z" fill="#071b39" stroke="url(#tt-chip-edge)" strokeWidth="2"/>
  <path d="m43 115 101 59 95-55v27l-95 56-101-60v-27Z" fill="#031429" stroke="#149bea" strokeWidth="1.5"/>
  <path d="m68 117 70-40 78 43-73 42-75-45Z" fill="url(#tt-chip-face)" stroke="#73f8ff" strokeWidth="2.5"/>
  <path d="m78 117 61-35 67 38-63 36-65-39Z" stroke="#3dccff" strokeWidth=".8"/>
  <path d="m87 115 53-29 57 33-54 31-56-35Z" fill="#0a3671" stroke="#269ef1" strokeWidth=".65"/>
  <path d="m91 114 49-27 53 31" stroke="#80edff" strokeWidth="1.4" opacity=".85"/>
  <g stroke="#16a8fa" strokeWidth=".6" opacity=".68"><path d="m23 161 48-28 17 10m-48 31 47-27m-30 39 43-26m121-17 39 22m-52-14 47 27m-65-19 53 30m-151-83-25-14m26 38-26 14m134-19 24-14"/></g>
  <g stroke="#49eaff" strokeWidth="2.7" strokeLinecap="round"><path d="m56 150 0 10m14-2 0 10m15-2 0 10m15-2 0 10m15-2 0 10m15-2 0 10m28 0 0 9m15-18 0 9m15-18 0 9m15-18 0 9m15-18 0 9"/></g>
  <path d="m43 142 101 60 95-56" stroke="#31d9ff" strokeWidth="2" filter="url(#tt-chip-glow)"/>
 </svg>;
}

function Tile({name,value,detail,level,tone,icon,trend,gauge=true}:{name:string;value:string;detail:string;level?:number|null;tone:string;icon:ReactNode;trend?:number[];gauge?:boolean}){
 const measured=level!=null;
 return <div className={`tt-tile tt-${tone}`}><div className="tt-tile-top"><span className="tt-icon">{icon}</span><b>{name}</b></div><div className="tt-tile-main">{gauge?<><div className="tt-tile-signal">{!measured?<span className="tt-no-history">Sem leitura</span>:trend?<Trend values={trend} color="var(--tone)"/>:<div className="tt-meter" aria-hidden="true"><i style={{width:`${Math.max(0,Math.min(100,level))}%`}}/></div>}</div><span className="tt-gauge" style={{'--fill':`${Math.max(0,Math.min(100,level??0))}%`} as CSSProperties} role="img" aria-label={`${name}: ${value}`}><b>{measured?`${Math.round(level)}%`:'—%'}</b></span></>:<strong className={value==='Indisponível'?'missing':''}>{value}</strong>}</div>{!gauge&&trend&&<Trend values={trend} color="var(--tone)"/>}<small>{detail}</small></div>;
}

export function TelemetryDetail({metrics,connected,microphoneOn,providerConfigured,graphTotal,cpuHistory,ramHistory,gpuHistory,networkHistory,onDetails}:Props){
 // This is an estimated load/thermal index, not a hardware diagnostic or a fixed decoration.
 const health=metrics?.cpu_percent!=null&&metrics.ram_percent!=null&&metrics.disk_percent!=null?
  Math.max(0,Math.min(100,Math.round(100-(metrics.cpu_percent*.35+metrics.ram_percent*.35+metrics.disk_percent*.2+Math.max(0,(metrics.cpu_temperature_celsius??metrics.temperature_celsius??60)-60)*.5)))):null;
 const ringColors=['#12e5d9','#2cbcff','#3867ee','#14a9fa','#1debd8'];
 const ringBackground=health==null?'#103247':`conic-gradient(from -78deg,${ringColors.map((color,index)=>{const start=index*health/5,end=(index+1)*health/5,gap=Math.min(.9,(end-start)/5);return `${color} ${start}% ${end-gap}%,#061e32 ${end-gap}% ${end}%`;}).join(',')},#103247 ${health}% 100%)`;
 const network=metrics?.network_bytes_per_second==null?'Indisponível':megabitsPerSecond(metrics.network_bytes_per_second);
 const cpuTemperature=metrics?.cpu_temperature_celsius??metrics?.temperature_celsius;
 const gpuTemperature=metrics?.gpu_temperature_celsius;
 const fan=metrics?.fan_rpm!=null?`${Math.round(metrics.fan_rpm)} RPM`:metrics?.gpu_fan_percent!=null?`${Math.round(metrics.gpu_fan_percent)}% GPU`:'Indisponível';
 const batteryTone=metrics?.battery_percent==null?'cyan':metrics.battery_percent<=10?'red':metrics.battery_percent<=20?'amber':metrics.battery_plugged?'green':'cyan';
 const services=[
  {label:'CRONOS Core',detail:status(connected),active:connected,icon:<Cpu size={18}/>},
  {label:'Microfone',detail:microphoneOn?'Ligado':'Desligado',active:microphoneOn,icon:<AudioLines size={18}/>},
  {label:'IA principal',detail:providerConfigured?'Configurada; sem teste de resposta':'Sem configuração',active:false,icon:<Brain size={18}/>},
  {label:'Memória',detail:connected?`${graphTotal} notas indexadas; gravação não verificada`:'Indisponível',active:false,icon:<Database size={18}/>},
  {label:'Conexão local',detail:status(connected),active:connected,icon:<Network size={18}/>},
 ];
 return <div className="tt-detail">
  <div className="tt-topline" aria-hidden="true"><i/><i/><i/></div>
  <header className="tt-heading"><span className="tt-heading-icon"><Activity size={25}/></span><div><h2>SISTEMA EM TEMPO REAL</h2><p>Monitoramento e desempenho</p></div><span className={`tt-online ${connected?'is-online':''}`}><i/>{connected?'Online':'Offline'}</span></header>
  <div className="tt-overview"><div className="tt-chip"><ChipIllustration/></div><div className={`tt-main-gauge ${health==null?'':'measured'}`} title="Índice estimado a partir das leituras de CPU, RAM, armazenamento e temperatura. Não é um diagnóstico de hardware." style={{background:ringBackground}}><div><strong>{health==null?'—':health}<small>%</small></strong><span>SAÚDE<br/>DO SISTEMA</span></div></div><div className="tt-services">{services.map(item=><div key={item.label} title={`${item.label}: ${item.detail}`}><span>{item.icon}</span><b>{item.label}</b><small>{item.detail}</small><i className={item.active?'active':''}>{item.active?'✓':'—'}</i></div>)}</div></div>
  <div className={`tt-grid ${metrics&&metrics.battery_percent==null?'no-battery':''}`}>
   <Tile name="CPU" value={percent(metrics?.cpu_percent)} detail={metrics?.cpu_frequency_ghz==null?'Frequência indisponível':`${metrics.cpu_frequency_ghz.toFixed(2)}${metrics.cpu_frequency_max_ghz!=null?` / ${metrics.cpu_frequency_max_ghz.toFixed(2)}`:''} GHz`} level={metrics?.cpu_percent} tone="cyan" icon={<Cpu size={22}/>} trend={cpuHistory}/>
   <Tile name="RAM" value={percent(metrics?.ram_percent)} detail={`${gigabytes(metrics?.ram_used_bytes)} / ${gigabytes(metrics?.ram_total_bytes)}`} level={metrics?.ram_percent} tone="violet" icon={<MemoryStick size={22}/>} trend={ramHistory}/>
   <Tile name="GPU" value={percent(metrics?.gpu_percent)} detail={metrics?.gpu_memory_total_bytes==null?'Sensor indisponível':`${gigabytes(metrics?.gpu_memory_used_bytes)} / ${gigabytes(metrics.gpu_memory_total_bytes)}`} level={metrics?.gpu_percent} tone="blue" icon={<Brain size={22}/>} trend={gpuHistory}/>
   <Tile name="Armazenamento" value={percent(metrics?.disk_percent)} detail={`${gigabytes(metrics?.disk_used_bytes)} / ${gigabytes(metrics?.disk_total_bytes)}`} level={metrics?.disk_percent} tone="violet" icon={<HardDrive size={22}/>}/>
   <Tile name="Rede" value={network} detail={`↓ ${megabitsPerSecond(metrics?.network_download_bytes_per_second)} · ↑ ${megabitsPerSecond(metrics?.network_upload_bytes_per_second)}`} tone="cyan" icon={<Wifi size={22}/>} trend={networkHistory} gauge={false}/>
   {(!metrics||metrics.battery_percent!=null)&&<Tile name="Bateria" value={percent(metrics?.battery_percent)} detail={metrics?.battery_percent==null?'Sem medição':metrics.battery_plugged?'Carregando':'Energia restante'} level={metrics?.battery_percent} tone={batteryTone} icon={<Battery size={22}/>}/>}
  </div>
  <div className="tt-temperature"><h3><Thermometer size={23}/> Temperatura</h3><div className="tt-temperature-inner"><div className="tt-temp-readings"><div><span>{metrics?.cpu_temperature_celsius==null?'Sistema':'CPU'}</span><strong>{cpuTemperature==null?'Indisponível':`${cpuTemperature.toFixed(1)} °C`}</strong><div className="tt-temp-track"><i style={{width:cpuTemperature==null?'0%':`${Math.min(100,Math.max(0,cpuTemperature))}%`}}/></div></div><div><span>GPU</span><strong>{gpuTemperature==null?'Indisponível':`${gpuTemperature.toFixed(1)} °C`}</strong><div className="tt-temp-track"><i style={{width:gpuTemperature==null?'0%':`${Math.min(100,Math.max(0,gpuTemperature))}%`}}/></div></div></div><div className={`tt-fan ${fan!=='Indisponível'?'active':''}`}><Fan size={27}/><span>Ventoinha<br/><b>{fan}</b></span></div></div></div>
  <div className="tt-bottom"><div><h3><Activity size={20}/> Uso Geral</h3><div className="tt-dual-trend">{cpuHistory.length<2&&ramHistory.length<2?<span className="tt-no-history">Aguardando histórico de CPU e RAM</span>:<>{cpuHistory.length>=2&&<Trend values={cpuHistory} color="#40d9ff"/>}{ramHistory.length>=2&&<Trend values={ramHistory} color="#b868ff"/>}</>}</div></div><button onClick={onDetails}>Detalhes do sistema <ChevronRight size={18}/></button></div>
  <small className="tt-data-note"><Zap size={13}/> Leituras reais · saúde estimada · atualização a cada 8 segundos</small>
 </div>;
}
