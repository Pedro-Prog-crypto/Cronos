import React,{useEffect,useMemo,useState} from 'react';
import {ExternalLink,RotateCw,X} from 'lucide-react';
import {api} from '../api';
import {spokenSlideIndex,visualSlides} from '../visualSlides';
import {isNearDuplicateHash,normalizedImageTitle,normalizedImageUrl,selectWallImages,wallGridLayout} from '../studyImageDedupe';
import './StudyExplanationPanel.css';

type StoryImage={title:string;url:string;proxy_url:string;source_url:string;license:string;artist:string;provider?:string;kind?:'image'};
type StoryMedia={images:StoryImage[]};
const mediaCache=new Map<string,{media:StoryMedia;expires:number}>();
export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number};spokenChunk?:string;spokenChunkIndex?:number;references?:Array<{title:string;url:string;excerpt?:string}>};
type Props={panels:StudyPanelItem[];activeId?:string|null;speaking?:boolean;generating?:boolean;onClose:(id:string)=>void};

function StudyStory({panel,onClose}:{panel:StudyPanelItem;onClose:()=>void}){
 const slides=useMemo(()=>visualSlides(panel.reply,panel.title),[panel.reply,panel.title]);
 const active=spokenSlideIndex(slides,panel.spokenChunk||'',0);
 const collectionQuery=slides[0]?.query||panel.title;
 const [images,setImages]=useState<StoryImage[]>([]),[imageSources,setImageSources]=useState<Record<string,string>>({}),[loadState,setLoadState]=useState<'waiting'|'loading'|'ready'|'failed'>('waiting'),[photosLoading,setPhotosLoading]=useState(false),[failedCount,setFailedCount]=useState(0),[retry,setRetry]=useState(0);
 const visibleImages=images.filter(image=>Boolean(imageSources[image.proxy_url]));
 const wallImages=useMemo(()=>selectWallImages(visibleImages,active,8),[visibleImages,active]);
 const wallLayout=wallGridLayout(wallImages.length);
 useEffect(()=>{
  let alive=true;
  const key=`${collectionQuery.toLocaleLowerCase('pt-BR')}|tentativa:${retry}`;
  if(panel.reply.length<=80){setLoadState('waiting');return()=>{alive=false;};}
  const cached=mediaCache.get(key);
  if(cached&&cached.expires>Date.now()){
   setImages(cached.media.images);setLoadState(cached.media.images.length?'ready':'failed');return()=>{alive=false;};
  }
  if(cached)mediaCache.delete(key);
  const controller=new AbortController();setLoadState('loading');
  void api(`/studies/images?query=${encodeURIComponent(collectionQuery)}&limit=36&attempt=${retry}`,{signal:controller.signal})
   .then(response=>response.json()).then((data:any)=>{
    if(!alive)return;
    const urls=new Set<string>(),titles=new Set<string>();
    const results:StoryImage[]=(data.images||[]).filter((item:StoryImage)=>{
     const url=normalizedImageUrl(item.url),title=normalizedImageTitle(item.title);
     const lowQuality=/\b(?:shutterstock|alamy|dreamstime|stock photo|clipart|sticker|transparent background|png cutout)\b/i.test(`${item.title} ${item.provider||''}`);
     if(!/^https:\/\//i.test(item.url)||!/^\/studies\/media\/[A-Za-z0-9_-]+$/.test(item.proxy_url)||!/^https?:\/\//i.test(item.source_url)||item.url.toLowerCase().endsWith('.svg')||lowQuality||urls.has(url)||title.length>5&&titles.has(title))return false;
     urls.add(url);if(title.length>5)titles.add(title);return true;
    }).slice(0,36);
    const media={images:results};
    if(results.length)mediaCache.set(key,{media,expires:Date.now()+20*60*1000});
    setImages(results);setFailedCount(0);setLoadState(results.length?'ready':'failed');
   }).catch(()=>{if(alive&&!controller.signal.aborted)setLoadState('failed');});
  return()=>{alive=false;controller.abort();};
 },[collectionQuery,panel.reply.length,retry]);
 useEffect(()=>{
  if(!images.length){setImageSources({});setFailedCount(0);setPhotosLoading(false);return;}
  const controller=new AbortController(),objectUrls:string[]=[];setImageSources({});setFailedCount(0);setPhotosLoading(true);
  let next=0,successes=0,failures=0;const acceptedHashes:string[]=[];
  const worker=async()=>{while(next<images.length&&successes<36&&!controller.signal.aborted){const image=images[next++];try{
   const response=await api(image.proxy_url,{signal:controller.signal}),blob=await response.blob();
   if(!blob.type.startsWith('image/'))throw new Error('A fonte não devolveu uma imagem.');
   const objectUrl=URL.createObjectURL(blob),probe=new Image();probe.src=objectUrl;try{await probe.decode();}catch(error){URL.revokeObjectURL(objectUrl);throw error;}
   const canvas=document.createElement('canvas');canvas.width=9;canvas.height=8;const context=canvas.getContext('2d',{willReadFrequently:true});if(context){context.drawImage(probe,0,0,9,8);const pixels=context.getImageData(0,0,9,8).data;let hash='',transparent=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]<220)transparent++;if(transparent>pixels.length/4*.12){URL.revokeObjectURL(objectUrl);continue;}for(let y=0;y<8;y++)for(let x=0;x<8;x++){const left=(y*9+x)*4,right=left+4;const gray=(index:number)=>pixels[index]*.299+pixels[index+1]*.587+pixels[index+2]*.114;hash+=gray(left)>gray(right)?'1':'0';}if(isNearDuplicateHash(hash,acceptedHashes)){URL.revokeObjectURL(objectUrl);continue;}acceptedHashes.push(hash);}
   objectUrls.push(objectUrl);successes++;setImageSources(previous=>({...previous,[image.proxy_url]:objectUrl}));
  }catch{if(!controller.signal.aborted){failures++;setFailedCount(failures);}}}};
  void Promise.all(Array.from({length:6},()=>worker())).finally(()=>{if(!controller.signal.aborted)setPhotosLoading(false);});
  return()=>{controller.abort();objectUrls.forEach(URL.revokeObjectURL);};
 },[images]);
 const showFallback=loadState==='failed'&&!visibleImages.length||images.length>0&&!photosLoading&&!visibleImages.length;
 return <div className="study-cinema" aria-label={`Imagens relacionadas a ${panel.title}`}>
  <div className="study-visual-mosaic" style={{'--wall-columns':wallLayout.columns,'--wall-rows':wallLayout.rows} as React.CSSProperties}>
   {wallImages.map((image,index)=><figure className="study-visual-tile" key={`${active}-${image.proxy_url}`} style={{'--tile-index':index,...(index===wallImages.length-1&&wallLayout.lastSpan>1?{gridColumn:`span ${wallLayout.lastSpan}`}:{})} as React.CSSProperties}>
    <img src={imageSources[image.proxy_url]} alt={image.title} decoding="async" onError={()=>setImageSources(previous=>{const next={...previous};delete next[image.proxy_url];return next;})}/>
   </figure>)}
  </div>
  {(loadState==='loading'&&!images.length||photosLoading&&!visibleImages.length)&&<div className="study-cinema-status"><i/><span>BUSCANDO IMAGENS PARA A EXPLICAÇÃO</span></div>}
  {showFallback&&<div className="study-cinema-fallback"><span>SEM IMAGENS CONFIÁVEIS NESTA BUSCA</span><button type="button" onClick={()=>setRetry(value=>value+1)}><RotateCw size={15}/> TENTAR OUTRAS IMAGENS</button><div><a href={`https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=${encodeURIComponent(collectionQuery)}`} target="_blank" rel="noreferrer">WIKIMEDIA <ExternalLink size={12}/></a><a href={`https://openverse.org/search/image?q=${encodeURIComponent(collectionQuery)}`} target="_blank" rel="noreferrer">OPENVERSE <ExternalLink size={12}/></a></div></div>}
  {visibleImages.length>0&&<a className="study-cinema-credit" href={visibleImages[0].source_url} target="_blank" rel="noreferrer" aria-label="Abrir a fonte das imagens" title="Abrir a fonte das imagens"><ExternalLink size={14}/></a>}
  <button className="study-cinema-close" type="button" onClick={onClose} aria-label="Fechar apresentação" title="Fechar"><X size={20}/></button>
 </div>;
}

export function StudyExplanationPanel({panels,activeId,onClose}:Props){
 const ordered=panels.slice().sort((a,b)=>a.createdAt-b.createdAt);
 const active=activeId?ordered.find(panel=>panel.id===activeId&&!panel.minimized):undefined;
 if(!active)return null;
 return <StudyStory key={active.id} panel={active} onClose={()=>onClose(active.id)}/>;
}
