import React,{useEffect,useMemo,useRef,useState} from 'react';
import {ExternalLink,RotateCw,X} from 'lucide-react';
import {api} from '../api';
import {spokenSlideIndex,visualSlides} from '../visualSlides';
import {isNearDuplicateHash,normalizedImageUrl,partitionWallImages} from '../studyImageDedupe';
import './StudyExplanationPanel.css';

type StoryImage={title:string;url:string;proxy_url:string;source_url:string;license:string;artist:string;provider?:string;kind?:'image';aspect?:number};
type StoryMedia={images:StoryImage[]};
const PHOTO_WALL_TARGET=12;
const PHOTO_WALL_DEADLINE_MS=6500;
export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number};spokenChunk?:string;spokenChunkIndex?:number;references?:Array<{title:string;url:string;excerpt?:string}>};
async function decodeImage(image:HTMLImageElement,signal:AbortSignal){
 if(signal.aborted)throw new DOMException('Imagem interrompida.','AbortError');
 await new Promise<void>((resolve,reject)=>{
  const cancel=()=>reject(new DOMException('Imagem interrompida.','AbortError'));
  signal.addEventListener('abort',cancel,{once:true});
  image.decode().then(resolve,reject).finally(()=>signal.removeEventListener('abort',cancel));
 });
}
type Props={panels:StudyPanelItem[];activeId?:string|null;speaking:boolean;generating?:boolean;onClose:(id:string)=>void};

