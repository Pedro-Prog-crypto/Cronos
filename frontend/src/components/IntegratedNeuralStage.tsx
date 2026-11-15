import React from 'react';
import {CronosOrb} from './CronosOrb';
import {AudioWaveform} from 'lucide-react';
import {CronosState} from '../types/cronos';
interface Props {state:CronosState;thinking?:boolean;audioLevelSource?:React.RefObject<number>;audioLevel?:number;onOrbClick?:()=>void;onMicToggle?:()=>void;onModuleClick?:(index:number)=>void;className?:string;}
// The former star modules now live in the dashboard's gear menu.
export const IntegratedNeuralStage=React.memo(function Stage({state,thinking=false,audioLevelSource,audioLevel=0,onOrbClick,className=''}:Props){
 const visualState=state==='SPEAKING'?'SPEAKING':thinking?'THINKING':state;
 const label=visualState==='SPEAKING'?'FALANDO':visualState==='THINKING'?'PENSANDO':visualState==='LISTENING'?'OUVINDO':'EM ESPERA';
 return <div className={`cronos-reference-scene relative w-full h-full overflow-hidden select-none ${className}`}>
  <div className="reference-grid-background" aria-hidden="true"/>
  <div className="cronos-central-hologram absolute z-20 flex flex-col items-center justify-center pointer-events-auto">
   <CronosOrb state={state} audioLevel={audioLevel} audioLevelSource={audioLevelSource} onOrbClick={onOrbClick} size={620} weaveDensity={1} showCrossLinks={false}/>
   <div className="reference-voice-status" data-state={visualState} role="status"><span>{label}</span><i aria-hidden="true"/></div>
  </div>
  <button className="reference-voice-control" data-state={visualState} onClick={onOrbClick} aria-label={state==='LISTENING'?'Desligar escuta do Cronos':'Ativar controle de voz do Cronos'}><AudioWaveform size={30}/></button>
 </div>;
});
