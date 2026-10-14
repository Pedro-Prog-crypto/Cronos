export type MusicCommand={action:'search';query:string;similar:boolean;video?:boolean}|{action:'frequency';hz:number}|{action:'pause'|'resume'|'stop'|'next'|'previous'};
export function musicCommand(text:string):MusicCommand|null {
 const clean=text.trim().replace(/^(?:kronos|cronos|chronos|chrome)[,\s:]+/i,'').replace(/[.!?]+$/,'').replace(/[,\s]+por favor$/i,'').replace(/^por favor[,\s]+/i,'').replace(/^(?:(?:voce|você) (?:pode|poderia)|(?:pode|poderia))\s+/i,'').replace(/\s+/g,' ');
 const plain=clean.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 if(/^(?:parar|pare|desligar|desligue|fechar|feche) (?:a |o )?(?:musica|som|player|frequencia|clipe|video)$/.test(plain))return {action:'stop'};
 if(/^(?:pausar|pause) (?:a |o )?(?:musica|som|player|frequencia|clipe|video)$/.test(plain))return {action:'pause'};
 if(/^(?:continuar|continue|retomar|retome) (?:a |o )?(?:musica|som|player|frequencia|clipe|video)$/.test(plain))return {action:'resume'};
 if(/^(?:proxima musica|proximo (?:clipe|video)|pular (?:a )?musica)$/.test(plain))return {action:'next'};
 if(/^(?:musica anterior|(?:clipe|video) anterior|voltar (?:a )?musica)$/.test(plain))return {action:'previous'};
 const frequency=plain.match(/^(?:tocar|toque|colocar|coloque|reproduzir|reproduza) (?:uma |a )?(?:frequencia|tom)(?: de)? (\d+(?:[.,]\d+)?)\s*(?:hz|hertz)?$/);
 if(frequency)return {action:'frequency',hz:Number(frequency[1].replace(',','.'))};
 const similar=clean.match(/^(?:tocar|toque|colocar|coloque|reproduzir|reproduza) (?:umas? )?m[uú]sicas? (?:parecidas?|semelhantes?) (?:com |(?:as? )?de )(.+)$/i);
 if(similar)return {action:'search',query:similar[1].trim(),similar:true};
 const media=clean.match(/^(?:tocar|toque|colocar|coloque|reproduzir|reproduza|abrir|abra|abre|ver|quero(?: ouvir| ver)?)\s+(?:(?:a |o |uma |um )?(?:minha |meu )?)(m[uú]sicas?|clipes?|v[ií]deos?)\s+(.+)$/i);
 if(media){const query=media[2].replace(/^(?:preferid[ao]|favorit[ao])(?:[, ]+(?:(?:que )?[eé]|chamad[ao]|se chama))?[, :]+/i,'').replace(/^(?:que )?[eé][, :]+/i,'').trim();if(!query)return null;return {action:'search',query,similar:false,...(/clipe|v[ií]deo/i.test(media[1])?{video:true}:{})};}
 const direct=clean.match(/^(?:tocar|toque)\s+(.+)$/i)||clean.match(/^(?:colocar|coloque|reproduzir|reproduza)\s+(https:\/\/.+)$/i);
 if(direct&&!/^(?:o |a )?(?:olho|mem[oó]ria|obsidian|painel|frequ[eê]ncia|tom)\b/i.test(direct[1]))return {action:'search',query:direct[1].trim(),similar:false};
 return null;
}
