import React from 'react';
import {Minus,PanelTop,Play,Pause,X} from 'lucide-react';
import './WindowShelf.css';
export function MinimizeWindow({onClick,label}:{onClick?:()=>void;label:string}){
 return onClick?<button type="button" className="window-minimize" aria-label={'Minimizar '+label} title="Minimizar; a tarefa continua em segundo plano" onClick={onClick}><Minus size={18}/></button>:null;
}
export function WindowSurface({minimized,children}:{minimized:boolean;children:React.ReactNode}){
 return <div style={{display:minimized?'none':'contents'}} inert={minimized} aria-hidden={minimized}>{children}</div>;
}
export type ShelfItem={id:string;title:string;detail?:string;onRestore:()=>void;onClose?:()=>void;playing?:boolean;onPlayback?:()=>void};
export function WindowShelf({items}:{items:ShelfItem[]}){
 if(!items.length)return null;
 return <nav className="window-shelf" aria-label="Janelas em segundo plano">{items.map(item=><div key={item.id} className="window-shelf-item"><button className="window-restore" aria-label={'Restaurar '+item.title} title={item.detail||item.title} onClick={item.onRestore}><PanelTop size={16}/><span><b>{item.title}</b>{item.detail&&<small>{item.detail}</small>}</span></button>{item.onPlayback&&<button aria-label={item.playing?'Pausar música minimizada':'Continuar música minimizada'} onClick={item.onPlayback}>{item.playing?<Pause size={16}/>:<Play size={16}/>}</button>}{item.onClose&&<button aria-label={'Fechar '+item.title+' minimizado'} onClick={item.onClose}><X size={14}/></button>}</div>)}</nav>;
}
