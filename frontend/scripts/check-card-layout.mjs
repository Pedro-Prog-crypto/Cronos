import assert from 'node:assert/strict';
import {cardHome,cardPositionCommand} from '../src/cardLayout.ts';
import {orbEnergy,orbPoint} from '../src/animation/renderers.ts';
assert.equal(cardPositionCommand('Cronos, coloque os cards na direita'),'right');
assert.equal(cardPositionCommand('Deixe os cartões do lado esquerdo'),'left');
assert.equal(cardPositionCommand('Organize os cards ao redor do holograma'),'orbit');
assert.equal(cardPositionCommand('Explique a política de direita'),null);
assert.equal(cardPositionCommand('Mova a imagem para a direita'),null);
const homes=Array.from({length:6},(_,i)=>cardHome(i,6,1600,900,280,180,'orbit'));
assert.equal(homes.filter(p=>p.x+140<800).length,3);assert.equal(homes.filter(p=>p.x+140>800).length,3);
for(const p of homes){assert(p.x>=0&&p.x+280<=1600&&p.y>=0&&p.y+180<=900);}
for(let t=0;t<8;t+=.35)for(let u=0;u<Math.PI;u+=.13){
 const a=orbPoint(u,.7,t,196,.8),b=orbPoint(u+Math.PI,.7,t,196,.8);
 assert(Math.abs(a.x+b.x-600)<1e-8&&Math.abs(a.y+b.y-600)<1e-8,'opposite sides must share the same center');
}
assert(orbEnergy('LISTENING',.8)>orbEnergy('SPEAKING',.8)*3);
console.log('PASS: six cards split around the hologram, local positioning commands, balanced ring geometry and stronger microphone response than assistant speech.');
