const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\s+/g,' ').trim();
export function cardRequest(text:string):boolean|null{
 const value=normalize(text);
 const target='(?:cards?|cartoes|cartaozinhos|cartoezinhos|cartao|textos?|respostas?|tela)';
 if(new RegExp('\\b(?:nao (?:quero (?:que voce )?)?(?:mostrar|mostre|exibir|exiba|colocar|coloque|usar|use)|ocultar|oculte|esconder|esconda|fechar|feche)\\b.*\\b'+target+'\\b').test(value))return false;
 if(/\b(?:em|nos|com|usando|por|os) (?:forma de )?(?:cards?|cartoes|cartaozinhos|cartoezinhos)\b/.test(value)||/\bna tela\b/.test(value)&&/\b(?:explique|explicar|mostre|mostrar|coloque|colocar|exiba|exibir|abrir|abra|abre|quero|ver)\b/.test(value))return true;
 if(new RegExp('\\b(?:mostre|mostrar|exiba|exibir|coloque|colocar|abrir|abra|abre)\\b.*\\b'+target+'\\b').test(value))return true;
 return null;
}
export function cardDisplayCommand(text:string):boolean|null{
 const value=normalize(text).replace(/^(?:cronos|kronos|chronos)[,\s:]+/,'').replace(/[.!?]+$/,'').replace(/[,\s]+por favor$/,'');
 if(/^(?:mostrar|mostre|exibir|exiba|colocar|coloque|abrir|abra|abre|ver) (?:(?:o|os|a|as) )?(?:cards?|cartoes|cartaozinhos|cartoezinhos|textos?|respostas?)(?: na (?:(?:minha|sua) )?tela)?$/.test(value)||/^(?:mostrar|mostre|exibir|exiba) na tela$/.test(value))return true;
 if(/^(?:ocultar|oculte|esconder|esconda|fechar|feche) (?:(?:o|os|a|as) )?(?:cards?|cartoes|textos?|respostas?)$/.test(value))return false;
 return null;
}
