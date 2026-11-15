import {useMemo} from 'react';
import {answerSections} from './HolographicCards';
import {HologramDeck} from './HologramDeck';
import {spokenSectionIndex} from '../animation/referenceDeck';
export function SpokenReferenceCards({reply,spokenChunk,finished,onClose}:{reply:string;spokenChunk:string;finished:boolean;onClose:()=>void}){
 const sections=useMemo(()=>answerSections(reply),[reply]);
 const active=useMemo(()=>spokenSectionIndex(sections,spokenChunk),[sections,spokenChunk]);
 const cards=sections.map((s,i)=>({id:String(i),title:s.title,kicker:'CRONOS · RESPOSTA',body:s.body}));
 return <HologramDeck cards={cards} label="Resposta do Cronos" activeCue={active} finished={finished} onClose={onClose}/>;
}
