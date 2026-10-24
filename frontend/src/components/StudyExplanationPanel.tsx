import React from 'react';
import {ArrowLeft,ArrowRight,ExternalLink,ImageOff,Lock,LockOpen,Minus,X} from 'lucide-react';
import {useEffect,useMemo,useState} from 'react';
import {api} from '../api';
import {spokenSlideIndex,visualSlides} from '../visualSlides';
import './StudyExplanationPanel.css';

type StoryImage={title:string;url:string;source_url:string;license:string;artist:string};
const imageCache=new Map<string,StoryImage[]>();

export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number};spokenChunk?:string;references?:Array<{title:string;url:string;excerpt?:string}>};
type Props={panels:StudyPanelItem[];onMinimize:(id:string)=>void;onRestore:(id:string)=>void;onClose:(id:string)=>void;onToggleLock:(id:string)=>void;onMove:(id:string,left:number,top:number)=>void};

const TextBody=React.memo(function TextBody({text}:{text:string}){
 const blocks=text.split(/\n\s*\n/).filter(Boolean);
 return <div className="study-dossier-prose">{blocks.map((block,index)=>{
  const lines=block.split(/\r?\n/).filter(Boolean);
  return <section key={index}>{lines.map((line,n)=>{
   const heading=line.match(/^\s*(#{1,3})\s+(.+)/);
   if(heading){const Tag=(['h2','h3','h4'] as const)[heading[1].length-1];return <Tag key={n}>{heading[2]}</Tag>;}
   if(/^\s*[-*]\s+/.test(line))return <p className="dossier-bullet" key={n}>{line.replace(/^\s*[-*]\s+/,'')}</p>;
   if(/^\s*\d+[.)]\s+/.test(line))return <p className="dossier-bullet" key={n}>{line}</p>;
   return <p key={n}>{line}</p>;
  })}</section>;
 })}</div>;
});

function StudyStory({panel}:{panel:StudyPanelItem}){
 const slides=useMemo(()=>visualSlides(panel.reply,panel.title),[panel.reply,panel.title]);
 const matched=spokenSlideIndex(slides,panel.spokenChunk||'',0);
 const [selected,setSelected]=useState(0),[manual,setManual]=useState(false),[images,setImages]=useState<StoryImage[]>([]),[imageIndex,setImageIndex]=useState(0),[imageState,setImageState]=useState<'loading'|'ready'|'empty'>('loading');
 const active=Math.min(slides.length-1,Math.max(0,panel.spokenChunk&&!manual?matched:selected));
 const slide=slides[active];
 const image=images[Math.min(imageIndex,Math.max(0,images.length-1))]||null;
 useEffect(()=>{if(panel.spokenChunk){setSelected(matched);setManual(false);}},[panel.spokenChunk,matched]);
 useEffect(()=>{
  let alive=true;const key=slide.query.trim().toLocaleLowerCase('pt-BR');
  setImages(imageCache.get(key)||[]);setImageIndex(0);setImageState(imageCache.has(key)?(imageCache.get(key)!.length?'ready':'empty'):'loading');
  if(panel.reply.length<180){setImages([]);setImageState('empty');return()=>{alive=false;};}
  if(!imageCache.has(key)){
   const controller=new AbortController();
   // This request is intentionally independent of chat and voice generation. A slow
   // image service can never hold up the answer or narration.
   void api(`/studies/images?query=${encodeURIComponent(slide.query)}`,{signal:controller.signal}).then(response=>response.json()).then((data:any)=>{
    const found:StoryImage[]=[...new Map<string,StoryImage>((data.images||[]).filter((item:StoryImage)=>/^https:\/\/upload\.wikimedia\.org\//.test(item.url)&&/^https:\/\//.test(item.source_url)).map((item:StoryImage)=>[item.url,item])).values()].slice(0,3);
    imageCache.set(key,found);if(alive){setImages(found);setImageIndex(0);setImageState(found.length?'ready':'empty');}
   }).catch(()=>{if(alive&&!controller.signal.aborted){imageCache.set(key,[]);setImages([]);setImageState('empty');}});
   return()=>{alive=false;controller.abort();};
  }
  return()=>{alive=false;};
 },[slide.query,panel.reply.length]);
 const select=(index:number)=>{setSelected(Math.max(0,Math.min(slides.length-1,index)));setManual(true);};
 return <div className="study-dossier-body study-story" aria-live="polite">
  <div className="study-story-kicker"><span>SEQUÊNCIA EXPLICATIVA</span><b>{String(active+1).padStart(2,'0')} / {String(slides.length).padStart(2,'0')}</b></div>
  <nav className="study-story-track" aria-label="Partes da explicação">{slides.map((item,index)=><button type="button" key={item.id} className={index===active?'is-current':''} onClick={()=>select(index)} aria-current={index===active?'step':undefined} title={item.title}><i/>{index+1}</button>)}</nav>
  <section className="study-story-scene" key={slide.id}>
   <div className="study-story-scene-head"><span>CAPÍTULO {String(active+1).padStart(2,'0')}</span><h3>{slide.title}</h3></div>
   <figure className={`study-story-visual ${image?'has-image':''}`}>
    {image?<img src={image.url} alt={image.title} loading="lazy" decoding="async"/>:<div className="study-story-placeholder">{imageState==='loading'?<><i/><span>BUSCANDO UMA REFERÊNCIA VISUAL</span></>:<><ImageOff size={24}/><span>CONTEXTO VISUAL INDISPONÍVEL</span></>}</div>}
    {images.length>1&&<div className="study-story-thumbs" aria-label="Outras imagens deste capítulo">{images.map((item,index)=><button type="button" key={item.url} className={index===imageIndex?'is-selected':''} onClick={()=>setImageIndex(index)} title={item.title} aria-label={`Mostrar imagem ${index+1}: ${item.title}`}><img src={item.url} alt="" loading="lazy" decoding="async"/></button>)}</div>}
    <figcaption>{image?<><span>{image.title}{image.artist?` · ${image.artist}`:''}{image.license?` · ${image.license}`:''}</span><a href={image.source_url} target="_blank" rel="noreferrer" aria-label="Abrir a fonte da imagem">FONTE <ExternalLink size={11}/></a></>:<span>O texto continua disponível mesmo sem uma imagem relacionada.</span>}</figcaption>
   </figure>
   <div className="study-story-prose"><TextBody text={slide.text}/></div>
  </section>
  <div className="study-story-nav"><button type="button" onClick={()=>select(active-1)} disabled={active===0} aria-label="Parte anterior"><ArrowLeft size={15}/> ANTERIOR</button><button type="button" onClick={()=>select(active+1)} disabled={active===slides.length-1} aria-label="Próxima parte">PRÓXIMA <ArrowRight size={15}/></button></div>
  {panel.references?.length? <section className="study-story-sources"><b>FONTES CONSULTADAS</b>{panel.references.slice(0,4).map((reference,index)=><a key={`${reference.url}-${index}`} href={reference.url} target="_blank" rel="noreferrer">{reference.title||reference.url}<ExternalLink size={11}/></a>)}</section>:null}
  <details className="study-story-transcript"><summary>VER A EXPLICAÇÃO COMPLETA</summary><TextBody text={panel.reply}/></details>
 </div>;
}

export function StudyExplanationPanel({panels,onMinimize,onRestore,onClose,onToggleLock,onMove}:Props){
 const drag=React.useRef<{id:string;pointerId:number;startX:number;startY:number;left:number;top:number}|null>(null);
 const [dragging,setDragging]=React.useState<string|null>(null);
 const ordered=panels.slice().sort((a,b)=>a.slot-b.slot);
 if(!panels.length)return null;
 const defaultPosition=(slot:number)=>{
  const width=typeof window==='undefined'?1440:window.innerWidth,height=typeof window==='undefined'?900:window.innerHeight;
  const cardWidth=Math.min(560,Math.max(280,width*.30));
  const lane=width<=650?width*.92:width*.325;
  const initial=width<=650?width*.07+slot*lane:width*.025+slot*lane;
  return {left:Math.max(0,Math.min(width-cardWidth,initial)),top:height*.16};
 };
 const beginDrag=(event:React.PointerEvent<HTMLElement>,panel:StudyPanelItem)=>{
  if((event.target as HTMLElement).closest('button'))return;
  event.preventDefault();
  const rect=event.currentTarget.closest('.study-dossier')?.getBoundingClientRect();if(!rect)return;
  const position=panel.position??{left:rect.left,top:rect.top};
  drag.current={id:panel.id,pointerId:event.pointerId,startX:event.clientX,startY:event.clientY,left:position.left,top:position.top};
  setDragging(panel.id);
  event.currentTarget.setPointerCapture(event.pointerId);
 };
 const moveDrag=(event:React.PointerEvent<HTMLElement>)=>{
  const active=drag.current;if(!active||active.pointerId!==event.pointerId)return;
  const card=event.currentTarget.closest('.study-dossier') as HTMLElement|null;
  const width=typeof window==='undefined'?1440:window.innerWidth,height=typeof window==='undefined'?900:window.innerHeight;
  const cardWidth=card?.getBoundingClientRect().width??Math.min(560,Math.max(280,width*.30));
  const cardHeight=card?.getBoundingClientRect().height??Math.min(720,height*.68);
  onMove(active.id,Math.max(0,Math.min(width-cardWidth,active.left+event.clientX-active.startX)),Math.max(0,Math.min(height-cardHeight,active.top+event.clientY-active.startY)));
 };
 const endDrag=(event:React.PointerEvent<HTMLElement>)=>{if(drag.current?.pointerId===event.pointerId){drag.current=null;setDragging(null);}};
 return <div className="study-dossier-stack" aria-label="Explicações de estudo">
  {ordered.filter(panel=>!panel.minimized).map(panel=>{const position=panel.position??defaultPosition(panel.slot);return <aside key={panel.id} style={{left:position.left,top:position.top,zIndex:dragging===panel.id?5:undefined}} className={`study-dossier${panel.locked?' is-locked':''}${dragging===panel.id?' is-dragging':''}`} aria-label={`Explicação: ${panel.title}`}>
    <header className="study-dossier-head" title="Arraste para mover este painel" onPointerDown={event=>beginDrag(event,panel)} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag}><div className="study-dossier-sigil" aria-hidden="true"><span/></div><div className="study-dossier-label"><small>SISTEMA · CRONOS</small><strong>JANELA DE MISSÃO</strong><span><i/>{panel.locked?'REGISTRO FIXADO':panel.reply?'CONCEITO REGISTRADO':'ANÁLISE EM ANDAMENTO'}</span></div><div className="study-dossier-actions">
      <button type="button" onPointerDown={event=>event.stopPropagation()} onClick={()=>onToggleLock(panel.id)} title={panel.locked?'Desafixar painel':'Fixar painel'} aria-label={panel.locked?'Desafixar painel':'Fixar painel'} aria-pressed={panel.locked}>{panel.locked?<Lock size={16}/>:<LockOpen size={16}/>}</button>
      <button type="button" onPointerDown={event=>event.stopPropagation()} onClick={()=>onMinimize(panel.id)} title="Minimizar painel" aria-label="Minimizar painel"><Minus size={17}/></button>
      <button type="button" onPointerDown={event=>event.stopPropagation()} onClick={()=>onClose(panel.id)} title="Fechar painel" aria-label="Fechar painel"><X size={18}/></button>
     </div></header>
    <div className="study-dossier-topic"><small>ASSUNTO</small><h2>{panel.title}</h2></div>
    {panel.reply?<StudyStory panel={panel}/>:<div className="study-dossier-body"><p className="study-dossier-pending">Preparando a explicação…</p></div>}
    <footer className="study-dossier-foot"><span>{panel.locked?'FIXADO PELO SENHOR':panel.spokenChunk?'ACOMPANHANDO A NARRAÇÃO':'EXPLICAÇÃO VISUAL'}</span><b/></footer>
   </aside>;})}
  {ordered.some(panel=>panel.minimized)&&<div className="study-dossier-shelf" aria-label="Painéis minimizados">{ordered.filter(panel=>panel.minimized).map(panel=><button key={panel.id} type="button" className={`study-dossier-restore${panel.locked?' is-locked':''}`} onClick={()=>onRestore(panel.id)} title={`Restaurar ${panel.title}`}><span>↗</span><b>{panel.title}</b>{panel.locked&&<Lock size={13}/>}</button>)}</div>}
 </div>;
}
