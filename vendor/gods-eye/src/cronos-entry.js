import {createStandaloneApplication} from './standalone/application.js';
window.__CRONOS_EMBEDDED__=true;
let token='',query='',application=null,ready=false;
const parent=(type,message)=>window.parent.postMessage({type,message},window.location.origin);
const originalFetch=window.fetch.bind(window);
window.fetch=(input,options={})=>{
 const url=new URL(typeof input==='string'||input instanceof URL?input:input.url,location.href);
 if(url.origin===location.origin&&url.pathname.startsWith('/api/')){
  const headers=new Headers(input instanceof Request?input.headers:undefined);new Headers(options.headers).forEach((value,key)=>headers.set(key,value));headers.set('Authorization','Bearer '+token);
  return originalFetch(input,{...options,headers});
 }
 return originalFetch(input,options);
};
function navigate(){
 if(!ready||!query.trim())return;
 const input=document.getElementById('location-search');if(!input)return;
 input.value=query;input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));query='';
}
async function start(){
 try{
  await originalFetch('/world/eye/heartbeat',{method:'POST',headers:{Authorization:'Bearer '+token}});
  const response=await fetch('/api/cronos/browser-config');
  if(!response.ok)throw new Error('Eye data service unavailable');
  const browserConfig=await response.json();
  application=createStandaloneApplication({...browserConfig,allowQaRegistration:false});const components=await application.start();
  const viewer=components.scene?.viewer;
  if(viewer){viewer.targetFrameRate=20;viewer.resolutionScale=Math.min(1,1/window.devicePixelRatio);viewer.scene.globe.tileCacheSize=64;}
  const mic=document.getElementById('gev-voice-button');
  const help=document.getElementById('gev-voice-help');if(help)help.textContent='F4 liga ou desliga o microfone do Cronos.';
  if(mic){mic.title='Microfone do Cronos · F4';mic.setAttribute('aria-label','Microfone do Cronos · F4');mic.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation();parent('cronos:toggle-mic');},true);}
  ready=true;parent('cronos:world-ready');navigate();
 }catch{parent('cronos:world-error','Não foi possível iniciar o aplicativo Olho de Deus. Confira o diagnóstico local e as fontes de dados.');}
}
window.addEventListener('message',event=>{
 if(event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='cronos:world')return;
 if(typeof event.data.token!=='string'||!event.data.token)return;
 const first=!token;token=event.data.token;query=String(event.data.query||'').slice(0,160);
 if(first)void start();else navigate();
});
window.addEventListener('keydown',event=>{if(event.code==='Space'&&!(event.target instanceof Element&&event.target.closest('input,textarea,select,button,[contenteditable=true]'))){event.preventDefault();event.stopImmediatePropagation();return;}if(event.key==='F4'&&!event.altKey&&!event.ctrlKey&&!event.metaKey){event.preventDefault();event.stopImmediatePropagation();if(!event.repeat)parent('cronos:toggle-mic');return;}if(event.key==='Escape'){event.preventDefault();parent('cronos:interrupt');}},true);
const heartbeat=setInterval(()=>{if(token)void originalFetch('/world/eye/heartbeat',{method:'POST',headers:{Authorization:'Bearer '+token}}).catch(()=>{});},15000);
window.addEventListener('pagehide',()=>{clearInterval(heartbeat);void application?.destroy().catch(()=>{});});
parent('cronos:world-boot');
