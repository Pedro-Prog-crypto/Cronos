import assert from 'node:assert/strict';
import {orbPoint} from '../src/animation/proceduralOrb.ts';

const strands=[
 {offset:-42,seed:.6,spread:1},
 {offset:43,seed:27.349,spread:1},
 {offset:-27,seed:.38,spread:.75},
 {offset:26,seed:8.14,spread:.75},
];
let maximumStep=0;
for(const strand of strands){
 for(let phase=0;phase<30;phase+=.1){
  for(let index=0;index<360;index+=3){
   const angle=index*Math.PI/180;
   const first=orbPoint(angle,strand,phase,.035,0);
   const next=orbPoint(angle,strand,phase+.02,.07,.001);
   const radius=Math.hypot(first.x-300,first.y-300);
   assert.ok(radius>=135&&radius<=245,{strand,phase,angle,radius});
   maximumStep=Math.max(maximumStep,Math.hypot(next.x-first.x,next.y-first.y));
  }
 }
}
assert.ok(maximumStep<3,JSON.stringify({maximumStep}));
console.log(`Orb geometry stays within the ring; largest state step ${maximumStep.toFixed(2)} px.`);
