import assert from 'node:assert/strict';
import {studioCommand} from '../src/studioCommands.ts';
for(const text of ['Cronos, abrir estúdio de sites','Kronos, você pode abrir o estúdio de sites, por favor?','Abra o Studio de sites','Quero que você mostre o estúdio de sites'])assert.deepEqual(studioCommand(text),{brief:''},text);
for(const text of ['Cronos, faça um site para um lava-jato de Manaus','Crie um website para hotel','Você pode construir um site de uma loja?','Eu gostaria de criar uma landing page para um produto'])assert.ok(studioCommand(text)?.brief,text);
for(const text of ['Como criar um site?','Cronos, não crie um site','Não abra o estúdio de sites','Explique como fazer um site','Você sabe criar um site?','É possível criar um site em 3D?','O site está lento'])assert.equal(studioCommand(text),null,text);
console.log('PASS: local studio opening/creation requests, natural wording, negative and informational requests remain conversations.');
