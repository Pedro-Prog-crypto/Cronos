import React from 'react';
import {Lock,LockOpen,Minus,X} from 'lucide-react';
import './StudyExplanationPanel.css';

export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number;position?:{left:number;top:number}};
type Props={panels:StudyPanelItem[];onMinimize:(id:string)=>void;onRestore:(id:string)=>void;onClose:(id:string)=>void;onToggleLock:(id:string)=>void;onMove:(id:string,left:number,top:number)=>void};

const TextBody=React.memo(function TextBody({text}:{text:string}){
 const blocks=text.split(/\n\s*\n/).filter(Boolean);
 return <div className="study-dossier-prose">{blocks.map((block,index)=>{
  const lines=block.split(/\r?\n/).filter(Boolean);
  return <section key={index}>{lines.map((line,n)=>{
   const heading=line.match(/^\s*(#{1,3})\s+(.+)/);
   if(heading){const Tag=(['h2','h3','h4'] as const)[heading[1].length-1];return <Tag key={n}>{heading[2]}</Tag>;}
   if(/^\s*[-*]\s+/.test(line))return <p className="dossier-bullet" key={n}>{line.replace(/^\s*[-*]\s+/,'')}</p>;
   if(/^\s*\d+[.)]\s+/.test(line))return <p className="dossier-bullet" key={n}>{line}</p>;
   return <p key={n}>{line}</p>;
  })}</section>;
 })}</div>;
});

export function StudyExplanationPanel({panels,onMinimize,onRestore,onClose,onToggleLock,onMove}:Props){
 const drag=React.useRef<{id:string;pointerId:number;startX:number;startY:number;left:number;top:number}|null>(null);
 const [dragging,setDragging]=React.useState<string|null>(null);
 const ordered=panels.slice().sort((a,b)=>a.slot-b.slot);
 if(!panels.length)return null;
 const defaultPosition=(slot:number)=>{
  const width=typeof window==='undefined'?1440:window.innerWidth,height=typeof window==='undefined'?900:window.innerHeight;
  const cardWidth=Math.min(560,Math.max(280,width*.30));
  const lane=width<=650?width*.92:width*.325;
  const initial=width<=650?width*.07+slot*lane:width*.025+slot*lane;
  return {left:Math.max(0,Math.min(width-cardWidth,initial)),top:height*.16};
 };
 const beginDrag=(event:React.PointerEvent<HTMLElement>,panel:StudyPanelItem)=>{
  if((event.target as HTMLElement).closest('button'))return;
  event.preventDefault();
  const rect=event.currentTarget.closest('.study-dossier')?.getBoundingClientRect();if(!rect)return;
  const position=panel.position??{left:rect.left,top:rect.top};
  drag.current={id:panel.id,pointerId:event.pointerId,startX:event.clientX,startY:event.clientY,left:position.left,top:position.top};
  setDragging(panel.id);
  event.currentTarget.setPointerCapture(event.pointerId);
 };
 const moveDrag=(event:React.PointerEvent<HTMLElement>)=>{
  const active=drag.current;if(!active||active.pointerId!==event.pointerId)return;
  const card=event.currentTarget.closest('.study-dossier') as HTMLElement|null;
  const width=typeof window==='undefined'?1440:window.innerWidth,height=typeof window==='undefined'?900:window.innerHeight;
  const cardWidth=card?.getBoundingClientRect().width??Math.min(560,Math.max(280,width*.30));
  const cardHeight=card?.getBoundingClientRect().height??Math.min(720,height*.68);
  onMove(active.id,Math.max(0,Math.min(width-cardWidth,active.left+event.clientX-active.startX)),Math.max(0,Math.min(height-cardHeight,active.top+event.clientY-active.startY)));
 };
 const endDrag=(event:React.PointerEvent<HTMLElement>)=>{if(drag.current?.pointerId===event.pointerId){drag.current=null;setDragging(null);}};
 return <div className="study-dossier-stack" aria-label="Explicações de estudo">
  {ordered.filter(panel=>!panel.minimized).map(panel=>{const position=panel.position??defaultPosition(panel.slot);return <aside key={panel.id} style={{left:position.left,top:position.top,zIndex:dragging===panel.id?5:undefined}} className={`study-dossier${panel.locked?' is-locked':''}${dragging===panel.id?' is-dragging':''}`} aria-label={`Explicação: ${panel.title}`} aria-live="polite">
    <header className="study-dossier-head" title="Arraste para mover este painel" onPointerDown={event=>beginDrag(event,panel)} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag}><div className="study-dossier-sigil" aria-hidden="true"><span/></div><div className="study-dossier-label"><small>SISTEMA · CRONOS</small><strong>JANELA DE MISSÃO</strong><span><i/>{panel.locked?'REGISTRO FIXADO':panel.reply?'CONCEITO REGISTRADO':'ANÁLISE EM ANDAMENTO'}</span></div><div className="study-dossier-actions">
      <button type="button" onPointerDown={event=>event.stopPropagation()} onClick={()=>onToggleLock(panel.id)} title={panel.locked?'Desafixar painel':'Fixar painel'} aria-label={panel.locked?'Desafixar painel':'Fixar painel'} aria-pressed={panel.locked}>{panel.locked?<Lock size={16}/>:<LockOpen size={16}/>}</button>
      <button type="button" onPointerDown={event=>event.stopPropagation()} onClick={()=>onMinimize(panel.id)} title="Minimizar painel" aria-label="Minimizar painel"><Minus size={17}/></button>
      <button type="button" onPointerDown={event=>event.stopPropagation()} onClick={()=>onClose(panel.id)} title="Fechar painel" aria-label="Fechar painel"><X size={18}/></button>
     </div></header>
    <div className="study-dossier-topic"><small>ASSUNTO</small><h2>{panel.title}</h2></div>
    <div className="study-dossier-body">{panel.reply?<TextBody text={panel.reply}/>:<p className="study-dossier-pending">Preparando a explicação…</p>}</div>
    <footer className="study-dossier-foot"><span>{panel.locked?'FIXADO PELO SENHOR':'REGISTRO DE APRENDIZAGEM'}</span><b/></footer>
   </aside>;})}
  {ordered.some(panel=>panel.minimized)&&<div className="study-dossier-shelf" aria-label="Painéis minimizados">{ordered.filter(panel=>panel.minimized).map(panel=><button key={panel.id} type="button" className={`study-dossier-restore${panel.locked?' is-locked':''}`} onClick={()=>onRestore(panel.id)} title={`Restaurar ${panel.title}`}><span>↗</span><b>{panel.title}</b>{panel.locked&&<Lock size={13}/>}</button>)}</div>}
 </div>;
}
