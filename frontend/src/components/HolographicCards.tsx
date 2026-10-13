import React, {useMemo} from 'react';
import {FileText} from 'lucide-react';
import './holographic-cards.css';

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
export const HolographicCard=React.memo(function HolographicCard({title,children,variant='layered',className=''}:{title:string;children:React.ReactNode;variant?:'compact'|'vertical'|'layered'|'ribbon';className?:string}){
  return <article className={`holo-card holo-${variant} ${className}`}>
    <div className="holo-depth" aria-hidden="true"/><div className="holo-trails" aria-hidden="true"/>
    <div className="holo-shell"><div className="holo-surface">
      <span className="holo-accent-cyan" aria-hidden="true"/><span className="holo-accent-pink" aria-hidden="true"/>
      {variant==='ribbon'&&<div className="holo-document" aria-hidden="true"><FileText size={22}/></div>}
      <div className="holo-content"><h2>{title}</h2>{children}</div>
    </div></div>
  </article>;
});
export function AnswerCards({reply}:{reply:string}){
  const sections=useMemo(()=>answerSections(reply),[reply]);
  return <section className="answer-card-deck" aria-label="Resposta do Kronos" aria-live="polite">
    {sections.map((section,index)=><HolographicCard key={index} title={section.title} variant={section.body.length<160?'compact':sections.length>1&&section.body.length<320&&index%3===1?'vertical':'layered'}><p className="holo-text">{section.body}</p></HolographicCard>)}
  </section>;
}
