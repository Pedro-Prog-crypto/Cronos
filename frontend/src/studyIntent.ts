const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const cleanTitle=(text:string)=>text.replace(/^\s*#{1,3}\s*/,'').replace(/\*\*/g,'').replace(/\s*[—–:]\s*.*$/,'').replace(/^(?:a ideia central|contexto|resumo|explicacao|explicação|introducao|introdução|conclusao|conclusão|o que voce precisa saber)\s*[:—-]?\s*/i,'').replace(/^(?:a|o|as|os)\s+/i,'').trim();
export function isStudyQuestion(text:string){
 const value=normalize(text);
 return /\b(?:explique|explica|me ensine|ensine|me ajuda a entender|ajude a entender|quero entender|estude|resuma|resumo|compare|qual a diferenca|o que (?:e|foi|significa|causou)|como funciona|por que|me fale sobre|fale sobre|me explique|me explica|todas? as? obras|lista completa)\b/.test(value)
  || /\b(?:historia|filosofia|biologia|matematica|fisica|quimica|geografia|portugues|literatura|sociologia|prova|vestibular|enem|pais|guerra mundial|revolucao|filosofo|equacao|teorema|celula|mitocondria|fotossintese|primeira guerra|segunda guerra)\b/.test(value);
}

export function studyPanelTitle(question:string,reply=''){
 const isGeneric=(value:string)=>!value||/^(?:ideia central|explicacao|contexto|introducao|conclusao|resumo|resposta)$/i.test(normalize(value));
 const heading=reply.match(/^\s*#{1,3}\s+(.+)$/m)?.[1];
 const meaningfulHeading=heading&&cleanTitle(heading);
 if(meaningfulHeading&&!isGeneric(meaningfulHeading))return meaningfulHeading.slice(0,54);

 const source=question.trim().replace(/^(?:cron[oó]s|kronos|ch[oó]ronos)[,\s:-]*/i,'');
 // Prefer the actual subject named in a question, so a long spoken request never
 // becomes the large panel headline.
 const subject=source.match(/\b(?:sobre|acerca de|a respeito de|como foi|como aconteceu|o que foi|quem foi|o que é|quem é)\s+([^?!.\n,;]+)/i)?.[1]
  ?.split(/\s+(?:e|mas|tambem|também)\s+(?=(?:me|quero|inclua|explique|fale|mostre|diga|tambem|também))/i,1)[0];
 let title=subject||'';
 if(!title){
  title=source.replace(/^(?:por favor[,\s]*)?(?:me explique|explique|explica|me explica|me ensine|ensine|me fale sobre|fale sobre|quero saber sobre|quero entender|me ajuda a entender|ajude a entender|o que aconteceu com|como aconteceu|como foi|o que foi|qual foi|resuma|resuma a|resuma o|estude)\s+/i,'');
  title=title.split(/[?.!;\n]/,1)[0].split(/,\s*(?=(?:quero|inclua|explique|fale|mostre|diga|com detalhes|bem detalhad|tambem|também))/i,1)[0].trim();
 }
 title=cleanTitle(title).replace(/\s+/g,' ');
 if(isGeneric(title)){
  const firstSentence=reply.replace(/^\s*#{1,3}\s+[^\n]+\n?/m,'').split(/[.!?\n]/,1)[0];
  title=cleanTitle(firstSentence.replace(/^(?:neste texto|aqui vamos entender|vamos entender|vamos estudar)\s+/i,''));
 }
 if(isGeneric(title))title='Assunto em estudo';
 if(title.length>54)title=`${title.slice(0,51).replace(/\s+\S*$/,'')}…`;
 return title;
}
