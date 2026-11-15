import assert from 'node:assert/strict';
import {orbMotionTarget} from '../src/animation/orbDynamics.ts';

const idle=orbMotionTarget('IDLE',0);
const silence=orbMotionTarget('LISTENING',0);
const noise=orbMotionTarget('LISTENING',.08);
const quiet=orbMotionTarget('LISTENING',.25);
const loud=orbMotionTarget('LISTENING',.6);
const spoken=orbMotionTarget('SPEAKING',.6);

assert.equal(orbMotionTarget('IDLE',.9).rate,idle.rate);
assert.ok(noise.rate-silence.rate<.02,'background noise must not agitate the orb');
assert.ok(idle.rate<silence.rate&&silence.rate<quiet.rate&&quiet.rate<loud.rate);
assert.ok(loud.expansion>quiet.expansion&&quiet.expansion>silence.expansion);
assert.ok(spoken.rate>loud.rate&&spoken.expansion>loud.expansion);
for(const state of ['IDLE','LISTENING','SPEAKING']){
 const value=orbMotionTarget(state,NaN);
 assert.ok(Object.values(value).every(Number.isFinite));
 for(const level of [0,.08,.25,.6,1,10,-1,Infinity]){
  const motion=orbMotionTarget(state,level);
  assert.ok(motion.rate>=.65&&motion.rate<=1.2,'reference playback must stay close to its natural speed');
  assert.ok(motion.expansion>=0&&motion.expansion<=.015,'audio must not balloon the complete silhouette');
 }
}
console.log('Orb voice response: ok');
