import React,{useEffect,useMemo,useRef,useState} from 'react';
import {ExternalLink,Lock,LockOpen,Minus,RotateCw,X} from 'lucide-react';
import {api} from '../api';
import {spokenSlideIndex,visualSlides} from '../visualSlides';
import './StudyExplanationPanel.css';

type StoryImage={title:string;url:string;proxy_url:string;source_url:string;license:string;artist:string;provider?:string;kind?:'image'};
type StoryVideo={title:string;url:string;poster:string;poster_proxy_url:string;source_url:string;license:string;artist:string;provider?:string;kind:'video'};
type StoryMedia={images:StoryImage[];videos:StoryVideo[]};
const mediaCache=new Map<string,{media:StoryMedia;expires:number}>();
export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number};spokenChunk?:string;references?:Array<{title:string;url:string;excerpt?:string}>};
type Props={panels:StudyPanelItem[];activeId?:string|null;speaking?:boolean;generating?:boolean;audioLevel?:{current:number};onActivate:(id:string)=>void;onMinimize:(id:string)=>void;onRestore:(id:string)=>void;onClose:(id:string)=>void;onToggleLock:(id:string)=>void};

function StudyStory({panel,speaking=false,generating=false,audioLevel}:{panel:StudyPanelItem;speaking?:boolean;generating?:boolean;audioLevel?:{current:number}}){
 const slides=useMemo(()=>visualSlides(panel.reply,panel.title),[panel.reply,panel.title]);
 const matched=spokenSlideIndex(slides,panel.spokenChunk||'',0);
 const [selected,setSelected]=useState(0),[manual,setManual]=useState(false),[images,setImages]=useState<StoryImage[]>([]),[videos,setVideos]=useState<StoryVideo[]>([]),[loadState,setLoadState]=useState<'waiting'|'loading'|'ready'|'failed'>('waiting'),[retry,setRetry]=useState(0),[selectedImage,setSelectedImage]=useState(0),[imageSources,setImageSources]=useState<Record<string,string>>({}),[failedImageKeys,setFailedImageKeys]=useState<string[]>([]),[photosLoading,setPhotosLoading]=useState(false),[rotation,setRotation]=useState<number[]>(Array(8).fill(0)),[connections,setConnections]=useState(false),[emphasis,setEmphasis]=useState(false),[finished,setFinished]=useState(false);
 const previousSlide=useRef(slides[0]?.id);
 const heardSpeech=useRef(false);
 const coreRef=useRef<HTMLDivElement>(null);
 const active=Math.min(slides.length-1,Math.max(0,panel.spokenChunk&&!manual?matched:selected));
 const slide=slides[active];
 const visibleImages=images.filter(image=>Boolean(imageSources[image.proxy_url])).slice(0,8);
 const posterProxy=videos[0]?.poster_proxy_url;
 const videoPoster=posterProxy?images.find(image=>image.proxy_url===posterProxy&&imageSources[image.proxy_url]):undefined;
 const decodedImages=images.filter(image=>Boolean(imageSources[image.proxy_url])&&image.proxy_url!==posterProxy);
 const photoSlots=Array.from({length:8},(_,slot)=>decodedImages.filter((_,index)=>index%8===slot));
 if(videoPoster)photoSlots[7]=[videoPoster];
 const current=photoSlots[selectedImage]?.[rotation[selectedImage]||0]||photoSlots[selectedImage]?.[0]||photoSlots.flat()[0]||null;
 const companionText=(panel.spokenChunk||slide.text).replace(/^#+\s*/gm,'').slice(0,220);
 const highlightDuration=`${Math.max(1400,Math.min(11000,(companionText.trim().split(/\s+/).length/2.7)*1000))}ms`;
 useEffect(()=>{if(panel.spokenChunk){setSelected(matched);setManual(false);}},[panel.spokenChunk,matched]);
 useEffect(()=>{if(previousSlide.current===slide.id)return;previousSlide.current=slide.id;const sceneNumber=Number(slide.id.replace('scene-',''));const showConnections=sceneNumber>0&&sceneNumber%3===0,showEmphasis=sceneNumber>0&&sceneNumber%4===0;setConnections(showConnections);setEmphasis(showEmphasis);if(!showConnections&&!showEmphasis)return;const connectionTimer=window.setTimeout(()=>setConnections(false),2600),emphasisTimer=window.setTimeout(()=>setEmphasis(false),520);return()=>{window.clearTimeout(connectionTimer);window.clearTimeout(emphasisTimer);};},[slide.id]);
 useEffect(()=>{if(!speaking||!audioLevel||!coreRef.current)return;let frame=0;const draw=()=>{const level=Math.max(0,Math.min(1,audioLevel.current));coreRef.current?.style.setProperty('--audio-level',level.toFixed(3));frame=window.requestAnimationFrame(draw);};frame=window.requestAnimationFrame(draw);return()=>window.cancelAnimationFrame(frame);},[speaking,audioLevel]);
 useEffect(()=>{if(speaking)heardSpeech.current=true;if(speaking||generating){setFinished(false);return;}if(heardSpeech.current)setFinished(true);},[speaking,generating]);
 useEffect(()=>{setRotation(Array(8).fill(0));},[images]);
 useEffect(()=>{const timers:number[]=[];photoSlots.forEach((slot,index)=>{if(slot.length<2)return;const advance=()=>setRotation(previous=>previous.map((value,slotIndex)=>slotIndex===index?(value+1)%slot.length:value));const start=window.setTimeout(()=>{advance();timers.push(window.setInterval(advance,5200) as unknown as number);},index*480+5200);timers.push(start);});return()=>timers.forEach(timer=>{window.clearTimeout(timer);window.clearInterval(timer);});},[images,photoSlots.map(slot=>slot.length).join(',')]);
 useEffect(()=>{
  if(!images.length){setImageSources({});setFailedImageKeys([]);setPhotosLoading(false);return;}
  const controller=new AbortController(),objectUrls:string[]=[];setImageSources({});setFailedImageKeys([]);setPhotosLoading(true);
  // Keep trying the search results until eight images actually decode from the
  // local proxy. A dead hotlink in the first results no longer leaves a blank wall.
  let next=0,successes=0;
  const worker=async()=>{while(next<images.length&&successes<12&&!controller.signal.aborted){const index=next++,image=images[index];try{
   const response=await api(image.proxy_url,{signal:controller.signal}),blob=await response.blob();
   if(!blob.type.startsWith('image/'))throw new Error('Resposta sem imagem');
   const objectUrl=URL.createObjectURL(blob),probe=new Image();probe.src=objectUrl;try{await probe.decode();}catch(error){URL.revokeObjectURL(objectUrl);throw error;}objectUrls.push(objectUrl);successes++;
   setImageSources(previous=>({...previous,[image.proxy_url]:objectUrl}));
  }catch{if(!controller.signal.aborted)setFailedImageKeys(previous=>previous.includes(image.proxy_url)?previous:[...previous,image.proxy_url]);}}};
  void Promise.all(Array.from({length:3},()=>worker())).finally(()=>{if(!controller.signal.aborted)setPhotosLoading(false);});
  return()=>{controller.abort();objectUrls.forEach(URL.revokeObjectURL);};
 },[images]);
 useEffect(()=>{
  let alive=true;
  const key=slide.query.toLocaleLowerCase('pt-BR');
  const enoughContent=panel.reply.length>80;
  if(!enoughContent){setLoadState('waiting');return()=>{alive=false;};}
  const cached=mediaCache.get(key);
  if(cached&&cached.expires>Date.now()){setImages(cached.media.images);setVideos(cached.media.videos);setLoadState(cached.media.images.length?'ready':'failed');setSelectedImage(0);return()=>{alive=false;};}
  if(cached)mediaCache.delete(key);
  const controller=new AbortController();setVideos([]);setSelectedImage(0);setLoadState('loading');
  // Fetch media independently and in small batches, so it never holds up speech.
  void api(`/studies/images?query=${encodeURIComponent(slide.query)}&limit=12&attempt=${retry}`,{signal:controller.signal})
   .then(response=>response.json()).then((data:any)=>{
    if(!alive)return;
    const unique=new Set<string>();
    const safeImages:StoryImage[]=(data.images||[]).filter((item:StoryImage)=>{
     if(!/^https:\/\//i.test(item.url)||!/^\/studies\/media\/[A-Za-z0-9_-]+$/.test(item.proxy_url)||!/^https?:\/\//i.test(item.source_url)||item.url.toLowerCase().endsWith('.svg')||unique.has(item.url))return false;
     unique.add(item.url);return true;
    }).slice(0,16);
    const safeVideos:StoryVideo[]=[...new Map<string,StoryVideo>((data.videos||[]).filter((item:StoryVideo)=>/^https:\/\/upload\.wikimedia\.org\//i.test(item.url)&&/^https:\/\/upload\.wikimedia\.org\//i.test(item.poster)&&/^\/studies\/media\/[A-Za-z0-9_-]+$/.test(item.poster_proxy_url)&&/^https?:\/\//i.test(item.source_url)).map((item:StoryVideo)=>[item.url,item])).values()].slice(0,1);
    for(const video of safeVideos){if(!unique.has(video.poster)){const poster:StoryImage={title:video.title,url:video.poster,proxy_url:video.poster_proxy_url,source_url:video.source_url,license:video.license,artist:video.artist,provider:video.provider||'Wikimedia Commons',kind:'image'};safeImages.splice(Math.min(7,safeImages.length),0,poster);unique.add(video.poster);}}
    const result={images:safeImages,videos:safeVideos};
    if(safeImages.length)mediaCache.set(key,{media:result,expires:Date.now()+20*60*1000});
    setImages(safeImages);setVideos(safeVideos);setLoadState(safeImages.length?'ready':'failed');setSelectedImage(0);
   }).catch(()=>{if(alive&&!controller.signal.aborted){setLoadState('failed');setVideos([]);}});
  return()=>{alive=false;controller.abort();};
 },[slide.query,panel.reply.length,retry]);
 const select=(index:number)=>{setSelected(Math.max(0,Math.min(slides.length-1,index)));setManual(true);};
 const showFallback=loadState==='failed'&&!visibleImages.length||(images.length>0&&!photosLoading&&!visibleImages.length&&failedImageKeys.length>=images.length);
 return <div className="study-dossier-body study-story is-cinematic">
  <div className="study-story-bar"><div className="study-story-kicker"><i className={speaking?'is-live':''}/><span>{speaking?'VISUAL ACOMPANHANDO A FALA':'APRESENTAÇÃO VISUAL'}</span><b>CENA {String(active+1).padStart(2,'0')} / {String(slides.length).padStart(2,'0')}</b></div>
   <nav className="study-story-track" aria-label="Cenas da explicação">{slides.map((item,index)=><button type="button" key={item.id} className={index===active?'is-current':''} onClick={()=>select(index)} aria-current={index===active?'step':undefined} title={item.title}><i/>{String(index+1).padStart(2,'0')}</button>)}</nav>
  </div>
  <section className={`study-cinematic-scene${emphasis?' has-emphasis':''}${finished?' is-finished':''}`} aria-label={`Cena: ${slide.title}`}>
   <div className="study-cinematic-side">
    <div className="study-cinematic-heading"><span>{panel.title.toLocaleUpperCase('pt-BR')}</span><h3>{slide.title}</h3><small>{panel.spokenChunk?'AGORA NA EXPLICAÇÃO':'APRESENTAÇÃO VISUAL'}</small></div>
    <div ref={coreRef} className={`study-visual-core${speaking?' is-speaking':''}${emphasis?' is-emphasis':''}${finished?' is-finished':''}`} aria-hidden="true"><i/><b/><span/><div className="study-visual-core-bars">{Array.from({length:32},(_,index)=><i key={index} style={{'--bar-angle':`${index*11.25}deg`,'--bar-height':`${3+(index*7%8)}px`,'--bar-delay':`${index%8*55}ms`} as React.CSSProperties}/>)}</div></div>
    <small className="study-core-caption">CRONOS · ASSISTENTE</small>
    <p className="study-spoken-excerpt" key={`${slide.id}-${panel.spokenChunk||'idle'}`} style={{'--highlight-duration':highlightDuration} as React.CSSProperties} aria-live="polite"><span className="study-spoken-muted">{companionText}</span><span className="study-spoken-highlight" aria-hidden="true">{companionText}</span></p>
   </div>
   <div className="study-photo-area">
    <div className="study-photo-wall" aria-label={`Mural de imagens relacionadas a ${slide.title}`}>
     {photoSlots.map((slot,index)=>{
      const image=finished?(current||slot[0]):slot[rotation[index]||0]||slot[0],selected=index===selectedImage,src=image?imageSources[image.proxy_url]:'';
      return image?<button type="button" key={`slot-${index}-${image.proxy_url}`} className={`study-photo-tile${selected?' is-selected':''}${index===7&&videos[0]?' has-video':''}`} style={{'--photo-order':index} as React.CSSProperties} onClick={()=>setSelectedImage(index)} title={`Exibir ${image.title}`} aria-label={`Posição ${index+1}: ${image.title}`}>
       <img src={src} alt={image.title} decoding="async" onError={()=>{setFailedImageKeys(previous=>previous.includes(image.proxy_url)?previous:[...previous,image.proxy_url]);setImageSources(previous=>{const next={...previous};delete next[image.proxy_url];return next;});}}/>
       {index===7&&videos[0]&&<video className="study-photo-video" src={videos[0].url} poster={src} muted autoPlay loop playsInline preload="metadata" aria-label={videos[0].title}/>}
       <span className="study-photo-label">{String(index+1).padStart(2,'0')} · {image.provider||'REFERÊNCIA'}</span><span className="study-photo-caption">{image.title}</span>
      </button>:<div key={`slot-${index}-empty`} className="study-photo-tile is-empty" aria-hidden="true"><span>{photosLoading||loadState==='loading'?'CARREGANDO MÍDIA':'AGUARDANDO REFERÊNCIA'}</span></div>;
     })}
     {(loadState==='loading'&&!images.length||photosLoading&&!visibleImages.length)&&<div className="study-cinematic-loading"><span className="study-media-orbit"/><b>BUSCANDO FOTOS PARA ESTA CENA</b></div>}
     {showFallback&&<div className="study-cinematic-fallback"><b>AS FONTES NÃO ENTREGARAM FOTOS CARREGÁVEIS</b><small>Vou tentar novamente com outras imagens relacionadas à cena.</small><button type="button" onClick={()=>setRetry(value=>value+1)}><RotateCw size={15}/> TENTAR NOVAMENTE</button><div className="study-media-fallback-links"><a href={`https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=${encodeURIComponent(slide.query)}`} target="_blank" rel="noreferrer">WIKIMEDIA <ExternalLink size={12}/></a><a href={`https://openverse.org/search/image?q=${encodeURIComponent(slide.query)}`} target="_blank" rel="noreferrer">OPENVERSE <ExternalLink size={12}/></a></div></div>}
    </div>
    <div className="study-wall-ticker"><b>{finished?'CONCLUÍDO':'EXPLICAÇÃO'}</b><span>{finished?'Etapa visual encerrada':slide.title}</span><small>CENA {String(active+1).padStart(2,'0')} / {String(slides.length).padStart(2,'0')}</small></div>
   </div>
   {connections&&<svg className="study-connection-layer" viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true"><path d="M145 300 C270 300 290 100 420 100"/><path d="M145 300 C300 300 340 230 570 230"/><path d="M145 300 C310 300 370 370 720 370"/><path d="M145 300 C280 300 370 500 900 500"/></svg>}
   {current&&<div className="study-cinematic-creditline"><span>{current.title}{current.artist?` · ${current.artist}`:''}{current.license?` · ${current.license}`:''}</span><a href={current.source_url} target="_blank" rel="noreferrer">FONTE <ExternalLink size={13}/></a></div>}
   {videos[0]&&<a className="study-cinematic-video" href={videos[0].source_url} target="_blank" rel="noreferrer" title={`Vídeo de fonte aberta: ${videos[0].title}`}><span>VÍDEO RELACIONADO</span><b>{videos[0].title}</b><ExternalLink size={14}/></a>}
  </section>
  {panel.references?.length?<nav className="study-cinematic-sources" aria-label="Fontes consultadas">{panel.references.slice(0,4).map((reference,index)=><a key={`${reference.url}-${index}`} href={reference.url} target="_blank" rel="noreferrer">{reference.title||reference.url}<ExternalLink size={12}/></a>)}</nav>:null}
 </div>;
}

export function StudyExplanationPanel({panels,activeId,speaking=false,generating=false,audioLevel,onActivate,onMinimize,onRestore,onClose,onToggleLock}:Props){
 const ordered=panels.slice().sort((a,b)=>a.createdAt-b.createdAt);
 const active=ordered.find(panel=>panel.id===activeId&&!panel.minimized)||ordered.filter(panel=>!panel.minimized).at(-1);
 if(!panels.length)return null;
 return <div className="study-dossier-stack" aria-label="Explicações visuais do Cronos">
   {active&&<aside key={active.id} className={`study-dossier is-immersive${active.locked?' is-locked':''}`} aria-label={`Apresentação: ${active.title}`}>
   <header className="study-dossier-head"><div className="study-dossier-sigil" aria-hidden="true"><span/></div><div className="study-dossier-label"><small>SISTEMA · CRONOS</small><strong>APRESENTAÇÃO IMERSIVA</strong><span><i className={speaking?'is-live':''}/>{speaking?'VISUAIS ACOMPANHANDO A FALA':'EXPLICAÇÃO EM TELA'}</span></div>
    <nav className="study-story-topic-tabs" aria-label="Outros assuntos abertos">{ordered.filter(panel=>panel.id!==active.id).map(panel=><button key={panel.id} type="button" onClick={()=>onActivate(panel.id)} title={`Abrir ${panel.title}`}>{panel.title}</button>)}</nav>
    <div className="study-dossier-actions"><button type="button" onClick={()=>onToggleLock(active.id)} title={active.locked?'Desafixar explicação':'Fixar explicação'} aria-label={active.locked?'Desafixar explicação':'Fixar explicação'} aria-pressed={active.locked}>{active.locked?<Lock size={17}/>:<LockOpen size={17}/>}</button><button type="button" onClick={()=>onMinimize(active.id)} title="Minimizar apresentação" aria-label="Minimizar apresentação"><Minus size={19}/></button><button type="button" onClick={()=>onClose(active.id)} title="Fechar apresentação" aria-label="Fechar apresentação"><X size={20}/></button></div>
   </header>
   <div className="study-dossier-topic"><small>ASSUNTO</small><h2>{active.title}</h2></div>
   {active.reply?<StudyStory panel={active} speaking={speaking} generating={generating} audioLevel={audioLevel}/>:<div className="study-dossier-body study-media-pending"><span className="study-media-orbit"/><b>PREPARANDO A CENA VISUAL</b><small>As imagens acompanham os trechos da fala.</small></div>}
   <footer className="study-dossier-foot"><span>{active.locked?'FIXADO PELO SENHOR':speaking?'IMAGEM SINCRONIZADA À FALA':'APRESENTAÇÃO INTERATIVA'}</span><b/></footer>
  </aside>}
  {ordered.some(panel=>panel.minimized)&&<div className="study-dossier-shelf" aria-label="Explicações minimizadas">{ordered.filter(panel=>panel.minimized).map(panel=><button key={panel.id} type="button" className={`study-dossier-restore${panel.locked?' is-locked':''}`} onClick={()=>onRestore(panel.id)} title={`Restaurar ${panel.title}`}><span>↗</span><b>{panel.title}</b>{panel.locked&&<Lock size={13}/>}</button>)}</div>}
 </div>;
}
