import {useState} from 'react';
import {ExternalLink,Newspaper} from 'lucide-react';
import {HologramDeck,type HologramDeckCard} from './HologramDeck';
import type {NewsArticle} from '../newsPresentation';

function NewsVisual({article}:{article:NewsArticle}){
 const [failed,setFailed]=useState(false);
 return article.image&&!failed?<div className="deck-news-visual"><img src={article.image} alt="Imagem da fonte da notícia" loading="lazy" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/><span>{article.source.toUpperCase()}</span></div>
  :<div className="deck-news-source"><Newspaper size={24}/><span>{article.source}</span></div>;
}

export function NewsReferenceCards({articles,loading,spokenChunkIndex,finished,onClose}:{articles:NewsArticle[];loading:boolean;spokenChunkIndex:number;finished:boolean;onClose:()=>void}){
 const cards:HologramDeckCard[]=loading?
  [{id:'searching',title:'Notícias do dia',kicker:'CRONOS · BUSCA AO VIVO',body:'Consultando fontes recentes. As manchetes aparecerão aqui quando forem verificadas.',icon:<Newspaper size={20}/> }]:
  articles.length?articles.map((article,index)=>({id:article.url,title:article.title,kicker:`NOTÍCIA ${String(index+1).padStart(2,'0')} · ${article.source.toUpperCase()}`,badge:article.published||undefined,
   body:article.excerpt||'Abra a fonte para ler a notícia completa.',icon:<Newspaper size={20}/>,
   visual:<NewsVisual article={article}/>,
   action:'Abrir fonte',open:()=>window.open(article.url,'_blank','noopener,noreferrer')})):
  [{id:'unavailable',title:'Notícias indisponíveis',kicker:'CRONOS · BUSCA AO VIVO',body:'A busca não retornou manchetes verificadas. Tente novamente quando a conexão estiver disponível.',icon:<ExternalLink size={20}/> }];
 return <HologramDeck cards={cards} label="Notícias do dia" variant="news" activeCue={loading||!articles.length?null:Math.min(spokenChunkIndex,articles.length-1)} finished={!loading&&finished&&Boolean(articles.length)} onClose={onClose}/>;
}
