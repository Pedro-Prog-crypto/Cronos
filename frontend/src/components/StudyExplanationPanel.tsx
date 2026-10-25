import React,{useEffect,useMemo,useState} from 'react';
import {ExternalLink,RotateCw,X} from 'lucide-react';
import {api} from '../api';
import {spokenSlideIndex,visualSlides} from '../visualSlides';
import './StudyExplanationPanel.css';

type StoryImage={title:string;url:string;proxy_url:string;source_url:string;license:string;artist:string;provider?:string;kind?:'image'};
type StoryMedia={images:StoryImage[]};
const mediaCache=new Map<string,{media:StoryMedia;expires:number}>();
export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number};spokenChunk?:string;spokenChunkIndex?:number;references?:Array<{title:string;url:string;excerpt?:string}>};
type Props={panels:StudyPanelItem[];activeId?:string|null;speaking?:boolean;generating?:boolean;onClose:(id:string)=>void};

function StudyStory({panel,speaking=false,generating=false,onClose}:{panel:StudyPanelItem;speaking?:boolean;generating?:boolean;onClose:()=>void}){
 const slides=useMemo(()=>visualSlides(panel.reply,panel.title),[panel.reply,panel.title]);
 const active=spokenSlideIndex(slides,panel.spokenChunk||'',0),slide=slides[active];
 const [images,setImages]=useState<StoryImage[]>([]),[imageSources,setImageSources]=useState<Record<string,string>>({}),[loadState,setLoadState]=useState<'waiting'|'loading'|'ready'|'failed'>('waiting'),[photosLoading,setPhotosLoading]=useState(false),[failedCount,setFailedCount]=useState(0),[retry,setRetry]=useState(0);
 const visibleImages=images.filter(image=>Boolean(imageSources[image.proxy_url]));
 const moving=speaking||generating||visibleImages.length>0;
 useEffect(()=>{
  let alive=true;
  const key=slide.query.toLocaleLowerCase('pt-BR');
  if(panel.reply.length<=80){setLoadState('waiting');return()=>{alive=false;};}
  const cached=mediaCache.get(key);
  if(cached&&cached.expires>Date.now()){
   setImages(cached.media.images);setLoadState(cached.media.images.length?'ready':'failed');return()=>{alive=false;};
  }
  if(cached)mediaCache.delete(key);
  const controller=new AbortController();setLoadState('loading');
  void api(`/studies/images?query=${encodeURIComponent(slide.query)}&limit=12&attempt=${retry}`,{signal:controller.signal})
   .then(response=>response.json()).then((data:any)=>{
    if(!alive)return;
    const unique=new Set<string>();
    const results:StoryImage[]=(data.images||[]).filter((item:StoryImage)=>{
     if(!/^https:\/\//i.test(item.url)||!/^\/studies\/media\/[A-Za-z0-9_-]+$/.test(item.proxy_url)||!/^https?:\/\//i.test(item.source_url)||item.url.toLowerCase().endsWith('.svg')||unique.has(item.url))return false;
     unique.add(item.url);return true;
    }).slice(0,16);
    const media={images:results};
    if(results.length)mediaCache.set(key,{media,expires:Date.now()+20*60*1000});
    setImages(results);setFailedCount(0);setLoadState(results.length?'ready':'failed');
   }).catch(()=>{if(alive&&!controller.signal.aborted)setLoadState('failed');});
  return()=>{alive=false;controller.abort();};
 },[slide.query,panel.reply.length,retry]);
 useEffect(()=>{
  if(!images.length){setImageSources({});setFailedCount(0);setPhotosLoading(false);return;}
  const controller=new AbortController(),objectUrls:string[]=[];setImageSources({});setFailedCount(0);setPhotosLoading(true);
  let next=0,successes=0,failures=0;
  const worker=async()=>{while(next<images.length&&successes<12&&!controller.signal.aborted){const image=images[next++];try{
   const response=await api(image.proxy_url,{signal:controller.signal}),blob=await response.blob();
   if(!blob.type.startsWith('image/'))throw new Error('A fonte não devolveu uma imagem.');
   const objectUrl=URL.createObjectURL(blob),probe=new Image();probe.src=objectUrl;try{await probe.decode();}catch(error){URL.revokeObjectURL(objectUrl);throw error;}
   objectUrls.push(objectUrl);successes++;setImageSources(previous=>({...previous,[image.proxy_url]:objectUrl}));
  }catch{if(!controller.signal.aborted){failures++;setFailedCount(failures);}}}};
  void Promise.all(Array.from({length:3},()=>worker())).finally(()=>{if(!controller.signal.aborted)setPhotosLoading(false);});
  return()=>{controller.abort();objectUrls.forEach(URL.revokeObjectURL);};
 },[images]);
 const showFallback=loadState==='failed'&&!visibleImages.length||images.length>0&&!photosLoading&&!visibleImages.length&&failedCount>=images.length;
 const duration=`${Math.max(30,visibleImages.length*5.2)}s`;
 return <div className="study-cinema" style={{'--film-duration':duration} as React.CSSProperties}>
  <div className={`study-film-stage${moving?' is-moving':''}`} aria-label="Mural de imagens relacionadas à explicação">
   {[visibleImages,visibleImages.slice().reverse()].map((row,rowIndex)=><div className={`study-film-row ${rowIndex?'is-lower':''}`} key={rowIndex}>
    <div className="study-film-track">
     {[0,1].flatMap(copy=>row.map((image,index)=><figure className="study-film-frame" key={`${rowIndex}-${copy}-${index}-${image.proxy_url}`}>
       <img src={imageSources[image.proxy_url]} alt={copy===0?image.title:''} decoding="async" onError={()=>setImageSources(previous=>{const next={...previous};delete next[image.proxy_url];return next;})}/>
      </figure>))}
    </div>
   </div>)}
  </div>
  {(loadState==='loading'&&!images.length||photosLoading&&!visibleImages.length)&&<div className="study-cinema-status"><i/><span>BUSCANDO IMAGENS PARA A EXPLICAÇÃO</span></div>}
  {showFallback&&<div className="study-cinema-fallback"><span>AS IMAGENS NÃO CARREGARAM</span><button type="button" onClick={()=>setRetry(value=>value+1)}><RotateCw size={15}/> TENTAR OUTRAS IMAGENS</button><div><a href={`https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=${encodeURIComponent(slide.query)}`} target="_blank" rel="noreferrer">WIKIMEDIA <ExternalLink size={12}/></a><a href={`https://openverse.org/search/image?q=${encodeURIComponent(slide.query)}`} target="_blank" rel="noreferrer">OPENVERSE <ExternalLink size={12}/></a></div></div>}
  {visibleImages.length>0&&<a className="study-cinema-credit" href={visibleImages[0].source_url} target="_blank" rel="noreferrer" aria-label="Abrir a fonte das imagens" title="Abrir a fonte das imagens"><ExternalLink size={14}/></a>}
  <button className="study-cinema-close" type="button" onClick={onClose} aria-label="Fechar apresentação" title="Fechar"><X size={20}/></button>
 </div>;
}

export function StudyExplanationPanel({panels,activeId,speaking=false,generating=false,onClose}:Props){
 const ordered=panels.slice().sort((a,b)=>a.createdAt-b.createdAt);
 const active=activeId?ordered.find(panel=>panel.id===activeId&&!panel.minimized):undefined;
 if(!active)return null;
 return <StudyStory key={active.id} panel={active} speaking={speaking} generating={generating} onClose={()=>onClose(active.id)}/>;
}
