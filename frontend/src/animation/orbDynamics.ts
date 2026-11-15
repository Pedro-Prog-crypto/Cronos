import type {CronosState} from '../types/cronos';

/** Visual response only; capture and playback remain in the existing voice services. */
export function orbMotionTarget(state:CronosState,rawAudio:number){
 const level=Math.min(1,Math.max(0,Number.isFinite(rawAudio)?rawAudio:0));
 const audible=Math.min(1,Math.max(0,(level-.055)/.50));
 const activity=audible*audible*(3-2*audible);
 // Keep the coded curves calm and continuous, with a small response to audio.
 if(state==='SPEAKING')return {rate:.60+.035*activity,energy:.12+.13*activity,expansion:.001+.004*activity};
 if(state==='LISTENING')return {rate:.50+.02*activity,energy:.06+.08*activity,expansion:.001+.002*activity};
 return {rate:.42,energy:.035,expansion:0};
}
