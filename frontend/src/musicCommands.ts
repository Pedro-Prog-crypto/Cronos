export type MusicCommand={action:'search';query:string;similar:boolean}|{action:'frequency';hz:number}|{action:'pause'|'resume'|'stop'|'next'};
export function musicCommand(text:string):MusicCommand|null {
 const clean=text.trim().replace(/^(?:kronos|cronos|chrome)[,\s:]+/i,'').replace(/[.!?]+$/,'').replace(/[,\s]+por favor$/i,'').replace(/^por favor[,\s]+/i,'').replace(/\s+/g,' ');
 const plain=clean.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 if(/^(?:parar|pare|desligar|desligue|fechar|feche) (?:a |o )?(?:musica|som|player|frequencia)$/.test(plain))return {action:'stop'};
 if(/^(?:pausar|pause) (?:a |o )?(?:musica|som|player|frequencia)$/.test(plain))return {action:'pause'};
 if(/^(?:continuar|continue|retomar|retome) (?:a |o )?(?:musica|som|player|frequencia)$/.test(plain))return {action:'resume'};
 if(/^(?:proxima musica|pular (?:a )?musica)$/.test(plain))return {action:'next'};
 const frequency=plain.match(/^(?:tocar|toque|colocar|coloque|reproduzir|reproduza) (?:uma |a )?(?:frequencia|tom)(?: de)? (\d+(?:[.,]\d+)?)\s*(?:hz|hertz)?$/);
 if(frequency)return {action:'frequency',hz:Number(frequency[1].replace(',','.'))};
 const similar=clean.match(/^(?:tocar|toque|colocar|coloque|reproduzir|reproduza) (?:umas? )?m[uú]sicas? (?:parecidas?|semelhantes?) (?:com |(?:as? )?de )(.+)$/i);
 if(similar)return {action:'search',query:similar[1].trim(),similar:true};
 if(/^(?:colocar|coloque|reproduzir|reproduza)\s+/i.test(clean)&& !/^(?:colocar|coloque|reproduzir|reproduza)\s+(?:(?:a |uma )?m[uú]sicas?\b|https:\/\/)/i.test(clean))return null;
 const search=clean.match(/^(?:tocar|toque|colocar|coloque|reproduzir|reproduza)\s+(?:(?:a |uma )?m[uú]sica(?:s)?\s+)?(.+)$/i);
 if(search&&!/^(?:o |a )?(?:olho|mem[oó]ria|obsidian|painel|frequ[eê]ncia|tom)\b/i.test(search[1]))return {action:'search',query:search[1].trim(),similar:false};
 return null;
}
