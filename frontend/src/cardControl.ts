export type CardHoldCommand={mode:'pin'|'unpin';target:string};
const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();

export function cardHoldCommand(text:string):CardHoldCommand|null{
 const value=normalize(text).replace(/^(?:cronos|kronos|chronos)\s+/,'');
 const match=value.match(/^(mantenha|manter|fixe|fixar|deixe fixo|libere|desfixe|desfixar)\s+(.+)$/);
 if(!match||!/(?:card|cartao|noticia)/.test(match[2]))return null;
 return {mode:/^(?:libere|desfixe|desfixar)$/.test(match[1])?'unpin':'pin',target:match[2]};
}

export function cardTargetIndexes(target:string,cards:readonly {title:string}[],active:number|null):number[]{
 const normalized=normalize(target);
 const numbered=[...normalized.matchAll(/(?:card|cartao|noticia)s?\s*(\d+)/g)]
  .map(match=>Number(match[1])-1).filter(index=>index>=0&&index<cards.length);
 if(numbered.length)return [...new Set(numbered)];
 if(/\b(?:este|esse|esta|essa)\s+(?:card|cartao|noticia)\b/.test(normalized)&&active!==null)return [active];
 const selected=cards.map((card,index)=>({index,title:normalize(card.title)}))
  .filter(card=>card.title.length>=5&&(normalized.includes(card.title)||card.title.includes(normalized.replace(/^(?:o|a|os|as)\s+(?:card|cartao|noticia)s?\s+(?:de|da|do)?\s*/,''))))
  .map(card=>card.index);
 return selected;
}
