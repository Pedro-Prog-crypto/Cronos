import React,{useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import WorldView from './components/WorldView';
import {connect} from './api';
import './world.css';
function World(){
 const [query,setQuery]=useState(''),[ready,setReady]=useState(false);
 const parent=(type:string,message?:string)=>window.parent.postMessage({type,message},window.location.origin);
 useEffect(()=>{
  const receive=(event:MessageEvent)=>{
   if(event.source!==window.parent||event.origin!==window.location.origin||event.data?.type!=='cronos:world')return;
   if(typeof event.data.token!=='string'||!event.data.token)return;
   connect(event.data.token);setQuery(typeof event.data.query==='string'?event.data.query.slice(0,160):'');setReady(true);
  };window.addEventListener('message',receive);parent('cronos:world-boot');return()=>window.removeEventListener('message',receive);
 },[]);
 return ready?<WorldView query={query} onError={message=>parent('cronos:world-error',message)} onReady={()=>parent('cronos:world-ready')}/>:null;
}
createRoot(document.getElementById('root')!).render(<World/>);