function StudyStory({panel,onClose,speaking}:{panel:StudyPanelItem;onClose:()=>void;speaking:boolean}){
 const slides=useMemo(()=>visualSlides(panel.reply,panel.title),[panel.reply,panel.title]);
 const active=spokenSlideIndex(slides,panel.spokenChunk||'',0);
 const [mediaSlide,setMediaSlide]=useState(active);
 useEffect(()=>{if(active===mediaSlide)return;const timer=window.setTimeout(()=>setMediaSlide(active),650);return()=>window.clearTimeout(timer);},[active,mediaSlide]);
 const collectionQuery=slides[mediaSlide]?.query||panel.title;
 const [images,setImages]=useState<StoryImage[]>([]),[imageSources,setImageSources]=useState<Record<string,string>>({});
 const [loadState,setLoadState]=useState<'loading'|'ready'|'failed'>('loading');
 const [photosLoading,setPhotosLoading]=useState(false),[retry,setRetry]=useState(0),[failure,setFailure]=useState('');
 const assets=useRef(new Map<string,{url:string;hash:string;aspect:number}>());
 const mediaCache=useRef(new Map<string,{media:StoryMedia;expires:number}>());
 const visibleImages=images.filter(image=>Boolean(imageSources[image.proxy_url]));
 const [screenAspect,setScreenAspect]=useState(()=>window.innerWidth/Math.max(1,window.innerHeight));
 useEffect(()=>{const resize=()=>setScreenAspect(window.innerWidth/Math.max(1,window.innerHeight));window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);},[]);
 const wallRows=useMemo(()=>{
  const totalAspect=visibleImages.reduce((sum,item)=>sum+(item.aspect||1.5),0);
  const rows=Math.max(1,Math.min(4,Math.round(Math.sqrt(totalAspect/screenAspect))));
  return partitionWallImages(visibleImages,0,rows);
 },[visibleImages,screenAspect]);
 useEffect(()=>{
  if(!speaking)return;
  const timer=window.setInterval(()=>setRetry(value=>value+1),30000);
  return()=>window.clearInterval(timer);
 },[speaking]);
 useEffect(()=>()=>{assets.current.forEach(asset=>URL.revokeObjectURL(asset.url));assets.current.clear();},[]);
 useEffect(()=>{
  let disposed=false;
  const controller=new AbortController();
  let timer=window.setTimeout(()=>controller.abort(),7500);
  const key=`${collectionQuery.toLocaleLowerCase('pt-BR')}|${retry}`;
  setLoadState('loading');setFailure('');
  const run=async()=>{
   const cached=mediaCache.current.get(key);
   let candidates:StoryImage[];
   if(cached&&cached.expires>Date.now())candidates=cached.media.images;
   else{
    const response=await api(`/studies/images?query=${encodeURIComponent(collectionQuery)}&limit=18&attempt=${retry%21}`,{signal:controller.signal});
    const data=await response.json();
    const urls=new Set<string>();
    candidates=(data.images||[]).filter((item:StoryImage)=>{
     const identity=normalizedImageUrl(item.url);
     if(!/^https:\/\//i.test(item.url)||!/^\/studies\/media\/[A-Za-z0-9_-]+$/.test(item.proxy_url)||!/^https?:\/\//i.test(item.source_url)||urls.has(identity))return false;
     urls.add(identity);return true;
    }).slice(0,18);
    // Failures and empty searches are retried on a later visit, never cached for 20 minutes.
    if(candidates.length){
     if(mediaCache.current.size>=12)mediaCache.current.delete(mediaCache.current.keys().next().value!);
     mediaCache.current.set(key,{media:{images:candidates},expires:Date.now()+120000});
    }
    else throw new Error(data.message||'Nenhuma imagem relacionada encontrada.');
   }
   if(disposed)return;
   if(controller.signal.aborted)throw new DOMException('Busca interrompida.','AbortError');
   candidates=[...candidates].sort((left,right)=>Number(assets.current.has(normalizedImageUrl(left.url)))-Number(assets.current.has(normalizedImageUrl(right.url))));
   window.clearTimeout(timer);timer=window.setTimeout(()=>controller.abort(),PHOTO_WALL_DEADLINE_MS);
   setPhotosLoading(true);
   let next=0;const accepted:StoryImage[]=[],sources:Record<string,string>={},hashes:string[]=[];
   const worker=async()=>{while(next<candidates.length&&accepted.length<PHOTO_WALL_TARGET&&!controller.signal.aborted&&!disposed){
    const candidate=candidates[next++],identity=normalizedImageUrl(candidate.url);
    let temporary:string|undefined;
    try{
     let asset=assets.current.get(identity);
     if(!asset){
      const response=await api(candidate.proxy_url,{signal:controller.signal}),blob=await response.blob();
      if(!blob.type.startsWith('image/')||blob.size>4*1024*1024)throw new Error('Imagem inválida.');
      if(disposed||controller.signal.aborted)return;
      temporary=URL.createObjectURL(blob);const probe=new Image();probe.src=temporary;await decodeImage(probe,controller.signal);
      if(disposed||controller.signal.aborted)return;
      if(probe.naturalWidth<120||probe.naturalHeight<90)continue;
      const canvas=document.createElement('canvas');canvas.width=9;canvas.height=8;
      const context=canvas.getContext('2d',{willReadFrequently:true});let hash='';
      if(context){
       context.drawImage(probe,0,0,9,8);const pixels=context.getImageData(0,0,9,8).data;
       let transparent=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]<220)transparent++;
       if(transparent>pixels.length/4*.12)continue;
       const gray=(index:number)=>pixels[index]*.299+pixels[index+1]*.587+pixels[index+2]*.114;
       for(let y=0;y<8;y++)for(let x=0;x<8;x++){const left=(y*9+x)*4;hash+=gray(left)>gray(left+4)?'1':'0';}
      }
      asset={url:temporary,hash,aspect:Math.max(.4,Math.min(2.5,probe.naturalWidth/probe.naturalHeight))};assets.current.set(identity,asset);temporary=undefined;
     }
     if(disposed||controller.signal.aborted||accepted.length>=PHOTO_WALL_TARGET)return;
     if(asset.hash&&isNearDuplicateHash(asset.hash,hashes,3))continue;
     if(asset.hash)hashes.push(asset.hash);
     accepted.push({...candidate,aspect:asset.aspect});sources[candidate.proxy_url]=asset.url;
     setImages([...accepted]);setImageSources({...sources});setLoadState('ready');
    }catch{/* Try another candidate within the same total deadline. */}
    finally{if(temporary)URL.revokeObjectURL(temporary);}
   }};
   await Promise.all(Array.from({length:Math.min(6,candidates.length)},worker));
   if(disposed)return;
   if(!accepted.length){setImages([]);setImageSources({});throw new Error('As fontes retornaram imagens, mas os arquivos não carregaram.');}
   // Bound memory while preserving every image still displayed.
   const used=new Set(Object.values(sources));
   for(const [identity,asset] of assets.current){
    if(assets.current.size<=36)break;
    if(!used.has(asset.url)){URL.revokeObjectURL(asset.url);assets.current.delete(identity);}
   }
  };
  void run().catch(error=>{if(!disposed){setImages([]);setImageSources({});setLoadState('failed');setFailure(error instanceof Error&&error.name!=='AbortError'?error.message:'A fonte de imagens demorou a responder. Tente novamente.');}})
   .finally(()=>{window.clearTimeout(timer);if(!disposed)setPhotosLoading(false);});
  return()=>{disposed=true;window.clearTimeout(timer);controller.abort();};
 },[collectionQuery,retry]);
 const showFallback=loadState==='failed'&&!visibleImages.length;
 return <div className="study-cinema" aria-label={`Imagens relacionadas a ${panel.title}`}>
  <div className="study-film-wall" style={{gridTemplateRows:`repeat(${Math.max(1,wallRows.length)},minmax(0,1fr))`}} aria-label="Faixas de imagens relacionadas, movendo-se da direita para a esquerda">
   {wallRows.map((row,rowIndex)=><div className={`study-film-lane lane-${rowIndex+1}`} key={rowIndex}>
    <div className="study-film-lane-track" style={{'--lane-duration':`${Math.max(22,row.length*3.3)}s`,'--lane-tile-width':`max(16.6667vw, calc(100vw / ${row.length}))`} as React.CSSProperties}>
     {[0,1].map(copy=><div className="study-film-lane-set" key={copy} aria-hidden={copy===1}>
      {row.map((image,index)=><figure className="study-film-tile" key={`${copy}-${image.proxy_url}`} style={{width:`calc(100vw * ${(image.aspect||1.5)/row.reduce((sum,item)=>sum+(item.aspect||1.5),0)})`}}>
       <img src={imageSources[image.proxy_url]} alt={copy===0?image.title:''} decoding="async" onError={()=>setImageSources(previous=>{const next={...previous};delete next[image.proxy_url];return next;})}/>
      </figure>)}
     </div>)}
    </div>
   </div>)}
  </div>
  {(loadState==='loading'&&!images.length||photosLoading&&!visibleImages.length)&&<div className="study-cinema-status"><i/><span>BUSCANDO IMAGENS PARA A EXPLICAÇÃO</span></div>}
  {showFallback&&<div className="study-cinema-fallback"><span>{failure||'As imagens desta busca não carregaram.'}</span><button type="button" onClick={()=>setRetry(value=>value+1)}><RotateCw size={15}/> TENTAR OUTRAS IMAGENS</button><div><a href={`https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=${encodeURIComponent(collectionQuery)}`} target="_blank" rel="noreferrer">WIKIMEDIA <ExternalLink size={12}/></a><a href={`https://openverse.org/search/image?q=${encodeURIComponent(collectionQuery)}`} target="_blank" rel="noreferrer">OPENVERSE <ExternalLink size={12}/></a></div></div>}
  {visibleImages.length>0&&<a className="study-cinema-credit" href={visibleImages[0].source_url} target="_blank" rel="noreferrer" aria-label="Abrir a fonte das imagens" title="Abrir a fonte das imagens"><ExternalLink size={14}/></a>}
  <button className="study-cinema-close" type="button" onClick={onClose} aria-label="Fechar apresentação" title="Fechar"><X size={20}/></button>
 </div>;
}

export function StudyExplanationPanel({panels,activeId,onClose,speaking=false}:Props){
 const ordered=panels.slice().sort((a,b)=>a.createdAt-b.createdAt);
 const active=activeId?ordered.find(panel=>panel.id===activeId&&!panel.minimized):undefined;
 if(!active)return null;
 return <StudyStory key={active.id} panel={active} speaking={speaking} onClose={()=>onClose(active.id)}/>;
}
