import React from 'react';
import {CronosOrb} from './CronosOrb';
import {AudioWaveform,BookOpen,BookOpenCheck,Send} from 'lucide-react';
import {CronosState} from '../types/cronos';
interface Props {state:CronosState;thinking?:boolean;audioLevelSource?:React.RefObject<number>;audioLevel?:number;onOrbClick?:()=>void;onMicToggle?:()=>void;onModuleClick?:(index:number)=>void;onSendSpeech?:()=>void;canSendSpeech?:boolean;detailedExplanation?:boolean;onToggleExplanation?:()=>void;className?:string;}
// The former star modules now live in the dashboard's gear menu.
export const IntegratedNeuralStage=React.memo(function Stage({state,thinking=false,audioLevelSource,audioLevel=0,onOrbClick,onSendSpeech,canSendSpeech=false,detailedExplanation=false,onToggleExplanation,className=''}:Props){
 const visualState=state==='SPEAKING'?'SPEAKING':thinking?'THINKING':state;
 const label=visualState==='SPEAKING'?'FALANDO':visualState==='THINKING'?'PENSANDO':visualState==='LISTENING'?'OUVINDO':'EM ESPERA';
 return <div className={`cronos-reference-scene relative w-full h-full overflow-hidden select-none ${className}`}>
  <div className="reference-grid-background" aria-hidden="true"/>
  <div className="cronos-central-hologram absolute z-20 flex flex-col items-center justify-center pointer-events-auto">
   <CronosOrb state={state} audioLevel={audioLevel} audioLevelSource={audioLevelSource} onOrbClick={onOrbClick} size={620} weaveDensity={1} showCrossLinks={false}/>
   <div className="reference-voice-status" data-state={visualState} role="status"><span>{label}</span><i aria-hidden="true"/></div>
  </div>
  <button className="reference-explanation-mode" data-active={detailedExplanation} onClick={onToggleExplanation} aria-pressed={detailedExplanation} aria-label={detailedExplanation?'Voltar à explicação normal':'Ativar explicação detalhada'} title={detailedExplanation?'Explicação detalhada ativada · clique para voltar ao normal':'Explicação normal · clique para ativar a detalhada'}>{detailedExplanation?<BookOpenCheck size={19}/>:<BookOpen size={19}/>}</button>
  <button className="reference-voice-control" data-state={visualState} onClick={onOrbClick} aria-label={state==='LISTENING'?'Desligar escuta do Cronos':'Ativar controle de voz do Cronos'}><AudioWaveform size={30}/></button>
  {canSendSpeech&&<button className="reference-voice-send" onClick={onSendSpeech} aria-label="Enviar fala agora" title="Enviar agora sem esperar o silêncio"><Send size={20}/></button>}
 </div>;
});
