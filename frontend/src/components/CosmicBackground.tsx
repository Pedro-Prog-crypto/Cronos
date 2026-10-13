import React,{useEffect,useState} from 'react';
import bg from '../assets/images/cosmic-nebula.png';
import './cosmic-background.css';
const stars=Array.from({length:38},(_,i)=>({x:(i*71.73+5)%100,y:(i*43.19+9)%100,size:i%7===0?3:1+i%2,delay:-i*.83,duration:4+i%5}));
export const CosmicBackground=React.memo(function CosmicBackground({paused=false}:{paused?:boolean}){
 const [hidden,setHidden]=useState(document.hidden);
 useEffect(()=>{const update=()=>setHidden(document.hidden);document.addEventListener('visibilitychange',update);return()=>document.removeEventListener('visibilitychange',update);},[]);
 return <div className={`cosmic-background ${paused||hidden?'cosmic-paused':''}`} aria-hidden="true" style={{backgroundImage:`url(${bg})`}}>
  {stars.map((s,i)=><i key={i} className="cosmic-star" style={{left:s.x+'%',top:s.y+'%',width:s.size,height:s.size,animationDelay:s.delay+'s',animationDuration:s.duration+'s'}}/>)}
  <i className="cosmic-meteor meteor-one"/><i className="cosmic-meteor meteor-two"/>
 </div>;
});
