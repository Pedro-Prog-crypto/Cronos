import {renderOrb,renderStar,SceneInput} from './renderers';
let input:SceneInput={state:'IDLE',audio:0,hidden:false,links:true};
let stop:(()=>void)|undefined;
self.onmessage=event=>{
  if(event.data.type==='input'){input=event.data.input;return;}
  if(event.data.type==='init'){
    const {canvas,kind,size,density,pixelRatio}=event.data;
    stop?.();stop=(kind==='orb'?renderOrb:renderStar)(canvas,size,density,pixelRatio,()=>input);
    self.postMessage({type:'ready'});
  }
};
