export type Command={type:'eye'|'memory'|'panel'}|{type:'place';query:string};
export function localCommand(text:string,eyeOpen:boolean):Command|null{
 const clean=text.trim().replace(/^(?:kronos|cronos)[,\s:]+/i,'').replace(/[.!?]+$/,'');
 const normalized=clean.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 if(/^(?:abrir|abre|mostrar|ativar) (?:o )?olho de deus$/.test(normalized))return {type:'eye'};
 if(/^(?:abrir|voltar (?:para|a)|mostrar) (?:o |a )?(?:memoria|obsidian|cerebro)$/.test(normalized)||/^(?:fechar|fecha) (?:o )?olho de deus$/.test(normalized))return {type:'memory'};
 if(/^(?:abrir|abre) (?:o )?(?:painel|conversa)$/.test(normalized))return {type:'panel'};
 if(eyeOpen){const match=clean.match(/^(?:abrir|abre|mostrar|ir para|navegar para)\s+(?:(?:a )?cidade (?:de )?|(?:o )?aeroporto (?:de )?)?(.+)$/i);if(match){const airport=/aeroporto/i.test(clean);return {type:'place',query:(airport?'aeroporto ':'')+match[1]};}}
 return null;
}
