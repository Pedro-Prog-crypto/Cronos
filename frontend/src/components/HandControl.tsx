import React,{useCallback,useEffect,useRef,useState} from 'react';
import {Hand,Square,TriangleAlert} from 'lucide-react';
import {getToken} from '../api';
import './hand-control.css';

// Local, bundled MediaPipe assets: the webcam frames and landmarks stay on this PC.
import handsScript from '@mediapipe/hands/hands.js?url';
import packedLoader from '@mediapipe/hands/hands_solution_packed_assets_loader.js?url';
import packedData from '@mediapipe/hands/hands_solution_packed_assets.data?url';
import wasmJs from '@mediapipe/hands/hands_solution_wasm_bin.js?url';
import wasm from '@mediapipe/hands/hands_solution_wasm_bin.wasm?url';
import simdWasmJs from '@mediapipe/hands/hands_solution_simd_wasm_bin.js?url';
import simdWasm from '@mediapipe/hands/hands_solution_simd_wasm_bin.wasm?url';
import handGraph from '@mediapipe/hands/hands.binarypb?url';
import handModel from '@mediapipe/hands/hand_landmark_lite.tflite?url';

type Point={x:number;y:number;z?:number};
type Results={multiHandLandmarks?:Point[][];multiHandedness?:{label?:string}[]};
type Tracker={setOptions:(value:unknown)=>void;onResults:(fn:(result:Results)=>void)=>void;initialize:()=>Promise<void>;send:(value:{image:HTMLVideoElement})=>Promise<void>;close:()=>Promise<void>};
type TrackableHand={points:Point[];side:string};
const connections:[[number,number],...Array<[number,number]>]=[[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[0,17],[17,18],[18,19],[19,20]];
const files:Record<string,string>={
 'hands_solution_packed_assets_loader.js':packedLoader,'hands_solution_packed_assets.data':packedData,
 'hands_solution_wasm_bin.js':wasmJs,'hands_solution_wasm_bin.wasm':wasm,
 'hands_solution_simd_wasm_bin.js':simdWasmJs,'hands_solution_simd_wasm_bin.wasm':simdWasm,
 'hands.binarypb':handGraph,'hand_landmark_lite.tflite':handModel,
};
let scriptPromise:Promise<void>|null=null;
async function loadTracker():Promise<Tracker>{
 const target=window as any;
 if(!target.Hands){
  scriptPromise??=new Promise<void>((resolve,reject)=>{const script=document.createElement('script');script.src=handsScript;script.async=true;script.onload=()=>resolve();script.onerror=()=>{scriptPromise=null;reject(new Error('Não consegui carregar o rastreador local de mãos.'));};document.head.append(script);});
  await scriptPromise;
 }
 if(typeof target.Hands!=='function')throw new Error('O rastreador local de mãos não iniciou.');
 const tracker=new target.Hands({locateFile:(name:string)=>files[name]||name}) as Tracker;
 tracker.setOptions({maxNumHands:2,modelComplexity:0,selfieMode:false,minDetectionConfidence:.58,minTrackingConfidence:.48});
 return tracker;
}
const distance=(a:Point,b:Point)=>Math.hypot(a.x-b.x,a.y-b.y);
const fingerUp=(points:Point[],tip:number,pip:number)=>points[tip].y<points[pip].y;

export function HandControl(){
 const [active,setActive]=useState(false),[starting,setStarting]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState(''),[hands,setHands]=useState<TrackableHand[]>([]),[cursor,setCursor]=useState<{x:number;y:number}|null>(null);
 const video=useRef<HTMLVideoElement>(null),camera=useRef<MediaStream|null>(null),tracker=useRef<Tracker|null>(null),socket=useRef<WebSocket|null>(null),loop=useRef<number|undefined>(undefined),busy=useRef(false),enabled=useRef(false),leftDown=useRef(false),rightPinched=useRef(false),lastPoint=useRef({x:.5,y:.5}),lastMove=useRef(0),lastScroll=useRef({y:0,at:0}),lastRight=useRef(0),lastDimensions=useRef({width:window.innerWidth,height:window.innerHeight});
 enabled.current=active;
 const release=useCallback(()=>{if(leftDown.current){leftDown.current=false;try{socket.current?.readyState===WebSocket.OPEN&&socket.current.send(JSON.stringify({action:'up'}));}catch{}}},[]);
 const stop=useCallback(async(message='')=>{
  enabled.current=false;setActive(false);setStarting(false);if(loop.current!==undefined)window.clearTimeout(loop.current);loop.current=undefined;
  release();const current=socket.current;socket.current=null;if(current&&current.readyState<WebSocket.CLOSING)current.close(1000,'Gestos desligados');
  camera.current?.getTracks().forEach(track=>track.stop());camera.current=null;if(video.current)video.current.srcObject=null;
  const model=tracker.current;tracker.current=null;if(model)await model.close().catch(()=>{});
  busy.current=false;rightPinched.current=false;setHands([]);setCursor(null);setStatus('');if(message)setError(message);
 },[release]);
 const send=(action:string,extra:Record<string,number>={})=>{const ws=socket.current;if(ws?.readyState===WebSocket.OPEN)ws.send(JSON.stringify({action,...extra}));};
 const detect=(result:Results)=>{
  if(!enabled.current)return;
  const all=result.multiHandLandmarks||[];setHands(all.map((points,index)=>({points,side:result.multiHandedness?.[index]?.label||`MÃO ${index+1}`})));
  const points=all[0];if(!points||points.length<21)return;
  const indexUp=fingerUp(points,8,6),middleUp=fingerUp(points,12,10),ringUp=fingerUp(points,16,14),pinkyUp=fingerUp(points,20,18);
  const pinchScale=Math.max(.035,distance(points[5],points[17]));
  const pinchLeft=distance(points[4],points[8])<pinchScale*.34;
  const pinchRight=distance(points[4],points[12])<pinchScale*.34&&!pinchLeft;
  const now=performance.now();
  if(pinchRight&&!rightPinched.current&&now-lastRight.current>500){send('right_click');lastRight.current=now;}rightPinched.current=pinchRight;
  const pointPose=indexUp&&!middleUp&&!ringUp&&!pinkyUp;
  const scrollPose=indexUp&&middleUp&&!ringUp&&!pinkyUp&&!pinchLeft;
  if(pointPose||pinchLeft){
   const target={x:Math.min(1,Math.max(0,1-points[8].x)),y:Math.min(1,Math.max(0,points[8].y))};
   const smooth={x:lastPoint.current.x+(target.x-lastPoint.current.x)*.38,y:lastPoint.current.y+(target.y-lastPoint.current.y)*.38};lastPoint.current=smooth;
   const dimensions=lastDimensions.current;setCursor({x:smooth.x*dimensions.width,y:smooth.y*dimensions.height});
   if(now-lastMove.current>45){send('move',smooth);lastMove.current=now;}
  }
  if(pinchLeft!==leftDown.current){leftDown.current=pinchLeft;send(pinchLeft?'down':'up');}
  if(scrollPose){
   const y=(points[9].y+points[0].y)*.5,previous=lastScroll.current;
   if(previous.at&&now-previous.at>120&&Math.abs(y-previous.y)>.045){send('wheel',{delta:Math.sign(previous.y-y)*120});lastScroll.current={y,at:now};}
   else if(!previous.at||now-previous.at>450)lastScroll.current={y,at:now};
  }else lastScroll.current={y:0,at:0};
 };
 const start=async()=>{
  if(active||starting)return;setError('');setStarting(true);setStatus('Conectando ao controle local…');
  try{
   if(!getToken())throw new Error('Conecte o Cronos antes de ativar os gestos.');
   if(!navigator.mediaDevices?.getUserMedia)throw new Error('A câmera precisa de permissão no navegador do Cronos.');
   const wsUrl=new URL('/gestures/control',window.location.href);wsUrl.protocol=wsUrl.protocol==='https:'?'wss:':'ws:';
   const ws=new WebSocket(wsUrl,['cronos-auth',getToken()]);socket.current=ws;
   await new Promise<void>((resolve,reject)=>{let handshaken=false;const timer=window.setTimeout(()=>reject(new Error('O controle do Windows não respondeu.')),6000);ws.onmessage=event=>{const data=JSON.parse(event.data);if(data.type==='ready'){handshaken=true;lastDimensions.current={width:window.innerWidth,height:window.innerHeight};window.clearTimeout(timer);resolve();}else if(data.type==='unavailable'){window.clearTimeout(timer);reject(new Error(data.message||'O controle global não está disponível.'));}};ws.onerror=()=>{window.clearTimeout(timer);reject(new Error('Não consegui conectar o controle local do Windows.'));};ws.onclose=()=>{window.clearTimeout(timer);if(enabled.current)void stop('O controle local foi desconectado.');else if(!handshaken)reject(new Error('Não foi possível autenticar o controle local do Windows.'));};});
   camera.current=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:320,max:640},height:{ideal:240,max:480},frameRate:{ideal:15,max:20}},audio:false});
   camera.current.getVideoTracks()[0]?.addEventListener('ended',()=>{if(enabled.current)void stop('A câmera foi desconectada. O controle por gestos foi parado.');},{once:true});
   if(!video.current)throw new Error('A câmera não ficou pronta.');video.current.srcObject=camera.current;await video.current.play();
   const model=await loadTracker();tracker.current=model;model.onResults(detect);await model.initialize();
   lastDimensions.current={width:window.innerWidth,height:window.innerHeight};enabled.current=true;setActive(true);setStarting(false);setError('');setStatus('Aponte para mover · belisque polegar e indicador para clicar/arrastar · belisque polegar e médio para clicar com botão direito · dois dedos para rolar · Esc desliga');
   const tick=async()=>{if(!enabled.current)return;const source=video.current;if(source&&source.readyState>=2&&!busy.current){busy.current=true;try{await model.send({image:source});}catch{void stop('A leitura da câmera falhou. Pare e inicie o controle novamente.');return;}finally{busy.current=false;}}loop.current=window.setTimeout(()=>void tick(),95);};void tick();
  }catch(reason){await stop();setStarting(false);setError(reason instanceof Error?reason.message:'Não foi possível iniciar o controle por gestos.');}
 };
 useEffect(()=>{const resize=()=>{lastDimensions.current={width:window.innerWidth,height:window.innerHeight};};const key=(event:KeyboardEvent)=>{if(event.key==='Escape'&&enabled.current){event.preventDefault();event.stopImmediatePropagation();void stop();}};window.addEventListener('resize',resize);window.addEventListener('keydown',key,true);return()=>{window.removeEventListener('resize',resize);window.removeEventListener('keydown',key,true);void stop();};},[stop]);
 return <>
  <video ref={video} className="hand-control-video" muted autoPlay playsInline aria-hidden="true"/>
  {!active&&!starting&&<button className="reference-attachment" aria-label="Controlar computador com as mãos" title="Controle por gestos da mão" onClick={()=>void start()}><Hand size={17}/></button>}
  {(active||starting)&&<aside className="hand-control-status" role="status"><span className="hand-control-live"/><b>{starting?'PREPARANDO CONTROLE':'CRONOS · CONTROLE POR GESTOS'}</b><p>{status}</p>{error&&<p className="hand-control-error"><TriangleAlert size={13}/>{error}</p>}<button onClick={()=>void stop()} aria-label="Parar controle por gestos"><Square size={13}/> Parar</button></aside>}
  {error&&!active&&!starting&&<div className="hand-control-error-toast" role="alert"><TriangleAlert size={14}/><span>{error}</span><button onClick={()=>setError('')} aria-label="Fechar aviso">×</button></div>}
  {active&&<svg className="hand-control-overlay" viewBox={`0 0 ${lastDimensions.current.width} ${lastDimensions.current.height}`} preserveAspectRatio="none" aria-hidden="true">
   {hands.map((hand,index)=>{const width=lastDimensions.current.width,height=lastDimensions.current.height;const pts=hand.points.map(point=>({x:(1-point.x)*width,y:point.y*height}));return <g key={index} className="hand-control-skeleton">{connections.map(([a,b],edge)=><line key={edge} x1={pts[a].x} y1={pts[a].y} x2={pts[b].x} y2={pts[b].y}/>)}{pts.map((point,node)=><circle key={node} cx={point.x} cy={point.y} r={node===8||node===4?5:2.4}/>)}<text x={pts[0].x+12} y={pts[0].y-12}>{hand.side.toUpperCase()}</text></g>;})}
   {cursor&&<g className="hand-control-reticle"><circle cx={cursor.x} cy={cursor.y} r="15"/><circle cx={cursor.x} cy={cursor.y} r="3"/><path d={`M ${cursor.x-22} ${cursor.y} H ${cursor.x-11} M ${cursor.x+11} ${cursor.y} H ${cursor.x+22} M ${cursor.x} ${cursor.y-22} V ${cursor.y-11} M ${cursor.x} ${cursor.y+11} V ${cursor.y+22}`}/></g>}
  </svg>}
 </>;
}
