import {useEffect,useRef} from 'react';
import '../components/movable.css';
let foreground=50;

/** Move only the selected surface, using compositor offsets; never rerender the whole scene. */
export function useMovable(){
 const ref=useRef<HTMLElement|null>(null),offset=useRef({x:0,y:0});
 const drag=useRef<{id:number;x:number;y:number;left:number;top:number}|null>(null);
 const moved=useRef(false);
 const frame=useRef(0),next=useRef({x:0,y:0});
 const apply=(x:number,y:number)=>{
  const node=ref.current;if(!node)return;
  const rect=node.getBoundingClientRect(),left=rect.left-offset.current.x,top=rect.top-offset.current.y;
  const targetX=Math.max(0,Math.min(Math.max(0,window.innerWidth-rect.width),x));
  const targetY=Math.max(0,Math.min(Math.max(0,window.innerHeight-rect.height),y));
  offset.current={x:targetX-left,y:targetY-top};
  node.style.setProperty('--drag-x',offset.current.x+'px');node.style.setProperty('--drag-y',offset.current.y+'px');
 };
 const flush=()=>{cancelAnimationFrame(frame.current);frame.current=0;apply(next.current.x,next.current.y);};
 useEffect(()=>{
  const clamp=()=>{const node=ref.current;if(node&&node.dataset.moved){const rect=node.getBoundingClientRect();apply(rect.left,rect.top);}};
  window.addEventListener('resize',clamp);const observer=new ResizeObserver(clamp);if(ref.current)observer.observe(ref.current);
  return()=>{window.removeEventListener('resize',clamp);observer.disconnect();cancelAnimationFrame(frame.current);};
 },[]);
 const pin=(node:HTMLElement,rect:DOMRect)=>{
  if(moved.current)return;
  // Replace percentage/centering placement once: incoming text must not move a dragged panel.
  node.style.left=rect.left+'px';node.style.top=rect.top+'px';node.style.right='auto';node.style.bottom='auto';node.style.transform='none';
  offset.current={x:0,y:0};moved.current=true;
 };
 const onPointerDown=(event:React.PointerEvent<HTMLElement>)=>{
  const target=event.target as HTMLElement;
  if(event.button!==0||!target.closest('[data-drag-handle]')||target.closest('button,input,textarea,select,a'))return;
  const node=ref.current;if(!node)return;const rect=node.getBoundingClientRect();pin(node,rect);
  drag.current={id:event.pointerId,x:event.clientX,y:event.clientY,left:rect.left,top:rect.top};
  moved.current=true;node.dataset.dragging='true';node.dataset.moved='true';node.style.zIndex=String(++foreground);node.setPointerCapture(event.pointerId);event.preventDefault();
 };
 const onPointerMove=(event:React.PointerEvent<HTMLElement>)=>{
  const current=drag.current;if(!current||current.id!==event.pointerId)return;
  next.current={x:current.left+event.clientX-current.x,y:current.top+event.clientY-current.y};
  if(!frame.current)frame.current=requestAnimationFrame(()=>{frame.current=0;apply(next.current.x,next.current.y);});
 };
 const finish=(event:React.PointerEvent<HTMLElement>)=>{
  if(!drag.current||drag.current.id!==event.pointerId)return;
  if(frame.current)flush();drag.current=null;const node=ref.current;
  if(node){delete node.dataset.dragging;if(node.hasPointerCapture(event.pointerId))node.releasePointerCapture(event.pointerId);}
 };
 const onKeyDown=(event:React.KeyboardEvent<HTMLElement>)=>{
  if(!(event.target as HTMLElement).matches('[data-drag-handle]')||!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key))return;
  const node=ref.current;if(!node)return;event.preventDefault();const r=node.getBoundingClientRect();pin(node,r);node.dataset.moved='true';const step=event.shiftKey?30:10;
  apply(r.left+(event.key==='ArrowRight'?step:event.key==='ArrowLeft'?-step:0),r.top+(event.key==='ArrowDown'?step:event.key==='ArrowUp'?-step:0));
 };
 return {ref,moved,onPointerDown,onPointerMove,onPointerUp:finish,onPointerCancel:finish,onKeyDown};
}

/** Mouse drag scrolls overflowing text; wheel, touch scrolling and keyboard also remain available. */
export function useDragScroll(){
 const active=useRef<{id:number;y:number;top:number;dragging:boolean}|null>(null);
 const onPointerDown=(event:React.PointerEvent<HTMLElement>)=>{
  const target=event.target as HTMLElement,node=event.currentTarget;
  if(event.defaultPrevented||event.pointerType!=='mouse'||event.button!==0||target.closest('[data-drag-handle],button,input,textarea,select,a')||node.scrollHeight<=node.clientHeight+1)return;
  active.current={id:event.pointerId,y:event.clientY,top:node.scrollTop,dragging:false};
 };
 const onPointerMove=(event:React.PointerEvent<HTMLElement>)=>{
  const current=active.current;if(!current||current.id!==event.pointerId||event.buttons!==1)return;
  if(!current.dragging&&Math.abs(event.clientY-current.y)<5)return;
  if(!current.dragging){current.dragging=true;event.currentTarget.setPointerCapture(event.pointerId);window.getSelection()?.removeAllRanges();}
  event.currentTarget.dataset.panning='true';event.currentTarget.scrollTop=current.top+current.y-event.clientY;event.preventDefault();
 };
 const finish=(event:React.PointerEvent<HTMLElement>)=>{
  if(active.current?.id!==event.pointerId)return;active.current=null;delete event.currentTarget.dataset.panning;
  if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId);
 };
 return {onPointerDown,onPointerMove,onPointerUp:finish,onPointerCancel:finish};
}
