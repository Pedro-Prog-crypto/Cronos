import React,{useEffect,useRef,useState} from 'react';
import {X,Search,ExternalLink,Play,Maximize} from 'lucide-react';
import {api,jsonApi} from '../api';
import {StremioRequest} from '../stremioCommands';
import './StremioPanel.css';
export default function StremioPanel({initial,onClose,onPlayback}:{initial:StremioRequest;onClose:()=>void;onPlayback?:(active:boolean)=>void}){
 const [query,setQuery]=useState(initial.query),[kind,setKind]=useState(initial.kind),[season,setSeason]=useState(initial.season?.toString()||''),[episode,setEpisode]=useState(initial.episode?.toString()||'');
 const [result,setResult]=useState<StremioRequest|null>(initial.items?initial:null),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[registered,setRegistered]=useState<boolean|null>(null);
 const controller=useRef<AbortController|null>(null),openExact=useRef(Boolean(initial.openExact));
 const [addon,setAddon]=useState(''),[selected,setSelected]=useState<NonNullable<StremioRequest['items']>[number]|null>(null),[sources,setSources]=useState<{name:string;title:string;url:string}[]>([]),[playing,setPlaying]=useState(''),[expanded,setExpanded]=useState(false);
 const player=useRef<HTMLVideoElement>(null);
 const playback=useRef(onPlayback);playback.current=onPlayback;
 useEffect(()=>{const listen=()=>{player.current?.pause();playback.current?.(false);};window.addEventListener('cronos:listen',listen);return()=>{window.removeEventListener('cronos:listen',listen);playback.current?.(false);};},[]);
 async function internal(item:NonNullable<StremioRequest['items']>[number]){
  setSelected(item);setSources([]);setPlaying('');setMessage('');
  if(!addon.trim()){setMessage('Para reproduzir aqui, cole abaixo o manifest.json de um complemento seu que forneça mídia HTTPS direta. Também pode abrir o título no Stremio instalado.');return;}
  if(item.kind==='series'&&(!season||!episode)){setMessage('Informe temporada e episódio para consultar a fonte.');return;}
  setBusy(true);
  try{const data=await jsonApi('/stremio/streams',{id:item.id,kind:item.kind,addon:addon.trim(),...(item.kind==='series'?{season:Number(season),episode:Number(episode)}:{})});setSources(data.streams);setMessage(data.message||'Escolha a fonte para reproduzir dentro do Cronos.');}
  catch(error){setMessage(error instanceof Error?error.message:'A fonte não respondeu. Tente novamente.');}finally{setBusy(false);}
 }
 async function search(){
  controller.current?.abort();const request=new AbortController();controller.current=request;setBusy(true);setMessage('');
  try{const data=await(await api('/stremio/search',{method:'POST',body:JSON.stringify({query:query.trim(),kind,...(kind==='series'&&season&&episode?{season:Number(season),episode:Number(episode)}:{})}),headers:{'Content-Type':'application/json'},signal:request.signal})).json();if(!request.signal.aborted){setResult(data);if(openExact.current){openExact.current=false;const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();const exact=(data.items||[]).filter((item:any)=>normalize(item.name)===normalize(query));if(exact.length===1)await internal(exact[0]);}}}
  catch(error){if(!request.signal.aborted)setMessage(error instanceof Error?error.message:'Não foi possível pesquisar.');}
  finally{if(!request.signal.aborted)setBusy(false);}
 }
 useEffect(()=>{void jsonApi('/stremio/status').then(data=>setRegistered(data.protocol_registered)).catch(()=>{});if(!initial.items)void search();return()=>controller.current?.abort();},[]);
 async function open(item:NonNullable<StremioRequest['items']>[number]){
  if((Boolean(season)!==Boolean(episode))&&kind==='series'){setMessage('Informe temporada e episódio juntos, ou deixe ambos vazios.');return;}
  setBusy(true);setMessage('');try{const data=await jsonApi('/stremio/open',{id:item.id,kind:item.kind,...(item.kind==='series'&&season&&episode?{season:Number(season),episode:Number(episode)}:{})});setMessage(data.message);}catch(error){setMessage(error instanceof Error?error.message:'Não foi possível abrir o Stremio.');}finally{setBusy(false);}
 }
 return <section className={`stremio-panel ${expanded?'stremio-expanded':''}`} role="dialog" aria-label="Filmes e séries no Stremio"><header><div><h2>STREMIO</h2><p>Filmes e séries · fontes diretas ou aplicativo instalado</p></div><button aria-label="Ampliar Stremio" onClick={()=>setExpanded(v=>!v)}><Maximize/></button><button aria-label="Fechar Stremio" onClick={onClose}><X/></button></header>
 <form onSubmit={e=>{e.preventDefault();void search();}}><label>Título<input aria-label="Buscar filme ou série" value={query} onChange={e=>setQuery(e.target.value)} maxLength={200} placeholder="Nome do filme ou série" required/></label><label>Tipo<select aria-label="Tipo de título" value={kind} onChange={e=>setKind(e.target.value as 'movie'|'series')}><option value="movie">Filme</option><option value="series">Série</option></select></label>{kind==='series'&&<><label>Temporada<input aria-label="Temporada" type="number" min="0" max="200" value={season} onChange={e=>setSeason(e.target.value)}/></label><label>Episódio<input aria-label="Episódio" type="number" min="1" max="20000" value={episode} onChange={e=>setEpisode(e.target.value)}/></label></>}<button disabled={busy||!query.trim()}><Search size={18}/>{busy?'Aguarde…':'Pesquisar'}</button></form>
 <p>O catálogo identifica títulos. Para tocar aqui é necessária uma fonte de mídia direta autorizada; instalar o Stremio não compartilha automaticamente suas fontes ou conta com o Cronos.</p><label>Complemento para reprodução interna<input aria-label="Manifest do complemento Stremio" type="url" placeholder="https://seu-complemento/manifest.json" value={addon} onChange={e=>setAddon(e.target.value)} autoComplete="off"/></label><small>Usado apenas nesta sessão. O Cronos não lê credenciais nem instala complementos.</small>{selected&&<button disabled={busy||!addon.trim()} onClick={()=>void internal(selected)}>Consultar fontes de {selected.name}</button>}{registered===false&&<p role="status">O protocolo Stremio não foi detectado neste servidor. No Windows, abra o Stremio uma vez ou repare sua instalação.</p>}
 {message&&<p role="status">{message}</p>}{playing&&<div className="stremio-playback"><video ref={player} src={playing} controls autoPlay playsInline preload="metadata" onPlaying={()=>playback.current?.(true)} onPause={()=>playback.current?.(false)} onEnded={()=>playback.current?.(false)} onError={()=>{playback.current?.(false);setMessage('Esta fonte não pôde ser reproduzida neste navegador. Tente outra fonte ou use o aplicativo Stremio; o microfone continua disponível.');}}/><button onClick={()=>void player.current?.requestFullscreen().catch(()=>setExpanded(true))}>Tela cheia</button><button onClick={()=>setPlaying('')}>Fechar vídeo</button></div>}{sources.map((source,index)=><button key={index} onClick={()=>{setPlaying(source.url);setMessage('');}}><Play size={16}/>{source.name} · {source.title}</button>)}{result&&<><p>{result.message}</p><div className="stremio-results">{result.items?.map(item=><article key={item.id}><div><h3>{item.name}</h3><small>{item.year} · {item.kind==='movie'?'Filme':'Série'}</small></div><button disabled={busy} onClick={()=>void internal(item)}><Play size={16}/>Fontes no Cronos</button><button disabled={busy} onClick={()=>void open(item)}><ExternalLink size={16}/>Abrir no Stremio</button></article>)}</div></>}
 </section>;
}
