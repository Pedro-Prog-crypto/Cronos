import assert from 'node:assert/strict';
import {cardRequest} from '../src/cardRequests.ts';
import {explanationMode,isVisualRequest} from '../src/studyIntent.ts';

assert.equal(explanationMode('Cronos, me explique quem foi Platão'), 'text');
assert.equal(explanationMode('Cronos, me explique a Primeira Guerra Mundial'), 'text');
assert.equal(explanationMode('Quem você considera uma das pessoas mais importantes da história?'), 'text');
assert.equal(explanationMode('Cronos, me explique de forma escrita quem foi Aristóteles'), 'text');
assert.equal(explanationMode('Cronos, me mostre um texto sobre Sócrates'), 'text');
assert.equal(explanationMode('Cronos, me explique visualmente a Primeira Guerra Mundial'), 'visual');
assert.equal(explanationMode('Cronos, me explique visualmente sobre a Segunda Guerra Mundial'), 'visual');
assert.equal(explanationMode('Cronos, me mostre fotos da Primeira Guerra Mundial'), 'visual');
assert.equal(isVisualRequest('Por que as imagens não carregaram?'), false);
assert.equal(isVisualRequest('Cronos, não mostre imagens; me explique por escrito.'), false);
assert.equal(explanationMode('Cronos, tudo bem?'), null);
assert.equal(cardRequest('Cronos, me mostre um texto sobre Sócrates'), null);
assert.equal(cardRequest('Cronos, explique em cards quem foi Sócrates'), true);
console.log('Written, visual, and card routing scenarios passed.');
