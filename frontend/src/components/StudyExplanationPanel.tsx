import React,{useEffect,useMemo,useState} from 'react';
import {ExternalLink,Lock,LockOpen,Minus,RotateCw,X} from 'lucide-react';
import {api} from '../api';
import {spokenSlideIndex,visualSlides} from '../visualSlides';
import './StudyExplanationPanel.css';

type StoryImage={title:string;url:string;proxy_url:string;source_url:string;license:string;artist:string;provider?:string;kind?:'image'};
type StoryVideo={title:string;url:string;poster:string;source_url:string;license:string;artist:string;provider?:string;kind:'video'};
type StoryMedia={images:StoryImage[];videos:StoryVideo[]};
const mediaCache=new Map<string,StoryMedia>();
export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number};spokenChunk?:string;references?:Array<{title:string;url:string;excerpt?:string}>};
type Props={panels:StudyPanelItem[];activeId?:string|null;onActivate:(id:string)=>void;onMinimize:(id:string)=>void;onRestore:(id:string)=>void;onClose:(id:string)=>void;onToggleLock:(id:string)=>void};

function StudyStory({panel}:{panel:StudyPanelItem}){
 const slides=useMemo(()=>visualSlides(panel.reply,panel.title),[panel.reply,panel.title]);
 const matched=spokenSlideIndex(slides,panel.spokenChunk||'',0);
 const [selected,setSelected]=useState(0),[manual,setManual]=useState(false),[images,setImages]=useState<StoryImage[]>([]),[videos,setVideos]=useState<StoryVideo[]>([]),[loadState,setLoadState]=useState<'waiting'|'loading'|'ready'|'failed'>('waiting'),[retry,setRetry]=useState(0),[selectedImage,setSelectedImage]=useState(0),[imageSources,setImageSources]=useState<Record<string,string>>({}),[failedImageKeys,setFailedImageKeys]=useState<string[]>([]);
 const active=Math.min(slides.length-1,Math.max(0,panel.spokenChunk&&!manual?matched:selected));
 const slide=slides[active];
 const current=images[selectedImage]||null;
 useEffect(()=>{if(panel.spokenChunk){setSelected(matched);setManual(false);}},[panel.spokenChunk,matched]);
 useEffect(()=>{
  if(!images.length){setImageSources({});setFailedImageKeys([]);return;}
  const controller=new AbortController(),objectUrls:string[]=[];setImageSources({});setFailedImageKeys([]);
  // Seven small images recreate the reference's changing visual wall; no transcript
  // and no huge concurrent background downloads.
  images.slice(0,7).forEach((image,index)=>void api(image.proxy_url,{signal:controller.signal}).then(async response=>{
   const blob=await response.blob();
   if(!blob.type.startsWith('image/'))throw new Error('Resposta sem imagem');
   const objectUrl=URL.createObjectURL(blob);objectUrls.push(objectUrl);
   setImageSources(previous=>({...previous,[image.proxy_url]:objectUrl}));
  }).catch(()=>{if(!controller.signal.aborted){setFailedImageKeys(previous=>previous.includes(image.proxy_url)?previous:[...previous,image.proxy_url]);setSelectedImage(selectedIndex=>selectedIndex===index?index+1:selectedIndex);}}));
  return()=>{controller.abort();objectUrls.forEach(URL.revokeObjectURL);};
 },[images]);
 useEffect(()=>{
  let alive=true;
  const key=slide.query.toLocaleLowerCase('pt-BR');
  const enoughContent=panel.reply.length>80;
  if(!enoughContent){setLoadState('waiting');return()=>{alive=false;};}
  const cached=mediaCache.get(key);
  if(cached){setImages(cached.images);setVideos(cached.videos);setLoadState(cached.images.length?'ready':'failed');setSelectedImage(0);return()=>{alive=false;};}
  const controller=new AbortController();setImages([]);setVideos([]);setSelectedImage(0);setLoadState('loading');
  // Fetch media independently and in small batches, so it never holds up speech.
  void api(`/studies/images?query=${encodeURIComponent(slide.query)}&limit=12&attempt=${retry}`,{signal:controller.signal})
   .then(response=>response.json()).then((data:any)=>{
    if(!alive)return;
    const unique=new Set<string>();
    const safeImages:StoryImage[]=(data.images||[]).filter((item:StoryImage)=>{
     if(!/^https:\/\//i.test(item.url)||!/^\/studies\/media\/[A-Za-z0-9_-]+$/.test(item.proxy_url)||!/^https?:\/\//i.test(item.source_url)||item.url.toLowerCase().endsWith('.svg')||unique.has(item.url))return false;
     unique.add(item.url);return true;
    }).slice(0,12);
    const safeVideos:StoryVideo[]=[...new Map<string,StoryVideo>((data.videos||[]).filter((item:StoryVideo)=>/^https:\/\/upload\.wikimedia\.org\//i.test(item.url)&&/^https:\/\/upload\.wikimedia\.org\//i.test(item.poster)&&/^https?:\/\//i.test(item.source_url)).map((item:StoryVideo)=>[item.url,item])).values()].slice(0,1);
    const result={images:safeImages,videos:safeVideos};
    if(safeImages.length)mediaCache.set(key,result);
    setImages(safeImages);setVideos(safeVideos);setLoadState(safeImages.length?'ready':'failed');setSelectedImage(0);
   }).catch(()=>{if(alive&&!controller.signal.aborted){setLoadState('failed');setImages([]);setVideos([]);}});
  return()=>{alive=false;controller.abort();};
 },[slide.query,panel.reply.length,retry]);
 const select=(index:number)=>{setSelected(Math.max(0,Math.min(slides.length-1,index)));setManual(true);};
 const showFallback=loadState==='failed'||(images.length>0&&images.slice(0,7).every(image=>failedImageKeys.includes(image.proxy_url)));
 return <div className="study-dossier-body study-story is-cinematic">
  <div className="study-story-bar"><div className="study-story-kicker"><i className={panel.spokenChunk?'is-live':''}/><span>{panel.spokenChunk?'VISUAL ACOMPANHANDO A FALA':'APRESENTAÇÃO VISUAL'}</span><b>CENA {String(active+1).padStart(2,'0')} / {String(slides.length).padStart(2,'0')}</b></div>
   <nav className="study-story-track" aria-label="Cenas da explicação">{slides.map((item,index)=><button type="button" key={item.id} className={index===active?'is-current':''} onClick={()=>select(index)} aria-current={index===active?'step':undefined} title={item.title}><i/>{String(index+1).padStart(2,'0')}</button>)}</nav>
  </div>
  <section className="study-cinematic-scene" key={slide.id} aria-label={`Cena: ${slide.title}`}>
   <div className="study-cinematic-heading"><span>{panel.title.toLocaleUpperCase('pt-BR')}</span><h3>{slide.title}</h3><small>{panel.spokenChunk?'FOTOS ACOMPANHANDO A FALA':'PAREDE VISUAL'}</small></div>
   <div className="study-photo-wall" aria-label={`Fotos relacionadas a ${slide.title}`}>
    {images.slice(0,7).map((image,index)=>{
     const featured=index===selectedImage,src=imageSources[image.proxy_url],failed=failedImageKeys.includes(image.proxy_url);
     if(failed)return null;
     return <button type="button" key={image.proxy_url} className={`study-photo-tile${featured?' is-featured':''}`} style={{'--photo-order':index} as React.CSSProperties} onClick={()=>setSelectedImage(index)} title={`Exibir ${image.title}`} aria-label={`Exibir imagem ${index+1}: ${image.title}`}>
      {src?<img src={src} alt={image.title} decoding="async" onError={()=>{setFailedImageKeys(previous=>previous.includes(image.proxy_url)?previous:[...previous,image.proxy_url]);setSelectedImage(currentIndex=>currentIndex===index?index+1:currentIndex);}}/>:<span className="study-photo-loading"><span className="study-media-orbit"/></span>}
      <span className="study-photo-caption">{image.title}</span>
      {featured&&<span className="study-photo-focus"><b>{slide.title}</b><small>{image.license||image.provider||'IMAGEM DE REFERÊNCIA'}</small></span>}
     </button>;
    })}
    {loadState==='loading'&&!images.length&&<div className="study-cinematic-loading"><span className="study-media-orbit"/><b>BUSCANDO FOTOS PARA ESTA CENA</b></div>}
    {showFallback&&<div className="study-cinematic-fallback"><b>AS FONTES NÃO ENTREGARAM FOTOS CARREGÁVEIS</b><small>Vou tentar novamente com outras imagens relacionadas à cena.</small><button type="button" onClick={()=>setRetry(value=>value+1)}><RotateCw size={15}/> TENTAR NOVAMENTE</button><div className="study-media-fallback-links"><a href={`https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=${encodeURIComponent(slide.query)}`} target="_blank" rel="noreferrer">WIKIMEDIA <ExternalLink size={12}/></a><a href={`https://openverse.org/search/image?q=${encodeURIComponent(slide.query)}`} target="_blank" rel="noreferrer">OPENVERSE <ExternalLink size={12}/></a></div></div>}
   </div>
   {current&&<div className="study-cinematic-creditline"><span>{current.title}{current.artist?` · ${current.artist}`:''}{current.license?` · ${current.license}`:''}</span><a href={current.source_url} target="_blank" rel="noreferrer">FONTE <ExternalLink size={13}/></a></div>}
   {videos[0]&&<a className="study-cinematic-video" href={videos[0].source_url} target="_blank" rel="noreferrer" title={`Vídeo de fonte aberta: ${videos[0].title}`}><span>VÍDEO RELACIONADO</span><b>{videos[0].title}</b><ExternalLink size={14}/></a>}
  </section>
  {panel.references?.length?<nav className="study-cinematic-sources" aria-label="Fontes consultadas">{panel.references.slice(0,4).map((reference,index)=><a key={`${reference.url}-${index}`} href={reference.url} target="_blank" rel="noreferrer">{reference.title||reference.url}<ExternalLink size={12}/></a>)}</nav>:null}
 </div>;
}

export function StudyExplanationPanel({panels,activeId,onActivate,onMinimize,onRestore,onClose,onToggleLock}:Props){
 const ordered=panels.slice().sort((a,b)=>a.createdAt-b.createdAt);
 const active=ordered.find(panel=>panel.id===activeId&&!panel.minimized)||ordered.filter(panel=>!panel.minimized).at(-1);
 if(!panels.length)return null;
 return <div className="study-dossier-stack" aria-label="Explicações visuais do Cronos">
  {active&&<aside key={active.id} className={`study-dossier is-immersive${active.locked?' is-locked':''}`} aria-label={`Apresentação: ${active.title}`}>
   <header className="study-dossier-head"><div className="study-dossier-sigil" aria-hidden="true"><span/></div><div className="study-dossier-label"><small>SISTEMA · CRONOS</small><strong>APRESENTAÇÃO IMERSIVA</strong><span><i className={active.spokenChunk?'is-live':''}/>{active.spokenChunk?'VISUAIS ACOMPANHANDO A FALA':'EXPLICAÇÃO EM TELA'}</span></div>
    <nav className="study-story-topic-tabs" aria-label="Outros assuntos abertos">{ordered.filter(panel=>panel.id!==active.id).map(panel=><button key={panel.id} type="button" onClick={()=>onActivate(panel.id)} title={`Abrir ${panel.title}`}>{panel.title}</button>)}</nav>
    <div className="study-dossier-actions"><button type="button" onClick={()=>onToggleLock(active.id)} title={active.locked?'Desafixar explicação':'Fixar explicação'} aria-label={active.locked?'Desafixar explicação':'Fixar explicação'} aria-pressed={active.locked}>{active.locked?<Lock size={17}/>:<LockOpen size={17}/>}</button><button type="button" onClick={()=>onMinimize(active.id)} title="Minimizar apresentação" aria-label="Minimizar apresentação"><Minus size={19}/></button><button type="button" onClick={()=>onClose(active.id)} title="Fechar apresentação" aria-label="Fechar apresentação"><X size={20}/></button></div>
   </header>
   <div className="study-dossier-topic"><small>ASSUNTO</small><h2>{active.title}</h2></div>
   {active.reply?<StudyStory panel={active}/>:<div className="study-dossier-body study-media-pending"><span className="study-media-orbit"/><b>PREPARANDO A CENA VISUAL</b><small>As imagens acompanham os trechos da fala.</small></div>}
   <footer className="study-dossier-foot"><span>{active.locked?'FIXADO PELO SENHOR':active.spokenChunk?'IMAGEM SINCRONIZADA À FALA':'APRESENTAÇÃO INTERATIVA'}</span><b/></footer>
  </aside>}
  {ordered.some(panel=>panel.minimized)&&<div className="study-dossier-shelf" aria-label="Explicações minimizadas">{ordered.filter(panel=>panel.minimized).map(panel=><button key={panel.id} type="button" className={`study-dossier-restore${panel.locked?' is-locked':''}`} onClick={()=>onRestore(panel.id)} title={`Restaurar ${panel.title}`}><span>↗</span><b>{panel.title}</b>{panel.locked&&<Lock size={13}/>}</button>)}</div>}
 </div>;
}
