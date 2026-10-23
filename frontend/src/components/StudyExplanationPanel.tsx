import React from 'react';
import {Minus,X} from 'lucide-react';
import './StudyExplanationPanel.css';

type Props={question:string;reply:string;minimized:boolean;onMinimize:()=>void;onRestore:()=>void;onClose:()=>void};

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

export function StudyExplanationPanel({question,reply,minimized,onMinimize,onRestore,onClose}:Props){
 if(minimized)return <button type="button" className="study-dossier-restore" onClick={onRestore}><span>↗</span> AULA NA TELA</button>;
 return <aside className="study-dossier" aria-label="Explicação didática" aria-live="polite">
  <header className="study-dossier-head"><div className="study-dossier-sigil" aria-hidden="true"><span/></div><div className="study-dossier-label"><small>CRONOS · REGISTRO DE CONHECIMENTO</small><strong>DOSSIÊ DE APRENDIZAGEM</strong><span><i/> CONCEITO EM ANÁLISE</span></div><div className="study-dossier-actions"><button type="button" onClick={onMinimize} title="Minimizar explicação" aria-label="Minimizar explicação"><Minus size={17}/></button><button type="button" onClick={onClose} title="Fechar explicação" aria-label="Fechar explicação"><X size={18}/></button></div></header>
  <div className="study-dossier-question"><small>ASSUNTO</small><h2>{question}</h2></div>
  <div className="study-dossier-body">{reply?<TextBody text={reply}/>:<p className="study-dossier-pending">Preparando uma explicação completa…</p>}</div>
  <footer className="study-dossier-foot"><span>EXPLICAÇÃO EM TEXTO · CRONOS</span><b/></footer>
 </aside>;
}
