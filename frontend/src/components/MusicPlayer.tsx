import React,{forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {api} from '../api';
import {musicCommand} from '../musicCommands';
import './MusicPlayer.css';
export type MusicHandle={handle:(text:string)=>boolean;stop:()=>void};
type Track={id:string;title:string};
export const MusicPlayer=forwardRef<MusicHandle,{local:boolean;onError:(message:string)=>void}>(({local,onError},ref)=>{
 const [visible,setVisible]=useState(false),[tracks,setTracks]=useState<Track[]>([]),[message,setMessage]=useState(''),[searchUrl,setSearchUrl]=useState(''),[hz,setHz]=useState<number|null>(null);
 const frame=useRef<HTMLIFrameElement>(null),context=useRef<AudioContext|null>(null),gain=useRef<GainNode|null>(null),request=useRef<AbortController|null>(null),version=useRef(0);
 const post=(func:string)=>frame.current?.contentWindow?.postMessage(JSON.stringify({event:'command',func,args:[]}),'https://www.youtube-nocookie.com');
 const clear=()=>{version.current++;request.current?.abort();request.current=null;if(context.current)void context.current.close();context.current=null;gain.current=null;setTracks([]);setHz(null);};
 const stop=()=>{clear();setVisible(false);setMessage('');setSearchUrl('');};
 const search=async(query:string,similar:boolean)=>{
  clear();const current=version.current;setVisible(true);setMessage('Buscando música…');setSearchUrl('');const controller=new AbortController();request.current=controller;
  try{const result=await(await api('/music/search?'+new URLSearchParams({query,similar:String(similar)}),{signal:controller.signal})).json();
   if(current!==version.current)return;setTracks(result.tracks);setSearchUrl(result.search_url);setMessage(result.message||'Se o áudio não começar, clique em reproduzir no player.');
  }catch(error){if(!controller.signal.aborted){setMessage('Não consegui buscar a música. Tente novamente.');onError('Não consegui buscar a música.');}}
 };
 const frequency=(value:number)=>{
  if(value<20||value>2000||!Number.isFinite(value)){onError('Escolha um tom entre 20 e 2000 Hz.');return;}
  clear();setVisible(true);setSearchUrl('');setHz(value);setMessage('Tom puro; não é uma música. Comece com volume baixo.');
  const ctx=new AudioContext();context.current=ctx;const oscillator=ctx.createOscillator(),level=ctx.createGain();gain.current=level;
  oscillator.frequency.value=value;level.gain.setValueAtTime(0,ctx.currentTime);level.gain.linearRampToValueAtTime(.025,ctx.currentTime+.1);oscillator.connect(level);level.connect(ctx.destination);oscillator.start();
  void ctx.resume().catch(()=>onError('Clique em Continuar para liberar o áudio no navegador.'));
 };
 useImperativeHandle(ref,()=>({stop,handle(text){
  const command=musicCommand(text);if(!command)return false;
  if(command.action==='search'){if(local){onError('Música online está desativada no modo local.');return true;}void search(command.query,command.similar);}
  else if(command.action==='frequency')frequency(command.hz);
  else if(command.action==='stop')stop();
  else if(command.action==='pause'){post('pauseVideo');void context.current?.suspend();}
  else if(command.action==='resume'){post('playVideo');void context.current?.resume();}
  else if(command.action==='next')post('nextVideo');return true;
 }}));
 useEffect(()=>{
  const receive=(event:MessageEvent)=>{
   if(event.source!==frame.current?.contentWindow||!['https://www.youtube-nocookie.com','https://www.youtube.com'].includes(event.origin))return;
   try{const data=typeof event.data==='string'?JSON.parse(event.data):event.data;if(data.event==='onError')setMessage('Este vídeo não pode tocar aqui. Escolha outro resultado ou abra no YouTube.');}catch{}
  };
  window.addEventListener('message',receive);return()=>{window.removeEventListener('message',receive);request.current?.abort();void context.current?.close();};
 },[]);
 if(!visible)return null;
 const first=tracks[0];const params=new URLSearchParams({autoplay:'1',playsinline:'1',enablejsapi:'1',origin:window.location.origin,rel:'0',playlist:tracks.slice(1).map(t=>t.id).join(',')});
 return <section className="music-player" aria-label="Música no Kronos">
  <header><strong>{hz?`${hz} Hz`:first?.title||'MÚSICA'}</strong><button onClick={stop} aria-label="Fechar música">×</button></header>
  {first&&<iframe ref={frame} title="Player de música do YouTube" src={`https://www.youtube-nocookie.com/embed/${first.id}?${params}`} allow="autoplay; encrypted-media; fullscreen" allowFullScreen onLoad={()=>{frame.current?.contentWindow?.postMessage(JSON.stringify({event:'listening',id:'cronos-music'}),'https://www.youtube-nocookie.com');frame.current?.contentWindow?.postMessage(JSON.stringify({event:'command',func:'addEventListener',args:['onError']}),'https://www.youtube-nocookie.com');}}/>}
  {message&&<p role="status">{message}</p>}
  <div className="music-actions"><button onClick={()=>{post('pauseVideo');void context.current?.suspend();}}>Pausar</button><button onClick={()=>{post('playVideo');void context.current?.resume();}}>Continuar</button><button onClick={stop}>Parar</button></div>
  {hz&&<label>Volume do tom <input type="range" min="0" max="0.08" step="0.001" defaultValue="0.025" onChange={e=>{if(gain.current&&context.current)gain.current.gain.setTargetAtTime(Number(e.target.value),context.current.currentTime,.05);}}/></label>}
  {tracks.length>1&&<select aria-label="Escolher música" value={first?.id} onChange={e=>{const selected=tracks.find(t=>t.id===e.target.value);if(selected)setTracks([selected,...tracks.filter(t=>t!==selected)]);}}>{tracks.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select>}
  {searchUrl&&<a href={searchUrl} target="_blank" rel="noopener noreferrer">Abrir no YouTube</a>}
  {!first&&!hz&&<form onSubmit={e=>{e.preventDefault();const input=new FormData(e.currentTarget).get('video');if(typeof input==='string')void search(input,false);}}><label>Link do vídeo<input name="video" type="url" required placeholder="https://www.youtube.com/watch?v=…"/></label><button>Tocar aqui</button></form>}
 </section>;
});
