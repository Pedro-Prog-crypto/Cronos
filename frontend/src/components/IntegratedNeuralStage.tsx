import React from 'react';
import {CronosOrb} from './CronosOrb';
import {CronosLogo} from './CronosLogo';
import {CosmicBackground} from './CosmicBackground';
import {modules} from '../panels/modules';
import {CronosState} from '../types/cronos';
interface Props {state:CronosState;audioLevelSource?:React.RefObject<number>;audioLevel?:number;onOrbClick?:()=>void;onMicToggle?:()=>void;onModuleClick?:(index:number)=>void;className?:string;}
// The tree is stationary: only the central hologram requires a rendering worker.
const rays=Array.from({length:56},(_,i)=>{const a=i*Math.PI*2/56;const r=26+(i*17)%52;return {x:120+Math.cos(a)*r,y:88+Math.sin(a)*r};});
export const IntegratedNeuralStage=React.memo(function Stage({state,audioLevelSource,audioLevel=0,onOrbClick,onModuleClick,className=''}:Props){
 return <div className={`relative w-full h-full overflow-hidden select-none ${className}`}>
  <CosmicBackground/>
  <div className="cronos-central-hologram absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 flex flex-col items-center justify-center pointer-events-auto">
   <CronosOrb state={state} audioLevel={audioLevel} audioLevelSource={audioLevelSource} onOrbClick={onOrbClick} size={440} weaveDensity={1} showCrossLinks/>
   <div className="-mt-7 flex flex-col items-center"><CronosLogo isSpeaking={state==='SPEAKING'} size="sm"/></div>
  </div>
  <div className="function-tree hidden lg:block">
   <svg viewBox="0 0 380 590" fill="none" aria-label="Funções do Kronos">
    <defs>
     <radialGradient id="stationary-star"><stop stopColor="#ffffff"/><stop offset=".15" stopColor="#caffff"/><stop offset=".33" stopColor="#4bddff" stopOpacity=".5"/><stop offset="1" stopColor="#00cfff" stopOpacity="0"/></radialGradient>
    </defs>
    {modules.map((m,i)=>{const y=28+i*45,color=[1,2,4,5].includes(i)?'#ff2255':'#00eaff',d=`M120 88 C162 114, 166 ${y}, 214.5 ${y}`,Icon=m.icon;
     return <g key={m.id}>
      <g className="tree-link" pointerEvents="none"><path d={d} stroke={color} strokeWidth="6" opacity=".08"/><path d={d} stroke={color} strokeWidth="2.4" opacity=".3"/><path d={d} stroke={color} strokeWidth="1"/><path d={d} stroke="#eaffff" strokeWidth=".35" opacity=".65"/></g>
      <g className="tree-node" role="button" tabIndex={0} aria-label={m.name} onClick={()=>onModuleClick?.(i)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onModuleClick?.(i);}}}>
       <rect x="207" y={y-19} width="171" height="38" fill="transparent"/>
       <circle cx="225" cy={y} r="14" stroke={color} strokeWidth="5" opacity=".1"/><circle cx="225" cy={y} r="10.5" stroke={color} fill="#03101a"/>
       <foreignObject x="218" y={y-7} width="14" height="14"><Icon size={14} color={color}/></foreignObject>
       <text x="242" y={y+(i===3||i===1?-3:3.5)} fill={color}>{i===3?<><tspan x="242">ENTENDIMENTO</tspan><tspan x="242" dy="11">DE LINGUAGEM</tspan></>:i===1?<><tspan x="242">VISÃO</tspan><tspan x="242" dy="11">COMPUTACIONAL</tspan></>:m.name}</text>
      </g>
     </g>;
    })}
    <g className="tree-star">
     <circle cx="120" cy="88" r="105" fill="url(#stationary-star)"/>
     {rays.map((r,i)=><path key={i} d={`M120 88 L${r.x} ${r.y}`} stroke="#afffff" strokeWidth=".5" opacity={.15+(i%5)*.07}/>)}
     <path d="M15 88 H225 M120 8 V168" stroke="#7eefff" opacity=".25"/>
     <circle cx="120" cy="88" r="15" stroke="#aaffff" strokeWidth=".7"/><circle cx="120" cy="88" r="5" fill="#fff"/>
    </g>
   </svg>
  </div>
 </div>;
});
