import assert from 'node:assert/strict';
import test from 'node:test';
import {localCommand} from '../src/commands.ts';
test('recognized navigation stays local and accepts accent/case',()=>{
 assert.deepEqual(localCommand('Kronos, abrir Olho de Deus.',false),{type:'eye'});
 assert.deepEqual(localCommand('Cronos abrir painel',false),{type:'panel'});
 assert.deepEqual(localCommand('voltar para memória',true),{type:'memory'});
 assert.deepEqual(localCommand('fechar o olho de deus',true),{type:'memory'});
});
test('global place navigation is not restricted to a predefined city',()=>{
 assert.deepEqual(localCommand('abrir cidade de São Paulo',true),{type:'place',query:'São Paulo'});
 assert.deepEqual(localCommand('abrir aeroporto Charles de Gaulle na França',true),{type:'place',query:'aeroporto Charles de Gaulle na França'});
 assert.deepEqual(localCommand('ir para Nairobi, Quênia',true),{type:'place',query:'Nairobi, Quênia'});
 assert.equal(localCommand('abrir cidade de São Paulo',false),null);
 assert.equal(localCommand('Quem foi Platão?',true),null);
});
