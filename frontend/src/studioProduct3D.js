// Loaded only inside a project preview that contains a user-provided self-contained GLB.
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
(async()=>{
 const source=window.__studioModel;if(!source)return;
 const hosts=[...document.querySelectorAll('[data-studio-model]')];if(!hosts.length)return;
 for(const host of hosts.slice(0,1)){
  let renderer,controls,observer;
  try{
   window.__studioModelState='loading';
   const notice=document.createElement('p');notice.textContent='Carregando modelo 3D fornecido…';host.append(notice);
   if(!host.clientHeight)host.style.minHeight='360px';
   const scene=new THREE.Scene();scene.background=new THREE.Color('#0c1420');
   const camera=new THREE.PerspectiveCamera(40,1,.01,1000);
   renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.3));renderer.setClearColor('#0c1420');renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;
   const canvas=renderer.domElement;canvas.setAttribute('aria-label','Modelo 3D do produto. Arraste para girar e use a roda do mouse para ampliar.');canvas.tabIndex=0;canvas.style.width='100%';canvas.style.height='100%';canvas.style.display='block';canvas.style.touchAction='none';
   scene.add(new THREE.HemisphereLight(0xc7eaff,0x454047,3));const key=new THREE.DirectionalLight(0xffffff,4);key.position.set(3,5,4);scene.add(key);const back=new THREE.DirectionalLight(0x46c9ff,2);back.position.set(-3,1,-3);scene.add(back);
   const bytes=source.startsWith('data:')?Uint8Array.from(atob(source.split(',')[1]),c=>c.charCodeAt(0)).buffer:await fetch(source).then(r=>{if(!r.ok)throw Error('Modelo não recebido.');return r.arrayBuffer();});
   const gltf=await new GLTFLoader().parseAsync(bytes,'');
   const model=gltf.scene;const bounds=new THREE.Box3().setFromObject(model);const size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3());const radius=Math.max(size.x,size.y,size.z);
   if(!Number.isFinite(radius)||radius<=0)throw Error('Modelo sem geometria visível.');
   model.position.sub(center);const group=new THREE.Group();group.add(model);group.scale.setScalar(2/radius);scene.add(group);
   const pieces=[];model.traverse(object=>{if(object.isMesh){const b=new THREE.Box3().setFromObject(object);const direction=b.getCenter(new THREE.Vector3()).sub(center);if(direction.length()<.01)direction.set(.2,.2,.2);pieces.push({object,position:object.position.clone(),direction:direction.normalize()});}});
   camera.position.set(3,1.8,3.6);camera.lookAt(0,0,0);controls=new OrbitControls(camera,canvas);controls.enableDamping=false;controls.minDistance=1.1;controls.maxDistance=10;controls.target.set(0,0,0);controls.update();
   const render=()=>{if(!document.hidden&&renderer)renderer.render(scene,camera);};controls.addEventListener('change',render);
   const view=document.createElement('div');view.style.height='360px';view.style.width='100%';view.append(canvas);host.replaceChildren(view);
   const bar=document.createElement('div');bar.style.display='flex';bar.style.flexWrap='wrap';bar.style.gap='12px';bar.style.padding='14px';bar.style.alignItems='center';bar.style.color='#9fbed0';bar.style.background='#0c1420';bar.style.font='12px Arial,sans-serif';
   const reset=document.createElement('button');reset.type='button';reset.textContent='Restaurar câmera';reset.addEventListener('click',()=>{camera.position.set(3,1.8,3.6);controls.target.set(0,0,0);controls.update();render();});bar.append(reset);
   const label=document.createElement('label');label.textContent='Separar objetos existentes ';label.style.display='flex';label.style.alignItems='center';label.style.gap='10px';const explode=document.createElement('input');explode.type='range';explode.min='0';explode.max='100';explode.value='0';explode.setAttribute('aria-label','Separação dos objetos existentes no GLB');explode.disabled=pieces.length<2;explode.style.width='110px';explode.addEventListener('input',()=>{const amount=Number(explode.value)/100*radius*.22;pieces.forEach(p=>p.object.position.copy(p.position).addScaledVector(p.direction,amount));render();});label.append(explode);bar.append(label);
   const detail=document.createElement('span');detail.textContent=pieces.length+' objeto(s) no arquivo. Não são componentes técnicos reconstruídos.';bar.append(detail);host.append(bar);
   observer=new ResizeObserver(()=>{const width=view.clientWidth,height=view.clientHeight;if(!width||!height)return;renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();render();});observer.observe(view);
   canvas.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-'].includes(event.key))return;event.preventDefault();if(event.key==='+'||event.key==='-')camera.position.multiplyScalar(event.key==='+'?.9:1.1);else{const axis=new THREE.Vector3(event.key==='ArrowUp'||event.key==='ArrowDown'?1:0,event.key==='ArrowLeft'||event.key==='ArrowRight'?1:0,0);camera.position.applyAxisAngle(axis,event.key==='ArrowLeft'||event.key==='ArrowUp'?.1:-.1);}controls.update();render();});
   addEventListener('visibilitychange',render);addEventListener('pagehide',()=>{observer.disconnect();controls.dispose();scene.traverse(object=>{if(object.geometry)object.geometry.dispose();const materials=Array.isArray(object.material)?object.material:[object.material];materials.filter(Boolean).forEach(m=>{Object.values(m).forEach(value=>{if(value?.isTexture)value.dispose();});m.dispose();});});renderer.dispose();},{once:true});render();window.__studioModelState='ready';
  }catch(error){window.__studioModelState='failed';if(observer)observer.disconnect();if(controls)controls.dispose();if(renderer)renderer.dispose();const message=document.createElement('p');message.textContent='Não foi possível mostrar o GLB: '+error.message+' Use um modelo leve, autocontido e com geometria visível.';host.replaceChildren(message);}
 }
})();
