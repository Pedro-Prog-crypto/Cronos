import React,{useEffect,useRef} from 'react';
import {getToken,api} from '../api';
export default function WorldMap({query,onError,onReady}:{query:string;onError:(message:string)=>void;onReady:()=>void}){
 const frame=useRef<HTMLIFrameElement>(null),callbacks=useRef({onError,onReady});callbacks.current={onError,onReady};
 const transmit=()=>frame.current?.contentWindow?.postMessage({type:'cronos:world',token:getToken(),query},window.location.origin);
 useEffect(()=>{transmit();},[query]);
 useEffect(()=>{const receive=(event:MessageEvent)=>{
  if(event.origin!==window.location.origin||event.source!==frame.current?.contentWindow)return;
  if(event.data?.type==='cronos:world-boot')transmit();
  if(event.data?.type==='cronos:world-ready')callbacks.current.onReady();
  if(event.data?.type==='cronos:world-error')callbacks.current.onError(String(event.data.message).slice(0,500));
  if(event.data?.type==='cronos:toggle-mic')window.dispatchEvent(new KeyboardEvent('keydown',{key:'F4'}));
  if(event.data?.type==='cronos:interrupt')window.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));
 };window.addEventListener('message',receive);return()=>{window.removeEventListener('message',receive);void api('/world/close',{method:'POST',keepalive:true}).catch(()=>{});};},[]);
 return <iframe ref={frame} className="world-map-frame" title="Olho de Deus — mapa mundial" src="/world/view" onLoad={transmit} allowFullScreen sandbox="allow-scripts allow-same-origin"/>;
}
