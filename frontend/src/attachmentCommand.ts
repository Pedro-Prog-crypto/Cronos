/** Only a direct attachment request opens a picker; conversation stays conversation. */
export function attachmentCommand(text:string):'image'|'document'|null{
 const value=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim().replace(/\s+/g,' ')
  .replace(/^(?:cronos|kronos|chronos)[,\s:]*/,'').replace(/^por favor[,\s]*/,'');
 const match=value.match(/^(?:(?:eu )?quero (?:que (?:voce |vc )?)?)?(?:analis(?:ar|e|a)|examin(?:ar|e|a)|abr(?:ir|a|e)|envi(?:ar|e|a)|carreg(?:ar|ue|a))\s+(?:(?:a|o|uma?|essa?|esta?|esse|este|minha?|meu)\s+)*(imagem|foto|fotografia|arquivo|zip|codigo)\b/);
 if(!match)return null;
 return /^(?:imagem|foto|fotografia)$/.test(match[1])?'image':'document';
}
