import assert from 'node:assert/strict';
import {cardHoldCommand,cardTargetIndexes} from '../src/cardControl.ts';

const cards=[{title:'Tecnologia'},{title:'Agenda livre'},{title:'Política'}];
assert.deepEqual(cardHoldCommand('Cronos, mantenha card 1 e card 3'),{mode:'pin',target:'card 1 e card 3'});
assert.deepEqual(cardTargetIndexes('card 1 e card 3',cards,1),[0,2]);
assert.deepEqual(cardTargetIndexes('mantenha este card',cards,1),[1]);
assert.deepEqual(cardTargetIndexes('card de política',cards,1),[2]);
assert.deepEqual(cardHoldCommand('desfixe card 2'),{mode:'unpin',target:'card 2'});
assert.equal(cardHoldCommand('me conte sobre política'),null);
console.log('Card pin voice targets: ok');
