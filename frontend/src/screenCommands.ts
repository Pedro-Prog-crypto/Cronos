// Only direct controls start capture; a question or a negated request never does.
export function screenCommand(text:string):'start'|'stop'|null{
 const value=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim().replace(/^(?:cronos|kronos|chronos)[,\s]*/,'').replace(/^por favor[,\s]*/,'');
 if(/^nao\s+(?:pare|desligue|encerre|feche)\b/.test(value))return null;
 if(/^(?:pare|para|parar|deixe|desligue|desliga|desligar|encerre|encerrar|feche|fechar|nao)\b.{0,65}\b(?:tela|visao|acompanhamento|compartilhamento)\b/.test(value))return 'stop';
 if(/^(?:(?:eu )?quero que (?:voce |vc )?)?(?:ver|veja|ve|olhe|olha|acompanhe|acompanha|acompanhar|observe|observar|enxergue|inicie|ative|ativar|abra|abrir)\b.{0,45}\b(?:minha tela|a tela|visao da tela|acompanhamento da tela)\b/.test(value))return 'start';
 return null;
}
