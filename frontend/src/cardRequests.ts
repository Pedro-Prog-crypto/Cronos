const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\s+/g,' ').trim();
export function cardRequest(text:string):boolean|null{
 const value=normalize(text);
 const target='(?:cards?|cartoes|cartaozinhos|cartao|texto|resposta|tela)';
 if(new RegExp('\\b(?:nao (?:quero (?:que voce )?)?(?:mostrar|mostre|exibir|exiba|colocar|coloque|usar|use)|ocultar|oculte|esconder|esconda|fechar|feche)\\b.*\\b'+target+'\\b').test(value))return false;
 if(/\b(?:em|nos|com|usando|por|os) (?:forma de )?(?:cards?|cartoes|cartaozinhos)\b/.test(value)||/\bna tela\b/.test(value)&&/\b(?:explique|explicar|mostre|mostrar|coloque|colocar|exiba|exibir|quero|ver)\b/.test(value))return true;
 if(new RegExp('\\b(?:mostre|mostrar|exiba|exibir|coloque|colocar)\\b.*\\b'+target+'\\b').test(value))return true;
 return null;
}
export function cardDisplayCommand(text:string):boolean|null{
 const value=normalize(text).replace(/^(?:cronos|kronos|chronos)[,\s:]+/,'').replace(/[.!?]+$/,'').replace(/[,\s]+por favor$/,'');
 if(/^(?:mostrar|mostre|exibir|exiba|colocar|coloque|ver) (?:(?:o|os|a|as) )?(?:cards?|cartoes|cartaozinhos|texto|resposta)(?: na tela)?$/.test(value)||/^(?:mostrar|mostre|exibir|exiba) na tela$/.test(value))return true;
 if(/^(?:ocultar|oculte|esconder|esconda|fechar|feche) (?:(?:o|os|a|as) )?(?:cards?|cartoes|texto|resposta)$/.test(value))return false;
 return null;
}
