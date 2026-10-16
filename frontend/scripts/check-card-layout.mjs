import assert from 'node:assert/strict';
import {cardHome,cardPositionCommand} from '../src/cardLayout.ts';
assert.equal(cardPositionCommand('Cronos, coloque os cards na direita'),'right');
assert.equal(cardPositionCommand('Deixe os cartões do lado esquerdo'),'left');
assert.equal(cardPositionCommand('Organize os cards ao redor do holograma'),'orbit');
assert.equal(cardPositionCommand('Explique a política de direita'),null);
assert.equal(cardPositionCommand('Mova a imagem para a direita'),null);
const homes=Array.from({length:6},(_,i)=>cardHome(i,6,1600,900,280,180,'orbit'));
assert.equal(homes.filter(p=>p.x+140<800).length,3);assert.equal(homes.filter(p=>p.x+140>800).length,3);
for(const p of homes){assert(p.x>=0&&p.x+280<=1600&&p.y>=0&&p.y+180<=900);}
console.log('PASS: six cards split around the hologram and local positioning commands.');
