import React,{useEffect,useRef,useState} from 'react';
import type * as CesiumTypes from 'cesium';
import {api} from '../api';
declare global {interface Window {Cesium:typeof CesiumTypes;CESIUM_BASE_URL:string}}
let loading:Promise<void>|null=null;
function loadCesium(){
  if(window.Cesium)return Promise.resolve();
  if(!loading)loading=new Promise((resolve,reject)=>{
    window.CESIUM_BASE_URL='/ui/cesium/';
    const css=document.createElement('link');css.rel='stylesheet';css.href='/ui/cesium/Widgets/widgets.css';document.head.append(css);
    const script=document.createElement('script');script.src='/ui/cesium/Cesium.js';script.onload=()=>resolve();script.onerror=()=>{script.remove();css.remove();loading=null;reject(new Error('Não foi possível carregar o mapa.'));};document.head.append(script);
  });return loading;
}
export default function WorldMap({query,onError,onReady}:{query:string;onError:(message:string)=>void;onReady:()=>void}){
  const container=useRef<HTMLDivElement>(null),credits=useRef<HTMLDivElement>(null),viewer=useRef<CesiumTypes.Viewer|null>(null);
  const [ready,setReady]=useState(false);const callbacks=useRef({onError,onReady});callbacks.current={onError,onReady};
  useEffect(()=>{
    let alive=true;let dispose:undefined|(()=>void);
    void(async()=>{try{
      await loadCesium();if(!alive)return;
      const {createApplicationViewer,installTrackpadPinchZoom}=await import('../vendor/gods-eye/viewer.js');
      if(!alive||!container.current||!credits.current)return;
      const C=window.Cesium;C.Ion.defaultAccessToken='';
      const instance=createApplicationViewer({container:container.current,creditContainer:credits.current});viewer.current=instance;
      instance.targetFrameRate=30;instance.resolutionScale=Math.min(1,1/window.devicePixelRatio);
      instance.scene.requestRenderMode=true;instance.scene.maximumRenderTimeChange=Infinity;
      instance.scene.globe.show=true;instance.scene.globe.maximumScreenSpaceError=4;instance.scene.globe.tileCacheSize=48;
      instance.scene.globe.enableLighting=false;instance.scene.postProcessStages.fxaa.enabled=false;
      instance.imageryLayers.addImageryProvider(new C.UrlTemplateImageryProvider({
        url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',maximumLevel:18,
        credit:new C.Credit('Powered by Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community'),
      }));
      dispose=installTrackpadPinchZoom(instance);
      const visibility=()=>{instance.useDefaultRenderLoop=!document.hidden;if(!document.hidden)instance.scene.requestRender();};
      document.addEventListener('visibilitychange',visibility);const pinch=dispose;dispose=()=>{pinch?.();document.removeEventListener('visibilitychange',visibility);};
      instance.scene.renderError.addEventListener(()=>callbacks.current.onError('O dispositivo encontrou um erro ao desenhar o mapa. Feche o Olho de Deus e tente novamente.'));
      let announced=false;instance.scene.postRender.addEventListener(()=>{if(!announced&&alive){announced=true;callbacks.current.onReady();}});
      visibility();setReady(true);
    }catch(error){if(alive)callbacks.current.onError(error instanceof Error?error.message:'Seu dispositivo não conseguiu iniciar o mapa 3D.');}})();
    return()=>{alive=false;dispose?.();if(viewer.current&&!viewer.current.isDestroyed())viewer.current.destroy();viewer.current=null;};
  },[]);
  useEffect(()=>{
    if(!ready||!query.trim())return;const controller=new AbortController();let alive=true;
    void(async()=>{try{
      const data=await(await api(`/world/places?q=${encodeURIComponent(query)}`,{signal:controller.signal})).json();
      if(!alive||!viewer.current)return;
      if(!data.places?.length){callbacks.current.onError(`Não encontrei esse lugar: ${query}.`);return;}
      const place=data.places[0];const C=window.Cesium;
      viewer.current.camera.flyTo({destination:C.Cartesian3.fromDegrees(place.lon,place.lat,12000),duration:1.5});
      viewer.current.scene.requestRender();
    }catch(error){if(alive&&!controller.signal.aborted)callbacks.current.onError(error instanceof Error?error.message:'Não foi possível localizar o lugar.');}})();
    return()=>{alive=false;controller.abort();};
  },[query,ready]);
  return <div className="world-map"><div ref={container} className="world-canvas"/><div ref={credits} className="world-credits"/></div>;
}
