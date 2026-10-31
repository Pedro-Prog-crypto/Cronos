import assert from 'node:assert/strict';
import {attachmentCommand} from '../src/attachmentCommand.ts';
import {cardPositionCommand} from '../src/cardLayout.ts';
import {screenCommand} from '../src/screenCommands.ts';

// 10,000 distinct utterances: command scope, politeness, object, verb and ASR
// formatting. These check popup routing, not real microphone/cloud playback.
const prefixes=[['',true],['Cronos, ',true],['Kronos: ',true],['Por favor, ',true],['Cronos, por favor, ',true],
 ['Não ',false],['Cronos, não ',false],['Não quero que você ',false],['Por que você vai ',false],
 ['Quando você puder ',false],['Eu disse para não ',false],['Minha professora pediu para ',false],
 ['O sistema insiste em ',false],['Será que você vai ',false],['Você não deveria ',false],
 ['Não precisa ',false],['Eu queria entender por que você tenta ',false],['Explique o significado de ',false],
 ['O botão dizia para ',false],['Ele sempre tenta ',false]];
const verbs=['analise','analisar','examine','examinar','abra','abrir','envie','enviar','carregue','carregar'];
const targets=[['a imagem','image'],['essa foto','image'],['uma fotografia','image'],['esta imagem','image'],['minha foto','image'],
 ['o arquivo','document'],['esse zip','document'],['um código','document'],['este arquivo','document'],['meu zip','document']];
const styles=[s=>s,s=>s.toUpperCase(),s=>`  ${s}  `,s=>s.replaceAll(' ','   '),s=>`${s}, por favor.`];
let passed=0;const seen=new Set();
for(const [prefix,direct] of prefixes)for(const verb of verbs)for(const [target,expected] of targets)for(const style of styles){
 const text=style(`${prefix}${verb} ${target}`);assert(!seen.has(text));seen.add(text);
 assert.equal(attachmentCommand(text),direct?expected:null,text);passed++;
}
for(const text of ['Não mova os cards para a direita','A IA insiste em colocar os cards à esquerda','Por que ele deixa as respostas do lado direito?'])assert.equal(cardPositionCommand(text),null,text);
assert.equal(cardPositionCommand('Cronos, coloque os cards à direita'),'right');
assert.equal(cardPositionCommand('Por favor, mova os cards à esquerda'),'left');
assert.equal(screenCommand('Não estou conseguindo ver a minha tela'),null);
assert.equal(screenCommand('Não pare de ver a tela'),null);
assert.equal(screenCommand('Cronos, não acompanhe minha tela'),'stop');
assert.equal(screenCommand('Cronos, olhe minha tela'),'start');
console.log(JSON.stringify({routing_checks_passed:passed,regressions_passed:9,scope:'Synthetic command routing; not cloud/physical audio validation'}));
