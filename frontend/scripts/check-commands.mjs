import assert from 'node:assert/strict';
import {localCommand} from '../src/commands.ts';
for (const phrase of ['Kronos, abrir olho de Deus', 'Cronos, abra o Olho de Deus!', 'Kronos, você pode abrir o olho de Deus, por favor?', 'Por favor, mostre o olho de Deus', 'eu gostaria de abrir o olho de Deus']) {
  assert.deepEqual(localCommand(phrase, false), {type:'eye'}, phrase);
}
for (const phrase of ['não abra o olho de Deus', 'o que é o olho de Deus?', 'procure um arquivo chamado olho de Deus', 'você pode não abrir o olho de Deus']) {
  assert.equal(localCommand(phrase, false), null, phrase);
}
assert.deepEqual(localCommand('Kronos, feche o olho de Deus', true), {type:'memory'});
assert.deepEqual(localCommand('Cronos, na escuta?', false), {type:'presence'});
assert.equal(localCommand('Cronos, na escuta? Explique Sócrates.', false), null);
assert.deepEqual(localCommand('abrir aeroporto Charles de Gaulle', true), {type:'place',query:'aeroporto Charles de Gaulle'});
console.log('PASS: direct and natural eye commands, closing, worldwide place commands, no informational or negative triggers.');
