import React from 'react';
import coastlines from '../vendor/gods-eye/coastlines.json';
export const HolographicGlobe=React.memo(function HolographicGlobe({onOpen}:{onOpen:()=>void}){
 return <svg viewBox="0 0 320 320" className="holographic-globe" role="button" tabIndex={0} aria-label="Abrir Olho de Deus" onClick={onOpen} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onOpen();}}}>
  <defs><radialGradient id="earth-light"><stop stopColor="#003f60" stopOpacity=".1"/><stop offset=".85" stopColor="#004c80" stopOpacity=".5"/><stop offset="1" stopColor="#23e6ff" stopOpacity=".8"/></radialGradient><filter id="earth-bloom"><feGaussianBlur stdDeviation="2"/></filter><clipPath id="earth-clip"><circle cx="160" cy="160" r="104"/></clipPath></defs>
  <circle cx="160" cy="160" r="106" fill="none" stroke="#00dfff" strokeWidth="3" opacity=".6" filter="url(#earth-bloom)"/><circle cx="160" cy="160" r="104" fill="url(#earth-light)" stroke="#47eaff"/>
  <g clipPath="url(#earth-clip)" className="earth-grid" fill="none" stroke="#0cbcf7" strokeWidth=".6" opacity=".8">
   {[-75,-50,-25,0,25,50,75].map(y=><ellipse key={'lat'+y} cx="160" cy={160+y} rx={Math.sqrt(104**2-y**2)} ry="14"/>)}
   {[22,44,66,88,104].map(x=><ellipse key={'lon'+x} cx="160" cy="160" rx={x} ry="104"/>)}
   {coastlines.map((path,index)=><path key={index} d={path} stroke="#4cdfff" strokeWidth=".5"/>)}
  </g>
  <ellipse cx="160" cy="163" rx="143" ry="10" fill="none" stroke="#00dfff" opacity=".9"/><ellipse cx="160" cy="163" rx="130" ry="6" fill="none" stroke="#86f4ff" opacity=".6"/>
  <g className="earth-beacons" stroke="#ff266c" fill="#160916"><path d="M 197 101 V 59 M 115 216 V 249"/><circle cx="197" cy="101" r="7"/><circle cx="115" cy="216" r="7"/><circle cx="197" cy="101" r="2" fill="#ff82ba"/><circle cx="115" cy="216" r="2" fill="#ff82ba"/></g>
 </svg>;
});
