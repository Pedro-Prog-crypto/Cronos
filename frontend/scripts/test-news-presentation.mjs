import assert from 'node:assert/strict';
import {isDailyNewsRequest,newsArticlesFromTools} from '../src/newsPresentation.ts';

assert.equal(isDailyNewsRequest('Cronos, notícias do dia'),true);
assert.equal(isDailyNewsRequest('Me mostre as notícias de hoje no Brasil'),true);
assert.equal(isDailyNewsRequest('Quais são as principais notícias do dia no Brasil?'),true);
assert.equal(isDailyNewsRequest('O que significa notícias do dia?'),false);
assert.equal(isDailyNewsRequest('Notícias do dia 10 de junho de 2015'),false);
assert.equal(isDailyNewsRequest('Notícias do dia e abra meus downloads'),false);
const articles=newsArticlesFromTools([{name:'web_news',status:'completed',result:{articles:[
 {title:'Fato verificado',url:'https://example.org/hoje',source:'Fonte',published:'Hoje',excerpt:'Resumo'},
 {title:'URL repetida',url:'https://example.org/hoje'},
 {title:'Endereço inválido',url:'javascript:alert(1)'},
 {title:'Endereço local',url:'http://127.0.0.1/private'},
]}}]);
assert.equal(articles.length,1);
assert.equal(articles[0].title,'Fato verificado');
console.log('News presentation uses only unique sourced articles.');
