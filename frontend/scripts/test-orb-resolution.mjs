import assert from 'node:assert/strict';
import {orbRenderRatio} from '../src/animation/startCanvasWorker.ts';

const canvas=width=>({getBoundingClientRect:()=>({width})});
globalThis.window={devicePixelRatio:1};
assert.equal(orbRenderRatio(canvas(430),430),1);
window.devicePixelRatio=2;
assert.equal(orbRenderRatio(canvas(430),430),2);
window.devicePixelRatio=3;
assert.equal(Math.round(orbRenderRatio(canvas(430),430)*430),900);
assert.equal(Math.round(orbRenderRatio(canvas(256),430)*430),768);
console.log('Orb bitmap resolution: ok');
