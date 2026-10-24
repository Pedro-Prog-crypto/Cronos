import React,{useEffect,useMemo,useRef,useState} from 'react';
import {ArrowLeft,ArrowRight,ExternalLink,Film,Lock,LockOpen,Minus,RotateCw,X} from 'lucide-react';
import {api} from '../api';
import {spokenSlideIndex,visualSlides} from '../visualSlides';
import './StudyExplanationPanel.css';

type StoryImage={title:string;url:string;source_url:string;license:string;artist:string;provider?:string;kind?:'image'};
type StoryVideo={title:string;url:string;poster:string;source_url:string;license:string;artist:string;provider?:string;kind:'video'};
type StoryMedia={images:StoryImage[];videos:StoryVideo[]};
const mediaCache=new Map<string,StoryMedia>();
export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number};spokenChunk?:string;references?:Array<{title:string;url:string;excerpt?:string}>};
type Props={panels:StudyPanelItem[];activeId?:string|null;onActivate:(id:string)=>void;onMinimize:(id:string)=>void;onRestore:(id:string)=>void;onClose:(id:string)=>void;onToggleLock:(id:string)=>void};

const cleanLine=(line:string)=>line.replace(/^\s*#{1,3}\s+/,'').replace(/\*\*/g,'').replace(/^\s*(?:[-*]|\d+[.)])\s+/,'').replace(/`/g,'').trim();
function paragraphs(text:string){return text.split(/\n\s*\n/).map(block=>block.split(/\r?\n/).map(cleanLine).filter(Boolean).join(' ')).filter(Boolean);}
function spokenParagraphIndex(blocks:string[],spoken:string){
 const normalize=(value:string)=>value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
 const tokens=[...new Set((normalize(spoken).match(/[\p{L}]{4,}/gu)||[]).filter(token=>!['para','como','essa','esse','sobre','entre','agora','entao','depois','senhor'].includes(token)))];
 if(!tokens.length)return 0;let best=0,score=0;
 blocks.forEach((block,index)=>{const content=normalize(block);const next=tokens.reduce((sum,token)=>sum+(content.includes(token)?1:0),0);if(next>score){best=index;score=next;}});return best;
}

function StoryText({text,spokenChunk}:{text:string;spokenChunk?:string}){
 const blocks=useMemo(()=>paragraphs(text),[text]);
 const active=spokenParagraphIndex(blocks,spokenChunk||'');
 const current=useRef<HTMLParagraphElement|null>(null);
 useEffect(()=>{current.current?.scrollIntoView({block:'nearest',behavior:'smooth'});},[active,spokenChunk]);
 return <div className="study-story-transcript-text" aria-live="polite">{blocks.map((block,index)=><p key={`${index}-${block.slice(0,20)}`} ref={index===active?current:undefined} className={index===active&&spokenChunk?'is-speaking':''}>{block}</p>)}</div>;
}

function MediaTile({image,index,selected,onSelect}:{image:StoryImage;index:number;selected:boolean;onSelect:()=>void}){
 return <a href={image.source_url} target="_blank" rel="noreferrer" title={`${image.title}${image.artist?` · ${image.artist}`:''}`} className={`study-media-tile study-media-tile-${index}${selected?' is-selected':''}`} style={{'--tile-order':index} as React.CSSProperties} onClick={event=>{event.preventDefault();onSelect();}}>
  <img src={image.url} alt={image.title} loading={index<6?'eager':'lazy'} decoding="async" referrerPolicy="no-referrer"/>
  <span className="study-media-caption">{image.title}<small>{image.provider||'Imagem com fonte'}</small></span>
  <span className="study-media-source" aria-label="Abrir crédito da imagem"><ExternalLink size={13}/></span>
 </a>;
}

function StudyStory({panel,immersive}:{panel:StudyPanelItem;immersive:boolean}){
 const slides=useMemo(()=>visualSlides(panel.reply,panel.title),[panel.reply,panel.title]);
 const matched=spokenSlideIndex(slides,panel.spokenChunk||'',0);
 const [selected,setSelected]=useState(0),[manual,setManual]=useState(false),[images,setImages]=useState<StoryImage[]>([]),[videos,setVideos]=useState<StoryVideo[]>([]),[loadState,setLoadState]=useState<'waiting'|'loading'|'ready'|'failed'>('waiting'),[retry,setRetry]=useState(0),[selectedImage,setSelectedImage]=useState(0);
 const active=Math.min(slides.length-1,Math.max(0,panel.spokenChunk&&!manual?matched:selected));
 const slide=slides[active];
 const current=images[Math.min(selectedImage,Math.max(0,images.length-1))]||null;
 useEffect(()=>{if(panel.spokenChunk){setSelected(matched);setManual(false);}},[panel.spokenChunk,matched]);
 useEffect(()=>{
  let alive=true;
  const topic=`${panel.title} ${slide.title}`.replace(/\s+/g,' ').trim().slice(0,180);
  const key=topic.toLocaleLowerCase('pt-BR');
  const enoughContent=panel.reply.length>320;
  if(!enoughContent){setLoadState('waiting');return()=>{alive=false;};}
  const cached=mediaCache.get(key);
  if(cached){setImages(cached.images);setVideos(cached.videos);setLoadState(cached.images.length?'ready':'failed');setSelectedImage(0);return()=>{alive=false;};}
  const controller=new AbortController();setImages([]);setVideos([]);setSelectedImage(0);setLoadState('loading');
  // Separate request: slow/restricted media sources never delay the answer or audio.
  void api(`/studies/images?query=${encodeURIComponent(topic)}&limit=30&attempt=${retry}`,{signal:controller.signal})
   .then(response=>response.json()).then((data:any)=>{
    if(!alive)return;
    const safeImages:StoryImage[]=[...new Map<string,StoryImage>((data.images||[]).filter((item:StoryImage)=>/^https:\/\//i.test(item.url)&&/^https?:\/\//i.test(item.source_url)&&!item.url.toLowerCase().endsWith('.svg')).map((item:StoryImage)=>[item.url,item])).values()].slice(0,24);
    const safeVideos:StoryVideo[]=[...new Map<string,StoryVideo>((data.videos||[]).filter((item:StoryVideo)=>/^https:\/\/upload\.wikimedia\.org\//i.test(item.url)&&/^https:\/\/upload\.wikimedia\.org\//i.test(item.poster)&&/^https?:\/\//i.test(item.source_url)).map((item:StoryVideo)=>[item.url,item])).values()].slice(0,3);
    const result={images:safeImages,videos:safeVideos};
    if(safeImages.length)mediaCache.set(key,result);
    setImages(safeImages);setVideos(safeVideos);setLoadState(safeImages.length?'ready':'failed');setSelectedImage(0);
   }).catch(()=>{if(alive&&!controller.signal.aborted){setLoadState('failed');setImages([]);setVideos([]);}});
  return()=>{alive=false;controller.abort();};
 },[panel.title,slide.title,panel.reply.length,retry]);
 const select=(index:number)=>{setSelected(Math.max(0,Math.min(slides.length-1,index)));setManual(true);};
 const visibleImages=images.slice(0,immersive?16:8);
 return <div className={`study-dossier-body study-story${immersive?' is-immersive':''}`}>
  <div className="study-story-bar"><div className="study-story-kicker"><i className={panel.spokenChunk?'is-live':''}/><span>{panel.spokenChunk?'NARRAÇÃO SINCRONIZADA':'APRESENTAÇÃO VISUAL'}</span><b>CAPÍTULO {String(active+1).padStart(2,'0')} / {String(slides.length).padStart(2,'0')}</b></div>
   <nav className="study-story-track" aria-label="Capítulos da explicação">{slides.map((item,index)=><button type="button" key={item.id} className={index===active?'is-current':''} onClick={()=>select(index)} aria-current={index===active?'step':undefined} title={item.title}><i/>{String(index+1).padStart(2,'0')}</button>)}</nav>
  </div>
  <section className="study-story-scene" key={slide.id}>
   <div className="study-story-media-column">
    <div className="study-story-scene-head"><span>AGORA NA EXPLICAÇÃO</span><h3>{slide.title}</h3><b>{images.length?`${Math.min(images.length,immersive?16:8)} REFERÊNCIAS VISUAIS`:loadState==='loading'?'CARREGANDO MÍDIAS':'PAINEL DE CONTEXTO'}</b></div>
    <div className={`study-media-wall ${visibleImages.length?'has-media':''}`} aria-label={`Imagens relacionadas a ${slide.title}`}>
     {visibleImages.map((image,index)=><MediaTile key={`${slide.id}-${image.url}`} image={image} index={index} selected={index===selectedImage} onSelect={()=>setSelectedImage(index)}/>)}
     {videos.slice(0,immersive?2:1).map((video,index)=><a className={`study-media-video study-media-video-${index}`} key={video.url} href={video.source_url} target="_blank" rel="noreferrer" title={`Vídeo com licença aberta: ${video.title}`}>
      <video src={video.url} poster={video.poster} muted autoPlay loop playsInline preload="none"/>
      <span className="study-video-badge"><Film size={13}/> CLIPE DE FONTE ABERTA</span><span className="study-video-title">{video.title}</span>
     </a>)}
     {!visibleImages.length&&<div className={`study-media-empty ${loadState}`}>
      {loadState==='loading'?<><span className="study-media-orbit"/><b>BUSCANDO IMAGENS, MAPAS E VÍDEOS</b><small>A resposta já está pronta; as mídias chegam em paralelo.</small></>:loadState==='waiting'?<><span className="study-media-orbit"/><b>PREPARANDO A NARRATIVA VISUAL</b><small>Montando os capítulos antes de buscar material relacionado.</small></>:<><b>AS FONTES DE IMAGEM NÃO RESPONDERAM</b><small>Tente carregar as mídias novamente ou confira a conexão do Cronos.</small><button type="button" onClick={()=>setRetry(value=>value+1)}><RotateCw size={14}/> TENTAR NOVAMENTE</button><div className="study-media-fallback-links"><a href={`https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=${encodeURIComponent(topicForSearch(panel.title,slide.title))}`} target="_blank" rel="noreferrer">BUSCAR EM WIKIMEDIA <ExternalLink size={12}/></a><a href={`https://openverse.org/search/image?q=${encodeURIComponent(topicForSearch(panel.title,slide.title))}`} target="_blank" rel="noreferrer">BUSCAR EM OPENVERSE <ExternalLink size={12}/></a></div></>}
     </div>}
    </div>
    {current&&<div className="study-media-credit"><span>{current.title}{current.artist?` · ${current.artist}`:''}{current.license?` · ${current.license}`:''}</span><a href={current.source_url} target="_blank" rel="noreferrer">VER CRÉDITO <ExternalLink size={12}/></a><small>{images.length} imagens carregadas · {videos.length} vídeos relacionados</small></div>}
    <div className="study-story-nav"><button type="button" onClick={()=>select(active-1)} disabled={active===0} aria-label="Capítulo anterior"><ArrowLeft size={16}/> ANTERIOR</button><button type="button" onClick={()=>select(active+1)} disabled={active===slides.length-1} aria-label="Próximo capítulo">PRÓXIMO <ArrowRight size={16}/></button></div>
   </div>
   <aside className="study-story-narration">
    <div className="study-story-transcript-head"><span className={panel.spokenChunk?'is-live':''}/><b>TRANSCRIÇÃO DA EXPLICAÇÃO</b><small>{panel.spokenChunk?'ACOMPANHANDO A VOZ':'TEXTO COMPLETO'}</small></div>
    <h4>{slide.title}</h4>
    <div className="study-story-narration-scroll"><StoryText text={slide.text} spokenChunk={panel.spokenChunk}/></div>
    {panel.references?.length?<section className="study-story-sources"><b>FONTES CONSULTADAS</b>{panel.references.slice(0,5).map((reference,index)=><a key={`${reference.url}-${index}`} href={reference.url} target="_blank" rel="noreferrer">{reference.title||reference.url}<ExternalLink size={12}/></a>)}</section>:null}
    <details className="study-story-transcript"><summary>ABRIR TEXTO INTEGRAL</summary><div className="study-story-fulltext"><StoryText text={panel.reply}/></div></details>
   </aside>
  </section>
 </div>;
}
function topicForSearch(topic:string,title:string){return `${topic} ${title}`.replace(/\s+/g,' ').trim();}

export function StudyExplanationPanel({panels,activeId,onActivate,onMinimize,onRestore,onClose,onToggleLock}:Props){
 const ordered=panels.slice().sort((a,b)=>a.createdAt-b.createdAt);
 const active=ordered.find(panel=>panel.id===activeId&&!panel.minimized)||ordered.filter(panel=>!panel.minimized).at(-1);
 if(!panels.length)return null;
 return <div className="study-dossier-stack" aria-label="Explicações visuais do Cronos">
  {active&&<aside key={active.id} className={`study-dossier is-immersive${active.locked?' is-locked':''}`} aria-label={`Apresentação: ${active.title}`}>
   <header className="study-dossier-head"><div className="study-dossier-sigil" aria-hidden="true"><span/></div><div className="study-dossier-label"><small>SISTEMA · CRONOS</small><strong>APRESENTAÇÃO IMERSIVA</strong><span><i className={active.spokenChunk?'is-live':''}/>{active.spokenChunk?'FALA E VISUAIS SINCRONIZADOS':'EXPLICAÇÃO EM TELA'}</span></div>
    <nav className="study-story-topic-tabs" aria-label="Outros assuntos abertos">{ordered.filter(panel=>panel.id!==active.id).map(panel=><button key={panel.id} type="button" onClick={()=>onActivate(panel.id)} title={`Abrir ${panel.title}`}>{panel.title}</button>)}</nav>
    <div className="study-dossier-actions"><button type="button" onClick={()=>onToggleLock(active.id)} title={active.locked?'Desafixar explicação':'Fixar explicação'} aria-label={active.locked?'Desafixar explicação':'Fixar explicação'} aria-pressed={active.locked}>{active.locked?<Lock size={17}/>:<LockOpen size={17}/>}</button><button type="button" onClick={()=>onMinimize(active.id)} title="Minimizar apresentação" aria-label="Minimizar apresentação"><Minus size={19}/></button><button type="button" onClick={()=>onClose(active.id)} title="Fechar apresentação" aria-label="Fechar apresentação"><X size={20}/></button></div>
   </header>
   <div className="study-dossier-topic"><small>ASSUNTO</small><h2>{active.title}</h2></div>
   {active.reply?<StudyStory panel={active} immersive/>:<div className="study-dossier-body study-media-pending"><span className="study-media-orbit"/><b>PREPARANDO A EXPLICAÇÃO</b><small>Assim que chegar o primeiro conteúdo, a cena visual começa a ser montada.</small></div>}
   <footer className="study-dossier-foot"><span>{active.locked?'FIXADO PELO SENHOR':active.spokenChunk?'ACOMPANHANDO A NARRAÇÃO':'APRESENTAÇÃO INTERATIVA'}</span><b/></footer>
  </aside>}
  {ordered.some(panel=>panel.minimized)&&<div className="study-dossier-shelf" aria-label="Explicações minimizadas">{ordered.filter(panel=>panel.minimized).map(panel=><button key={panel.id} type="button" className={`study-dossier-restore${panel.locked?' is-locked':''}`} onClick={()=>onRestore(panel.id)} title={`Restaurar ${panel.title}`}><span>↗</span><b>{panel.title}</b>{panel.locked&&<Lock size={13}/>}</button>)}</div>}
 </div>;
}
