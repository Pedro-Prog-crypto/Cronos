import assert from 'node:assert/strict';
import {ActionRouter,routeCapabilityCommand,capabilities} from '../src/capabilities.ts';

assert.equal(new Set(capabilities.map(item=>item.id)).size,capabilities.length);
assert.equal(routeCapabilityCommand('Cronos, abrir memória')?.id,'memory');
assert.equal(routeCapabilityCommand('abrir configurações')?.id,'settings');
assert.equal(routeCapabilityCommand('abrir estúdio de sites')?.id,'studio');
assert.equal(routeCapabilityCommand('Kronos, mostrar conexões')?.id,'connections');
assert.equal(routeCapabilityCommand('Me explique detalhadamente a Primeira Guerra Mundial'),undefined);
assert.equal(routeCapabilityCommand('analise este arquivo que vou enviar'),undefined);
let opened=0;
const router=new ActionRouter({memory:()=>opened++});
assert.equal(router.route('Cronos abrir memória'),true);
assert.equal(opened,1);
assert.equal(router.route('abrir configurações'),false);
assert.equal(opened,1);
console.log('UI capability routing: ok');
