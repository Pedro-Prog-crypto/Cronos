import React,{forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {api} from '../api';
import {musicCommand} from '../musicCommands';
import './MusicPlayer.css';
export type MusicHandle={handle:(text:string)=>boolean;stop:()=>void;load:(result:any)=>void};
type Track={id:string;title:string};
const time=(seconds:number)=>`${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;
export const MusicPlayer=forwardRef<MusicHandle,{local:boolean;onError:(message:string)=>void}>(({local,onError},ref)=>{
 const [visible,setVisible]=useState(false),[tracks,setTracks]=useState<Track[]>([]),[message,setMessage]=useState(''),[hz,setHz]=useState<number|null>(null);
 const [query,setQuery]=useState(''),[video,setVideo]=useState(false),[volume,setVolume]=useState(60),[elapsed,setElapsed]=useState(0),[duration,setDuration]=useState(0),[playerState,setPlayerState]=useState('Aguardando player');
 const frame=useRef<HTMLIFrameElement>(null),context=useRef<AudioContext|null>(null),gain=useRef<GainNode|null>(null),request=useRef<AbortController|null>(null),version=useRef(0),volumeRef=useRef(volume);volumeRef.current=volume;
 const post=(func:string,args:unknown[]=[])=>frame.current?.contentWindow?.postMessage(JSON.stringify({event:'command',func,args}),'https://www.youtube-nocookie.com');
 const clear=()=>{version.current++;request.current?.abort();request.current=null;if(context.current)void context.current.close();context.current=null;gain.current=null;setTracks([]);setHz(null);setElapsed(0);setDuration(0);setPlayerState('Aguardando player');};
 const stop=()=>{clear();setVisible(false);setMessage('');};
 const load=(result:any)=>{clear();setVisible(true);setTracks((result.tracks||[]).filter((t:any)=>/^[A-Za-z0-9_-]{11}$/.test(t.id)).slice(0,8));setMessage(result.message||'Se o áudio não começar, clique em reproduzir no vídeo.');};
 const search=async(value:string,similar=false,clip=video)=>{
  clear();setQuery(value);setVideo(clip);const current=version.current;setVisible(true);setMessage('Buscando música ou clipe…');const controller=new AbortController();request.current=controller;
  try{const result=await(await api('/music/search?'+new URLSearchParams({query:value,similar:String(similar),video:String(clip)}),{signal:controller.signal})).json();
   if(current!==version.current)return;setTracks(result.tracks);setMessage(result.message||'Se o áudio não começar, clique em reproduzir no vídeo.');
  }catch(error){if(!controller.signal.aborted){setMessage('A busca não respondeu. Nenhuma música começou. Tente outra busca ou cole o link do vídeo.');onError('Não consegui buscar a música.');}}
 };
 const frequency=(value:number)=>{
  if(value<20||value>2000||!Number.isFinite(value)){onError('Escolha um tom entre 20 e 2000 Hz.');return;}
  clear();setVisible(true);setHz(value);setMessage('Tom puro; não é uma música. Comece com volume baixo.');
  const ctx=new AudioContext();context.current=ctx;const oscillator=ctx.createOscillator(),level=ctx.createGain();gain.current=level;
  oscillator.frequency.value=value;level.gain.setValueAtTime(0,ctx.currentTime);level.gain.linearRampToValueAtTime(.025,ctx.currentTime+.1);oscillator.connect(level);level.connect(ctx.destination);oscillator.start();
  void ctx.resume().then(()=>setPlayerState('Reproduzindo tom')).catch(()=>onError('Clique em Continuar para liberar o áudio no navegador.'));
 };
 const pause=()=>{post('pauseVideo');void context.current?.suspend().then(()=>setPlayerState('Pausado'));};
 const resume=()=>{post('playVideo');void context.current?.resume().then(()=>setPlayerState('Reproduzindo tom'));};
 useImperativeHandle(ref,()=>({stop,load,handle(text){
  const command=musicCommand(text);if(!command)return false;
  if(command.action==='search'){if(local){onError('Música online está desativada no modo local.');return true;}void search(command.query,command.similar,Boolean(command.video));}
  else if(command.action==='frequency')frequency(command.hz);
  else if(command.action==='stop')stop();
  else if(command.action==='pause')pause();
  else if(command.action==='resume')resume();
  else if(command.action==='next')post('nextVideo');
  else if(command.action==='previous')post('previousVideo');return true;
 }}));
 useEffect(()=>{
  const receive=(event:MessageEvent)=>{
   if(event.source!==frame.current?.contentWindow||!['https://www.youtube-nocookie.com','https://www.youtube.com'].includes(event.origin))return;
   try{const data=typeof event.data==='string'?JSON.parse(event.data):event.data;
    if(data.event==='onReady'){post('setVolume',[volumeRef.current]);setPlayerState('Player pronto');}
    if(data.event==='onError'){setPlayerState('Falha no vídeo');setMessage('Este vídeo não permite reprodução aqui ou não está disponível. Escolha outro resultado da fila.');}
    const info=data.info;if(data.event==='infoDelivery'&&info){if(Number.isFinite(info.currentTime))setElapsed(info.currentTime);if(Number.isFinite(info.duration))setDuration(info.duration);if(info.playerState===1)setPlayerState('Reproduzindo');if(info.playerState===2)setPlayerState('Pausado');if(info.playerState===0)setPlayerState('Finalizado');}
    if(data.event==='onStateChange'){setPlayerState(({0:'Finalizado',1:'Reproduzindo',2:'Pausado',3:'Carregando'} as any)[data.info]||'Player pronto');}
   }catch{}
  };
  window.addEventListener('message',receive);return()=>{window.removeEventListener('message',receive);request.current?.abort();void context.current?.close();};
 },[]);
 if(!visible)return null;
 const first=tracks[0];const params=new URLSearchParams({autoplay:'1',playsinline:'1',enablejsapi:'1',origin:window.location.origin,rel:'0',playlist:tracks.slice(1).map(t=>t.id).join(',')});
 return <section className="music-player" aria-label="Música no Kronos">
  <header><strong>{hz?`${hz} Hz`:first?.title||'MÚSICA E CLIPES'}</strong><button onClick={stop} aria-label="Fechar música">×</button></header>
  {first&&<iframe id="cronos-music" ref={frame} title="Player de música do YouTube" src={`https://www.youtube-nocookie.com/embed/${first.id}?${params}`} allow="autoplay; encrypted-media; fullscreen" referrerPolicy="strict-origin-when-cross-origin" allowFullScreen onLoad={()=>{frame.current?.contentWindow?.postMessage(JSON.stringify({event:'listening',id:'cronos-music'}),'https://www.youtube-nocookie.com');for(const event of ['onReady','onError','onStateChange'])post('addEventListener',[event]);}}/>}
  {message&&<p role="status">{message}</p>}
  {(first||hz)&&<><div className="music-playback-status">{playerState}<span>{time(elapsed)} / {time(duration)}</span></div><div className="music-actions">{first&&<button aria-label="Música anterior" onClick={()=>post('previousVideo')}>⏮</button>}<button onClick={pause}>Pausar</button><button onClick={resume}>Continuar</button>{first&&<button aria-label="Próxima música" onClick={()=>post('nextVideo')}>⏭</button>}<button onClick={stop}>Parar</button></div></>}
  {first&&<><label>Posição da música<input aria-label="Posição da música" type="range" min="0" max={duration||1} value={Math.min(elapsed,duration||1)} disabled={!duration} onChange={e=>{setElapsed(Number(e.target.value));post('seekTo',[Number(e.target.value),true]);}}/></label><label>Volume · {volume}%<input aria-label="Volume da música" type="range" min="0" max="100" value={volume} onChange={e=>{const v=Number(e.target.value);setVolume(v);post('setVolume',[v]);}}/></label></>}
  {hz&&<label>Volume do tom <input type="range" min="0" max="0.08" step="0.001" defaultValue="0.025" onChange={e=>{if(gain.current&&context.current)gain.current.gain.setTargetAtTime(Number(e.target.value),context.current.currentTime,.05);}}/></label>}
  {tracks.length>1&&<label>Fila · escolha outro resultado<select aria-label="Escolher música" value={first?.id} onChange={e=>{const selected=tracks.find(t=>t.id===e.target.value);if(selected){setElapsed(0);setDuration(0);setTracks([selected,...tracks.filter(t=>t!==selected)]);}}}>{tracks.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></label>}
  {!hz&&<form onSubmit={e=>{e.preventDefault();if(query.trim())void search(query,false,video);}}><label>Buscar música, clipe ou colar link<input aria-label="Buscar música ou clipe" value={query} maxLength={240} onChange={e=>setQuery(e.target.value)} placeholder="Nada pra Fazer — informe o cantor se necessário"/></label><label><input type="checkbox" checked={video} onChange={e=>setVideo(e.target.checked)}/> Buscar clipe oficial</label><button disabled={!query.trim()}>Tocar aqui</button></form>}
 </section>;
});
