import assert from 'node:assert/strict';
import {prospectCommand} from '../src/prospectCommands.ts';
for(const city of ['Brasília, DF','Manaus, AM','Rio de Janeiro, RJ']){
 assert.deepEqual(prospectCommand(`Kronos, me fale um dos restaurantes que estão precisando de site em ${city}`),{city,category:'restaurante'});
}
assert.deepEqual(prospectCommand('procurar pizzarias sem site em Recife, PE'),{city:'Recife, PE',category:'pizzaria'});
assert.deepEqual(prospectCommand('abrir painel de prospecção'),{city:'',category:'restaurante'});
assert.equal(prospectCommand('Não procurar restaurantes sem site em Manaus'),null);
assert.equal(prospectCommand('Qual é o melhor restaurante em Manaus?'),null);
console.log('PASS: Brazil-wide city commands, category, open panel, negative and informational requests do not trigger.');
