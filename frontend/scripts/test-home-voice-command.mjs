import assert from 'node:assert/strict';
import {routeHomeVoiceCommand,routeModuleVoiceCommand} from '../src/homeVoiceCommand.ts';
import {routeCapabilityCommand} from '../src/capabilities.ts';

assert.deepEqual(routeHomeVoiceCommand('Cronos, abra os cards.'),{action:'open',index:0});
assert.deepEqual(routeHomeVoiceCommand('abra o clima'),{action:'open',index:1});
assert.deepEqual(routeHomeVoiceCommand('mostre a agenda'),{action:'open',index:2});
assert.deepEqual(routeHomeVoiceCommand('abrir e-mail'),{action:'open',index:3});
assert.deepEqual(routeHomeVoiceCommand('observações'),{action:'open',index:7});
assert.deepEqual(routeHomeVoiceCommand('feche os painéis'),{action:'close'});
assert.equal(routeHomeVoiceCommand('qual é a previsão do tempo?'),null);
assert.equal(routeCapabilityCommand('Cronos, abra o sistema')?.id,'system');
assert.equal(routeCapabilityCommand('mostre a memória')?.id,'memory');
assert.equal(routeModuleVoiceCommand('abra o monitoramento'),11);
assert.equal(routeModuleVoiceCommand('Cronos, abrir segurança'),10);
assert.equal(routeModuleVoiceCommand('abrir planejamento'),4);
assert.equal(routeModuleVoiceCommand('qual é o clima?'),null);
console.log('Home voice navigation checks passed.');
