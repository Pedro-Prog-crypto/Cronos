import type {SceneInput} from './renderers';
/** Draw at the visible pixel density, with a bounded bitmap for steady animation. */
export function orbRenderRatio(canvas:HTMLCanvasElement,size:number){
  const displayed=canvas.getBoundingClientRect().width||size;
  const density=Math.min(window.devicePixelRatio||1,3);
  return Math.max(.5,Math.min(900,Math.ceil(displayed*density))/size);
}
export function startCanvasWorker(canvas:HTMLCanvasElement,kind:'orb'|'star',size:number,density:number,input:()=>SceneInput,onFailure:()=>void):(()=>void)|null{
  if(!canvas.transferControlToOffscreen||!window.Worker)return null;
  const read=()=>{const value=input();return {...value,hidden:value.hidden||canvas.getClientRects().length===0};};
  let worker:Worker;
  try{worker=new Worker(new URL('./scene.worker.ts',import.meta.url),{type:'module'});}catch{return null;}
  try{
    const pixelRatio=kind==='orb'?orbRenderRatio(canvas,size):Math.min(window.devicePixelRatio||1,1.25);
    canvas.width=canvas.height=kind==='orb'?Math.min(900,Math.round(size*pixelRatio)):Math.ceil(size*pixelRatio);
    const offscreen=canvas.transferControlToOffscreen();
    worker.postMessage({type:'input',input:read()});
    worker.postMessage({type:'init',canvas:offscreen,kind,size,density,pixelRatio},[offscreen]);
  }catch{worker.terminate();onFailure();return ()=>{};}
  canvas.dataset.renderThread='worker';
  worker.onerror=()=>{onFailure();};
  const timer=setInterval(()=>worker.postMessage({type:'input',input:read()}),80);
  return ()=>{clearInterval(timer);worker.terminate();};
}
