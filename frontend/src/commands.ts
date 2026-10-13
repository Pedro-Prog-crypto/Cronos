export type Command={type:'eye'|'memory'|'panel'|'presence'}|{type:'place';query:string};
export function localCommand(text:string,eyeOpen:boolean):Command|null{
 const clean=text.trim().replace(/^(?:kronos|cronos)[,\s:]+/i,'').replace(/[.!?]+$/,'').replace(/[,\s]+por favor$/i,'').replace(/^por favor[,\s]+/i,'').replace(/^(?:(?:voce|você)\s+)?(?:pode|poderia|consegue)\s+/i,'').replace(/^eu (?:quero|gostaria de)\s+/i,'').replace(/\s+/g,' ').trim();
 const normalized=clean.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 if(/^(?:na escuta|(?:voce )?(?:esta|ta) (?:na escuta|ai|me ouvindo)|consegue me ouvir|me ouve)$/.test(normalized))return {type:'presence'};
 if(/^(?:abrir|abre|abra|mostrar|mostre|ativar|ative) (?:o )?olho de deus$/.test(normalized))return {type:'eye'};
 if(/^(?:abrir|abre|abra|voltar (?:para|a)|mostrar|mostre) (?:o |a )?(?:memoria|obsidian|cerebro)$/.test(normalized)||/^(?:fechar|fecha|feche) (?:o )?olho de deus$/.test(normalized))return {type:'memory'};
 if(/^(?:abrir|abre) (?:o )?(?:painel|conversa)$/.test(normalized))return {type:'panel'};
 if(eyeOpen){const match=clean.match(/^(?:abrir|abre|mostrar|ir para|navegar para)\s+(?:(?:a )?cidade (?:de )?|(?:o )?aeroporto (?:de )?)?(.+)$/i);if(match){const airport=/aeroporto/i.test(clean);return {type:'place',query:(airport?'aeroporto ':'')+match[1]};}}
 return null;
}
