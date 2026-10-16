import React, {useMemo,useEffect,useLayoutEffect,useState,useRef} from 'react';
import {FileText} from 'lucide-react';
import './holographic-cards.css';
import {useMovable,useDragScroll} from '../hooks/useMovable';
import {cardHome,CardLayout} from '../cardLayout';

export type AnswerSection={title:string;body:string};
/** Partition actual reply text; never substitute memory summaries or invent content. */
export function answerSections(text:string):AnswerSection[]{
  const sections:AnswerSection[]=[];let title='RESPOSTA',lines:string[]=[];
  const flush=()=>{const body=lines.join('\n').trim();if(body)sections.push({title,body});lines=[];};
  for(const line of text.split('\n')){
    const heading=line.match(/^\s*#{1,6}\s+(.+?)\s*#*\s*$/)||line.match(/^\s*\*\*(.+?)\*\*\s*:?[ \t]*$/);
    if(heading){flush();title=heading[1];}else lines.push(line);
  }
  flush();
  if(sections.length===1){
    const blocks=sections[0].body.split(/\n\s*\n/).filter(Boolean);
    if(blocks.length>1&&text.length>450)return limitSections(blocks.map(body=>({title:'RESPOSTA',body})));
    const rows=sections[0].body.split('\n');
    if(rows.length>1&&rows.every(row=>/^\s*(?:[-*•]|\d+[.)])\s+/.test(row)))return limitSections(rows.map(body=>({title:'RESPOSTA',body})));
  }
  return limitSections(sections.length?sections:text.trim()?[{title:'RESPOSTA',body:text}]:[]);
}
function limitSections(sections:AnswerSection[]){
  if(sections.length<=8)return sections;
  return [...sections.slice(0,7),{title:'CONTINUAÇÃO',body:sections.slice(7).map(s=>`${s.title}\n${s.body}`).join('\n\n')}];
}
export const HolographicCard=React.memo(function HolographicCard({title,children,variant='layered',className='',movable=false}:{title:string;children:React.ReactNode;variant?:'compact'|'vertical'|'layered'|'ribbon';className?:string;movable?:boolean}){
  return <article className={`holo-card holo-${variant} ${className}`}>
    <div className="holo-depth" aria-hidden="true"/><div className="holo-trails" aria-hidden="true"/>
    <div className="holo-shell"><div className="holo-surface">
      <span className="holo-accent-cyan" aria-hidden="true"/><span className="holo-accent-pink" aria-hidden="true"/>
      {variant==='ribbon'&&<div className="holo-document" aria-hidden="true"><FileText size={22}/></div>}
      <div className="holo-content"><h2 data-drag-handle={movable||undefined} tabIndex={movable?0:undefined} title={movable?'Arraste para mover o card':undefined}>{title}</h2>{children}</div>
    </div></div>
  </article>;
});
export function MovableCardFrame({children,className}:{children:React.ReactNode;className:string}){
 const movement=useMovable();
 return <div className={className+' movable-surface'} ref={movement.ref as React.RefObject<HTMLDivElement>} onPointerDown={movement.onPointerDown} onPointerMove={movement.onPointerMove} onPointerUp={movement.onPointerUp} onPointerCancel={movement.onPointerCancel} onKeyDown={movement.onKeyDown}>{children}</div>;
}
function FloatingAnswerCard({section,index,total,viewport,layout}:{section:AnswerSection;index:number;total:number;viewport:{width:number;height:number};layout:CardLayout}){
 const movement=useMovable(),scroll=useDragScroll();
 const [height,setHeight]=useState(170);
 const width=Math.min(Math.max(190,Math.min(300,viewport.width*.215)),section.body.length<90?225:section.body.length<240?275:300);
 const rows=layout==='orbit'?Math.ceil(total/2):total>3?Math.ceil(total/2):total;
 const limit=Math.max(60,Math.min(250,viewport.height/(rows+1.2)-80));
 const home=cardHome(index,total,viewport.width,viewport.height,width,height,layout);
 const placed=useRef(home);
 if(!movement.moved.current)placed.current=home;
 useLayoutEffect(()=>{
  const node=movement.ref.current;if(!node)return;
  const observer=new ResizeObserver(()=>setHeight(Math.round(node.getBoundingClientRect().height)));observer.observe(node);return()=>observer.disconnect();
 },[]);
 return <div className="floating-answer-card movable-surface" ref={movement.ref as React.RefObject<HTMLDivElement>} onPointerDown={movement.onPointerDown} onPointerMove={movement.onPointerMove} onPointerUp={movement.onPointerUp} onPointerCancel={movement.onPointerCancel} onKeyDown={movement.onKeyDown} style={{left:placed.current.x,top:placed.current.y,width,'--card-body-limit':limit+'px'} as React.CSSProperties}>
  <HolographicCard title={section.title} movable variant={section.body.length<160?'compact':'layered'}><p className="holo-text drag-scroll" tabIndex={0} {...scroll}>{section.body}</p></HolographicCard>
 </div>;
}
export function AnswerCards({reply,layout='orbit'}:{reply:string;layout?:CardLayout}){
 const sections=useMemo(()=>answerSections(reply),[reply]);
 const [viewport,setViewport]=useState({width:window.innerWidth,height:window.innerHeight});
 useEffect(()=>{const resize=()=>setViewport({width:window.innerWidth,height:window.innerHeight});window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);},[]);
 return <section className="answer-card-deck" aria-label="Resposta do Kronos" aria-live="polite">
  {sections.map((section,index)=><FloatingAnswerCard key={layout+'-'+index} section={section} index={index} total={sections.length} viewport={viewport} layout={layout}/>)}
 </section>;
}
