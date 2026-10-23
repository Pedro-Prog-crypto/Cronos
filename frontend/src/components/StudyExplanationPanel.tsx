import React from 'react';
import {Lock,LockOpen,Minus,X} from 'lucide-react';
import './StudyExplanationPanel.css';

export type StudyPanelItem={id:string;title:string;reply:string;slot:number;locked:boolean;minimized:boolean;createdAt:number};
type Props={panels:StudyPanelItem[];onMinimize:(id:string)=>void;onRestore:(id:string)=>void;onClose:(id:string)=>void;onToggleLock:(id:string)=>void};

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

export function StudyExplanationPanel({panels,onMinimize,onRestore,onClose,onToggleLock}:Props){
 if(!panels.length)return null;
 const ordered=panels.slice().sort((a,b)=>a.slot-b.slot);
 return <div className="study-dossier-stack" aria-label="Explicações de estudo">
  {ordered.filter(panel=>!panel.minimized).map(panel=><aside key={panel.id} style={{gridColumn:panel.slot+1}} className={`study-dossier${panel.locked?' is-locked':''}`} aria-label={`Explicação: ${panel.title}`} aria-live="polite">
    <header className="study-dossier-head"><div className="study-dossier-sigil" aria-hidden="true"><span/></div><div className="study-dossier-label"><small>SISTEMA · CRONOS</small><strong>JANELA DE MISSÃO</strong><span><i/>{panel.locked?'REGISTRO FIXADO':panel.reply?'CONCEITO REGISTRADO':'ANÁLISE EM ANDAMENTO'}</span></div><div className="study-dossier-actions">
      <button type="button" onClick={()=>onToggleLock(panel.id)} title={panel.locked?'Desafixar painel':'Fixar painel'} aria-label={panel.locked?'Desafixar painel':'Fixar painel'} aria-pressed={panel.locked}>{panel.locked?<Lock size={16}/>:<LockOpen size={16}/>}</button>
      <button type="button" onClick={()=>onMinimize(panel.id)} title="Minimizar painel" aria-label="Minimizar painel"><Minus size={17}/></button>
      <button type="button" onClick={()=>onClose(panel.id)} title="Fechar painel" aria-label="Fechar painel"><X size={18}/></button>
     </div></header>
    <div className="study-dossier-topic"><small>ASSUNTO</small><h2>{panel.title}</h2></div>
    <div className="study-dossier-body">{panel.reply?<TextBody text={panel.reply}/>:<p className="study-dossier-pending">Preparando a explicação…</p>}</div>
    <footer className="study-dossier-foot"><span>{panel.locked?'FIXADO PELO SENHOR':'REGISTRO DE APRENDIZAGEM'}</span><b/></footer>
   </aside>)}
  {ordered.some(panel=>panel.minimized)&&<div className="study-dossier-shelf" aria-label="Painéis minimizados">{ordered.filter(panel=>panel.minimized).map(panel=><button key={panel.id} type="button" className={`study-dossier-restore${panel.locked?' is-locked':''}`} onClick={()=>onRestore(panel.id)} title={`Restaurar ${panel.title}`}><span>↗</span><b>{panel.title}</b>{panel.locked&&<Lock size={13}/>}</button>)}</div>}
 </div>;
}
