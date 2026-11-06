import React from 'react';
import {CronosOrb} from './CronosOrb';
import {CronosLogo} from './CronosLogo';
import {CosmicBackground} from './CosmicBackground';
import {CronosState} from '../types/cronos';
interface Props {state:CronosState;audioLevelSource?:React.RefObject<number>;audioLevel?:number;onOrbClick?:()=>void;onMicToggle?:()=>void;onModuleClick?:(index:number)=>void;className?:string;}
// The former star modules now live in the dashboard's gear menu.
export const IntegratedNeuralStage=React.memo(function Stage({state,audioLevelSource,audioLevel=0,onOrbClick,className=''}:Props){
 return <div className={`relative w-full h-full overflow-hidden select-none ${className}`}>
  <CosmicBackground/>
  <div className="cronos-scene-tint" aria-hidden="true"/>
  <div className="cronos-scene-horizon" aria-hidden="true"/>
  <div className="cronos-central-hologram absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 flex flex-col items-center justify-center pointer-events-auto">
   <CronosOrb state={state} audioLevel={audioLevel} audioLevelSource={audioLevelSource} onOrbClick={onOrbClick} size={330} weaveDensity={1} showCrossLinks={false}/>
   <div className="-mt-7 flex flex-col items-center"><CronosLogo isSpeaking={state==='SPEAKING'} size="sm"/></div>
  </div>
 </div>;
});
