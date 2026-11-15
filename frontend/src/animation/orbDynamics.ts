import type {CronosState} from '../types/cronos';

/** Visual response only; capture and playback remain in the existing voice services. */
export function orbMotionTarget(state:CronosState,rawAudio:number){
 const level=Math.min(1,Math.max(0,Number.isFinite(rawAudio)?rawAudio:0));
 const audible=Math.min(1,Math.max(0,(level-.055)/.50));
 const activity=audible*audible*(3-2*audible);
 // One second in the atlas follows one second of the reference during speech.
 // Real audio adds a restrained response instead of stretching the whole ring.
 if(state==='SPEAKING')return {rate:1+.14*activity,energy:.12+.24*activity,expansion:.002+.009*activity};
 if(state==='LISTENING')return {rate:.85+.12*activity,energy:.06+.14*activity,expansion:.001+.004*activity};
 return {rate:.72,energy:.035,expansion:0};
}
