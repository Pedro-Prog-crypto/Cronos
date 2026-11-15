import {useEffect,useLayoutEffect,useRef,useState,type CSSProperties,type ReactNode} from 'react';
import {ChevronLeft,ChevronRight,FileText,LayoutGrid,X} from 'lucide-react';
import {deckPlacement} from '../animation/referenceDeck';
export type HologramDeckCard={id:string;title:string;kicker:string;body:string;icon?:ReactNode;action?:string;open?:()=>void};
type Props={cards:HologramDeckCard[];label:string;onClose:()=>void;activeCue?:number|null;finished?:boolean};

/** One DOM card moves from focus into history, then into the final horizontal row. */
export function HologramDeck({cards,label,onClose,activeCue,finished=false}:Props){
 const [active,setActive]=useState<number|null>(0),[visited,setVisited]=useState<number[]>([0]);
 const [viewport,setViewport]=useState({width:window.innerWidth,height:window.innerHeight});
 const lastCue=useRef<number|null|undefined>(undefined),controls=useRef<HTMLElement|null>(null);
 const choose=(index:number)=>{setActive(index);setVisited(old=>old.includes(index)?old:[...old,index].sort((a,b)=>a-b));};
 const overview=()=>{setVisited(cards.map((_,i)=>i));setActive(null);};
 useEffect(()=>{const resize=()=>setViewport({width:window.innerWidth,height:window.innerHeight});window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize);},[]);
 useEffect(()=>{
  if(activeCue==null||activeCue===lastCue.current||activeCue>=cards.length)return;
  lastCue.current=activeCue;setActive(activeCue);
  setVisited(old=>Array.from(new Set([...old,...Array.from({length:activeCue+1},(_,i)=>i)])).sort((a,b)=>a-b));
 },[activeCue,cards.length]);
 useEffect(()=>{if(finished){setVisited(cards.map((_,i)=>i));setActive(null);}},[finished,cards.length]);
 useLayoutEffect(()=>{if(document.activeElement?.closest('[data-miniature="true"]'))controls.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();},[active]);
 const history=visited.filter(i=>i!==active&&i<cards.length);
 const visibleHistory=active!==null&&viewport.width<700?history.slice(-3):history;
 return <section className="hologram-deck" aria-label={label} data-mode={active===null?'overview':'focus'}>
  <div className="hologram-deck-plane">{visited.filter(i=>i<cards.length&&(active===null||active===i||visibleHistory.includes(i))).map(index=>{
   const card=cards[index],focused=active===index;
   const p=deckPlacement((active===null?visited:visibleHistory).indexOf(index),active===null?visited.length:visibleHistory.length,focused,active===null,viewport.width,viewport.height);
   return <article key={card.id} className="hologram-deck-card" data-miniature={!focused} aria-label={card.title} style={{'--deck-x':`${p.x}px`,'--deck-y':`${p.y}px`,'--deck-scale':p.scale,'--deck-width':`${p.cardWidth}px`,'--deck-height':`${p.cardHeight}px`} as CSSProperties}>
    <header><span className="deck-card-icon">{card.icon||<FileText size={20}/>}</span><div><small>{card.kicker}</small><h2>{card.title}</h2></div></header>
    <div className="deck-card-body" tabIndex={focused?0:-1}>{card.body}</div>
    {card.open&&<button className="deck-card-action" tabIndex={focused?0:-1} onClick={card.open}>{card.action}<ChevronRight size={14}/></button>}
    {!focused&&<button className="deck-card-restore" aria-label={`Mostrar ${card.title}`} onClick={()=>choose(index)}/>}
   </article>;
  })}</div>
  <nav className="hologram-deck-controls" aria-label="Navegar entre os cards" ref={controls}>
   <button aria-label="Card anterior" disabled={active===0} onClick={()=>choose(active===null?cards.length-1:Math.max(0,active-1))}><ChevronLeft size={16}/></button>
   <span role="status">{active===null?'VISÃO GERAL':`${String((active??0)+1).padStart(2,'0')} / ${String(cards.length).padStart(2,'0')}`}</span>
   <button aria-label={active===cards.length-1?'Concluir apresentação':'Próximo card'} disabled={active===null} onClick={()=>{if(active===cards.length-1)overview();else choose((active??-1)+1);}}><ChevronRight size={16}/></button>
   <button aria-label="Ver todos os cards" aria-pressed={active===null} onClick={overview}><LayoutGrid size={16}/></button>
   <button aria-label="Fechar cards" onClick={onClose}><X size={16}/></button>
  </nav>
 </section>;
}
