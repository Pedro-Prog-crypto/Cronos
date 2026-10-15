import React,{forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {api} from '../api';
import {musicCommand} from '../musicCommands';
import './MusicPlayer.css';
export type MusicHandle={handle:(text:string)=>boolean;stop:()=>void;exitView:()=>boolean;load:(result:any)=>void};
type Track={id:string;title:string};
type Media={audio_url?:string|null;video_url?:string|null;title?:string;player?:'official';id?:string};
const time=(n:number)=>`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;
function officialPlayer(id:string){const url=new URL('/music/player',location.href);url.hostname=location.hostname==='localhost'?'127.0.0.1':'localhost';url.search=new URLSearchParams({id,parentOrigin:location.origin}).toString();return url;}
export const MusicPlayer=forwardRef<MusicHandle,{local:boolean;onError:(message:string)=>void;onTalk?:()=>Promise<void>}>(({local,onError,onTalk},ref)=>{
 const [visible,setVisible]=useState(false),[tracks,setTracks]=useState<Track[]>([]),[index,setIndex]=useState(0),[media,setMedia]=useState<Media|null>(null),[message,setMessage]=useState(''),[hz,setHz]=useState<number|null>(null);
 const [fullscreenActive,setFullscreenActive]=useState(false);
 const [expanded,setExpanded]=useState(false),[qualityHelp,setQualityHelp]=useState(false);
 const container=useRef<HTMLElement>(null);
 const fullscreen=async()=>{setExpanded(true);try{if(document.fullscreenElement){await document.exitFullscreen();return;}if(container.current?.requestFullscreen)await container.current.requestFullscreen();else setMessage('Este navegador não liberou tela cheia. O player está ampliado dentro do Cronos.');}catch{setMessage('Tela cheia não foi liberada pelo navegador. O player foi ampliado dentro do Cronos.');}};
 useEffect(()=>{const changed=()=>setFullscreenActive(Boolean(document.fullscreenElement&&container.current?.contains(document.fullscreenElement)));document.addEventListener('fullscreenchange',changed);return()=>document.removeEventListener('fullscreenchange',changed);},[]);
 const exitView=()=>{if(!expanded&&!fullscreenActive)return false;if(document.fullscreenElement)void document.exitFullscreen().catch(()=>{});setExpanded(false);return true;};
 const [query,setQuery]=useState(''),[clip,setClip]=useState(false),[volume,setVolume]=useState(60),[elapsed,setElapsed]=useState(0),[duration,setDuration]=useState(0),[state,setState]=useState('Em espera');
 const audio=useRef<HTMLAudioElement>(null),video=useRef<HTMLVideoElement>(null),official=useRef<HTMLIFrameElement>(null),context=useRef<AudioContext|null>(null),gain=useRef<GainNode|null>(null),request=useRef<AbortController|null>(null),generation=useRef(0);
 const playerCommand=(command:string,value?:number)=>official.current?.contentWindow?.postMessage({type:'cronos:music:command',command,value},officialPlayer('').origin);
 const primary=()=>media?.audio_url?audio.current:video.current;
 const pause=()=>{playerCommand('pause');audio.current?.pause();video.current?.pause();if(context.current?.state==='running')void context.current.suspend().then(()=>setState('Pausado')).catch(()=>{});};
 const talk=()=>{pause();if(onTalk)void onTalk().catch(()=>setMessage('Não foi possível ativar o microfone. Confira a permissão do navegador.'));};
 const clear=()=>{generation.current++;request.current?.abort();pause();if(context.current&&context.current.state!=='closed')void context.current.close().catch(()=>{});context.current=null;gain.current=null;setTracks([]);setIndex(0);setMedia(null);setHz(null);setElapsed(0);setDuration(0);setState('Em espera');};
 const stop=()=>{clear();setVisible(false);setExpanded(false);setQualityHelp(false);setMessage('');if(document.fullscreenElement===container.current)void document.exitFullscreen().catch(()=>{});};
 const resume=async()=>{
  try{
   if(media?.player==='official'){playerCommand('play');return;}
   if(context.current){await context.current.resume();setState('Reproduzindo tom');return;}
   if(!primary()){setMessage('Aguarde a preparação da música ou escolha outro resultado.');return;}
   if(audio.current)await audio.current.play();
   if(video.current)await video.current.play();
  }catch{audio.current?.pause();video.current?.pause();setState('Clique para reproduzir');setMessage('Clique em Continuar para liberar o áudio. Se falhar novamente, escolha outro resultado.');}
 };
 const load=(result:any)=>{clear();setQuery(result.query||result.tracks?.[0]?.title||'');setVisible(true);setClip(Boolean(result.video));setTracks((result.tracks||[]).filter((t:any)=>/^[A-Za-z0-9_-]{11}$/.test(t.id)).slice(0,8));setMessage(result.message||'Preparando o player interno…');};
 const search=async(value:string,similar=false,asClip=clip)=>{
  clear();setQuery(value);setClip(asClip);setVisible(true);setMessage('Buscando música ou clipe…');const id=generation.current,controller=new AbortController();request.current=controller;
  try{const result=await(await api('/music/search?'+new URLSearchParams({query:value,similar:String(similar),video:String(asClip)}),{signal:controller.signal})).json();if(id!==generation.current)return;setTracks(result.tracks);setMessage(result.message||'Preparando o player interno…');}
  catch{if(!controller.signal.aborted)setMessage('A busca não respondeu. Tente outra música ou cole um link. Nenhuma aba externa foi aberta.');}
 };
 const frequency=(value:number)=>{
  if(value<20||value>2000||!Number.isFinite(value)){onError('Escolha um tom entre 20 e 2000 Hz.');return;}
  clear();setVisible(true);setHz(value);setMessage('Tom puro; comece com volume baixo.');const ctx=new AudioContext();context.current=ctx;
  const oscillator=ctx.createOscillator(),level=ctx.createGain();gain.current=level;oscillator.frequency.value=value;level.gain.setValueAtTime(0,ctx.currentTime);level.gain.linearRampToValueAtTime(.025,ctx.currentTime+.1);oscillator.connect(level);level.connect(ctx.destination);oscillator.start();void ctx.resume().then(()=>setState('Reproduzindo tom'));
 };
 const next=(delta=1)=>{pause();setElapsed(0);setIndex(old=>Math.max(0,Math.min(tracks.length-1,old+delta)));};
 useImperativeHandle(ref,()=>({stop,exitView,load,handle(text){const command=musicCommand(text);if(!command)return false;
  if(command.action==='search'){if(local){onError('Música online desativada no modo local.');return true;}void search(command.query,command.similar,Boolean(command.video));}
  else if(command.action==='frequency')frequency(command.hz);else if(command.action==='stop')stop();else if(command.action==='pause')pause();else if(command.action==='resume')void resume();else if(command.action==='next')next();else if(command.action==='previous')next(-1);return true;
 }}));
 const track=tracks[index];
 useEffect(()=>{
  if(!track)return;let alive=true;const controller=new AbortController();setMedia(null);setState('Preparando mídia');setDuration(0);setElapsed(0);
  void(async()=>{try{const result=await(await api('/music/resolve?'+new URLSearchParams({id:track.id,video:String(clip),native:'true'}),{signal:controller.signal})).json();if(result.player==='official')throw new Error('O servidor retornou o player antigo. Atualize o Cronos nesta mesma pasta para usar reprodução direta.');if(alive){setMedia(result);setMessage('');}}
  catch(error:any){if(alive&&!controller.signal.aborted){setState('Mídia indisponível');setMedia(null);setMessage(error instanceof Error?error.message:'Não foi possível preparar o fluxo de mídia. Escolha outro resultado.');}}})();
  return()=>{alive=false;controller.abort();audio.current?.pause();video.current?.pause();};
 },[track?.id,clip]);
 useEffect(()=>{if(audio.current)audio.current.volume=volume/100;if(video.current){video.current.volume=media?.audio_url?0:volume/100;video.current.muted=Boolean(media?.audio_url);}if(media)void resume();},[media]);
 useEffect(()=>{playerCommand('volume',volume);if(audio.current)audio.current.volume=volume/100;if(video.current)video.current.volume=media?.audio_url?0:volume/100;},[volume]);
 useEffect(()=>{
  if(media?.player!=='official')return;
  const receive=(event:MessageEvent)=>{
   if(event.origin!==officialPlayer('').origin||event.source!==official.current?.contentWindow)return;
   const data=event.data;
   if(data?.type==='cronos:music:ready'){playerCommand('volume',volume);setMessage('');}
   if(data?.type==='cronos:music:blocked'){setState('Clique para reproduzir');setMessage('Clique em Continuar para liberar a reprodução dentro do Kronos.');}
   if(data?.type==='cronos:music:progress'&&Number.isFinite(data.elapsed)&&Number.isFinite(data.duration)){setElapsed(data.elapsed);setDuration(data.duration);}
   if(data?.type==='cronos:music:state'){
    setState(({[-1]:'Carregando',0:'Finalizado',1:'Reproduzindo',2:'Pausado',3:'Carregando',5:'Pronto'} as Record<number,string>)[data.state]||'Em espera');
    if(data.state===1)setMessage('');
    if(data.state===0)ended();
   }
   if(data?.type==='cronos:music:error'){setState('Reprodução indisponível');setMessage([101,150].includes(data.code)?'O dono deste vídeo não permite reprodução incorporada. Escolha outro resultado.':data.code===100?'Este vídeo não está disponível. Escolha outro resultado.':data.code===153?'O YouTube recusou identificar este player. Feche e abra o Kronos atualizado.':'O player não conseguiu carregar. Verifique a conexão ou escolha outro resultado.');}
  };
  window.addEventListener('message',receive);return()=>window.removeEventListener('message',receive);
 },[media,index,tracks.length,volume]);
 useEffect(()=>()=>{request.current?.abort();audio.current?.pause();video.current?.pause();if(context.current&&context.current.state!=='closed')void context.current.close().catch(()=>{});},[]);
 const progress=()=>{const main=primary();if(!main)return;setElapsed(main.currentTime);setDuration(Number.isFinite(main.duration)?main.duration:0);if(media?.audio_url&&video.current&&Math.abs(video.current.currentTime-main.currentTime)>.35)video.current.currentTime=main.currentTime;};
 const seek=(value:number)=>{playerCommand('seek',value);if(audio.current)audio.current.currentTime=value;if(video.current)video.current.currentTime=value;setElapsed(value);};
 const failed=()=>{if(!track)return;audio.current?.pause();video.current?.pause();setState('Mídia indisponível');setMedia(null);setMessage('O fluxo de mídia falhou ou expirou. Pesquise novamente ou escolha outro resultado. Nenhum player do YouTube foi aberto.');};
 const ended=()=>{if(index+1<tracks.length)next();else setState('Finalizado');};
 if(!visible)return null;
 return <section ref={container} className={`music-player ${expanded?'music-expanded':''}`} aria-label="Música no Kronos"><header><strong>{hz?`${hz} Hz`:media?.title||track?.title||'MÚSICA E CLIPES'}</strong><button onClick={()=>setExpanded(v=>!v)} aria-label={expanded?'Reduzir player':'Maximizar player'}>{expanded?'▣':'□'}</button><button onClick={()=>void fullscreen()} aria-label={fullscreenActive?'Sair da tela cheia':'Tela cheia do Cronos'}>⛶</button><button onClick={talk} aria-label="Pausar música e falar com Cronos" title="Pausar música e falar com Cronos">🎙</button><button onClick={stop} aria-label="Fechar música">×</button></header>
  {!hz&&<form className="music-search" onSubmit={e=>{e.preventDefault();if(query.trim())void search(query,false,clip);}}><label>Buscar música, clipe ou colar link<input aria-label="Buscar música ou clipe" value={query} maxLength={240} onChange={e=>setQuery(e.target.value)} placeholder="Nome da música · cantor opcional · ou link"/></label><label><input type="checkbox" checked={clip} onChange={e=>setClip(e.target.checked)}/> Buscar clipe oficial</label><button disabled={!query.trim()}>Tocar aqui</button></form>}

  {media?.player==='official'&&<iframe ref={official} title="Player de música interno" src={officialPlayer(media.id||track.id).href} allow="autoplay; encrypted-media; fullscreen" allowFullScreen referrerPolicy="strict-origin-when-cross-origin"/>}
  {media?.video_url&&<video ref={video} src={media.video_url} playsInline preload="metadata" onTimeUpdate={media.audio_url?undefined:progress} onLoadedMetadata={progress} onPlaying={()=>setState('Reproduzindo')} onPause={()=>setState('Pausado')} onEnded={media.audio_url?undefined:ended} onError={failed}/>}
  {media?.audio_url&&<audio ref={audio} src={media.audio_url} preload="metadata" onTimeUpdate={progress} onLoadedMetadata={progress} onPlaying={()=>setState('Reproduzindo')} onPause={()=>setState('Pausado')} onEnded={ended} onError={failed}/>}
  {(media?.player==='official'||media?.video_url)&&<div className="music-actions"><button onClick={()=>void fullscreen()}>{fullscreenActive?'Sair da tela cheia':'Tela cheia'}</button>{media?.player==='official'&&<button aria-expanded={qualityHelp} onClick={()=>{setQualityHelp(v=>!v);setExpanded(true);}}>Qualidade do vídeo</button>}</div>}
  {qualityHelp&&media?.player==='official'&&<p className="music-quality-help">No vídeo, clique na engrenagem ⚙ → Qualidade. Escolha Automática, 480p, 720p, 1080p ou 1440p quando aparecerem. O YouTube mostra as opções disponíveis para este vídeo e dispositivo; o Cronos não força uma resolução. Se travar, escolha Automática ou 480p.</p>}
  {message&&<p role="status">{message}</p>}<div className="music-playback-status">{state}<span>{time(elapsed)} / {time(duration)}</span></div>
  <div className="music-actions"><button aria-label="Música anterior" disabled={index<=0} onClick={()=>next(-1)}>⏮</button><button onClick={pause}>Pausar</button><button onClick={()=>void resume()}>Continuar</button><button aria-label="Próxima música" disabled={index+1>=tracks.length} onClick={()=>next()}>⏭</button><button onClick={stop}>Parar</button></div>
  {!!tracks.length&&<><label>Posição da música<input aria-label="Posição da música" type="range" min="0" max={duration||1} value={Math.min(elapsed,duration||1)} disabled={!duration} onChange={e=>seek(Number(e.target.value))}/></label><label>Volume · {volume}%<input aria-label="Volume da música" type="range" min="0" max="100" value={volume} onChange={e=>setVolume(Number(e.target.value))}/></label><label>Fila<select aria-label="Escolher música" value={index} onChange={e=>{pause();setIndex(Number(e.target.value));}}>{tracks.map((t,i)=><option key={t.id} value={i}>{t.title}</option>)}</select></label></>}
  {hz&&<label>Volume do tom<input type="range" min="0" max="0.08" step="0.001" defaultValue="0.025" onChange={e=>{if(gain.current&&context.current)gain.current.gain.setTargetAtTime(Number(e.target.value),context.current.currentTime,.05);}}/></label>}

 </section>;
});
