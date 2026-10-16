import React,{useEffect,useState} from 'react';
import bg from '../assets/images/cosmic-nebula.png';
import './cosmic-background.css';
// A single static SVG texture supplies hundreds of stars; only 38 highlights animate.
const dust=Array.from({length:380},(_,i)=>{const x=(i*137.508)%1600,y=(i*83.17)%900,r=i%19===0?1.15:.35+(i%5)*.12;return `<circle cx="${x}" cy="${y}" r="${r}" fill="${i%9?'#dcefff':'#63beff'}" opacity="${.22+(i%7)*.09}"/>`;}).join('');
const starTexture=`url("data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">'+dust+'</svg>')}")`;
const stars=Array.from({length:38},(_,i)=>({x:(i*71.73+5)%100,y:(i*43.19+9)%100,size:i%7===0?3:1+i%2,delay:-i*.83,duration:4+i%5}));
export const CosmicBackground=React.memo(function CosmicBackground({paused=false}:{paused?:boolean}){
 const [hidden,setHidden]=useState(document.hidden);
 useEffect(()=>{const update=()=>setHidden(document.hidden);document.addEventListener('visibilitychange',update);return()=>document.removeEventListener('visibilitychange',update);},[]);
 return <div className={`cosmic-background ${paused||hidden?'cosmic-paused':''}`} aria-hidden="true" style={{backgroundImage:`url(${bg})`}}>
  <div className="cosmic-starfield" style={{backgroundImage:starTexture}}/>
  {stars.map((s,i)=><i key={i} className="cosmic-star" style={{left:s.x+'%',top:s.y+'%',width:s.size,height:s.size,animationDelay:s.delay+'s',animationDuration:s.duration+'s'}}/>)}
  <i className="cosmic-meteor meteor-one"/><i className="cosmic-meteor meteor-two"/>
 </div>;
});
