export type StremioRequest={openExact?:boolean;query:string;kind:'movie'|'series';season?:number;episode?:number;items?:{id:string;name:string;year:string;kind:'movie'|'series'}[];message?:string};
export function stremioCommand(text:string):StremioRequest|null{
 const clean=text.trim().replace(/^(?:cronos|kronos|chronos|chrome)[,\s:]+/i,'').replace(/[.!?]+$/,'').replace(/[,\s]+por favor$/i,'');
 const match=clean.match(/^(?:abra|abrir|abre|coloque|colocar|coloca|reproduza|reproduzir|quero ver|assistir)\s+(?:a |o |uma |um )?(filme|s[eé]rie)\s+(.+)$/i);
 if(!match)return null;
 const title=match[2].replace(/\s+(?:no |pelo |com o )?Stremio$/i,'');
 const episode=title.match(/\s+(?:na )?temporada\s+(\d+)\s*[,–-]?\s*(?:no )?epis[oó]dio\s+(\d+)$/i);
 const query=title.replace(/\s+(?:na )?temporada\s+\d+\s*[,–-]?\s*(?:no )?epis[oó]dio\s+\d+$/i,'').trim();
 if(!query)return null;
 return {openExact:true,query,kind:match[1].toLowerCase()==='filme'?'movie':'series',...(episode?{season:Number(episode[1]),episode:Number(episode[2])}:{})};
}
