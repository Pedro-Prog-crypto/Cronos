const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
export function isStudyQuestion(text:string){
 const value=normalize(text);
 return /\b(?:explique|explica|me ensine|ensine|me ajuda a entender|ajude a entender|quero entender|estude|resuma|resumo|compare|qual a diferenca|o que (?:e|foi|significa|causou)|como funciona|por que|me fale sobre|fale sobre|me explique|me explica|todas? as? obras|lista completa)\b/.test(value)
  || /\b(?:historia|filosofia|biologia|matematica|fisica|quimica|geografia|portugues|literatura|sociologia|prova|vestibular|enem|pais|guerra mundial|revolucao|filosofo|equacao|teorema|celula|mitocondria|fotossintese|primeira guerra|segunda guerra)\b/.test(value);
}
