import type {SceneInput} from './renderers';
export function startCanvasWorker(canvas:HTMLCanvasElement,kind:'orb'|'star',size:number,density:number,input:()=>SceneInput,onFailure:()=>void):(()=>void)|null{
  if(!canvas.transferControlToOffscreen||!window.Worker)return null;
  let worker:Worker;
  try{worker=new Worker(new URL('./scene.worker.ts',import.meta.url),{type:'module'});}catch{return null;}
  try{
    canvas.width=canvas.height=Math.ceil(size*Math.min(window.devicePixelRatio||1,1.25));
    const offscreen=canvas.transferControlToOffscreen();
    worker.postMessage({type:'input',input:input()});
    worker.postMessage({type:'init',canvas:offscreen,kind,size,density,pixelRatio:Math.min(window.devicePixelRatio||1,1.25)},[offscreen]);
  }catch{worker.terminate();onFailure();return ()=>{};}
  canvas.dataset.renderThread='worker';
  worker.onerror=()=>{onFailure();};
  const timer=setInterval(()=>worker.postMessage({type:'input',input:input()}),80);
  return ()=>{clearInterval(timer);worker.terminate();};
}
