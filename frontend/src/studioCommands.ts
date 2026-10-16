export type StudioIntent={brief:string};
export function studioCommand(text:string):StudioIntent|null{
 let value=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 value=value.replace(/^(?:cronos|kronos|chronos)[,\s:]*/,'').replace(/^por favor[,\s]*/,'');
 value=value.replace(/^(?:(?:voce|vc)\s+)?(?:pode|poderia|consegue)\s+/,'').replace(/^(?:eu\s+)?(?:quero|gostaria)\s+(?:que\s+(?:voce|vc)\s+|de\s+)?/,'');
 if(/^(?:nao|nunca|como|explique|o que|qual|quando|onde|por que|sera que|e possivel|voce sabe|vc sabe)\b/.test(value))return null;
 if(/^(?:abr\w*|mostr\w*|entr\w*|ir|acess\w*)\b.{0,35}\b(?:estudio|studio)\b.{0,15}\b(?:sites?|web)\b/.test(value)||/^(?:abr\w*|mostr\w*)\b.{0,20}\bmeus projetos\b/.test(value))return {brief:''};
 if(/^(?:me\s+)?(?:faca|crie|criar|construa|construir|desenvolva|desenvolver|monte|montar)\b.{0,40}\b(?:site|website|landing page|pagina web)\b/.test(value))return {brief:text.replace(/^\s*(?:cronos|kronos|chronos)[,\s]*/i,'').trim()};
 return null;
}
