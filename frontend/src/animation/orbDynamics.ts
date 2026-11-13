import type {CronosState} from '../types/cronos';

/** Visual response only; capture and playback remain in the existing voice services. */
export function orbMotionTarget(state:CronosState,rawAudio:number){
 const level=Math.min(1,Math.max(0,Number.isFinite(rawAudio)?rawAudio:0));
 const audible=Math.min(1,Math.max(0,(level-.055)/.50));
 const activity=audible*audible*(3-2*audible);
 if(state==='SPEAKING')return {rate:.62+1.05*activity,energy:.18+.57*activity,expansion:.010+.050*activity};
 if(state==='LISTENING')return {rate:.25+.91*activity,energy:.035+.45*activity,expansion:.001+.030*activity};
 return {rate:.22,energy:.018,expansion:0};
}
