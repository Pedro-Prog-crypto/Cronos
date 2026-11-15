import assert from 'node:assert/strict';
import {deckPlacement,spokenSectionIndex} from '../src/animation/referenceDeck.ts';

const sections=[
 {title:'Clima',body:'O tempo está aberto em Maragogi e a temperatura é agradável.'},
 {title:'Agenda',body:'Você não tem compromissos marcados para hoje.'},
 {title:'E-mail',body:'Há cinco mensagens que precisam de atenção.'},
];
assert.equal(spokenSectionIndex(sections,'Você não tem compromissos marcados para hoje.'),1);
assert.equal(spokenSectionIndex(sections,'Há cinco mensagens que precisam de atenção.'),2);
assert.equal(spokenSectionIndex(sections,'Uma frase sem correspondência nos cards.'),null);
const desktop=Array.from({length:8},(_,i)=>deckPlacement(i,8,false,true,1440,900));
assert.deepEqual(desktop.slice(0,4).map(p=>p.y),Array(4).fill(desktop[0].y));
assert.ok(desktop[4].y>desktop[0].y);
const mobile=Array.from({length:8},(_,i)=>deckPlacement(i,8,false,true,390,844));
assert.equal(mobile[0].y,mobile[1].y);
assert.ok(mobile[2].y>mobile[0].y);
assert.ok(deckPlacement(0,8,true,false,390,844).scale===1);
console.log('Reference deck checks passed.');
