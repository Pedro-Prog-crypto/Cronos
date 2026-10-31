/** Route existing Jarvis audio; an obsolete device preference must not mute it. */
async function deviceOperation<T>(operation:()=>Promise<T>):Promise<T>{
 let timer:ReturnType<typeof setTimeout>;
 try{return await Promise.race([operation(),new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new Error('Dispositivo de áudio não respondeu.')),1500);})]);}
 finally{clearTimeout(timer!);}
}
export async function routeVoiceOutput(context:AudioContext,label:string|undefined,onWarning:(message:string)=>void){
 const ctx=context as AudioContext&{sinkId?:string|object;setSinkId?:(id:string)=>Promise<void>};
 // New contexts already use the default sink. Some Windows WebViews expose
 // setSinkId but reject it; do not require that optional API for normal audio.
 if(!label){
  if(ctx.sinkId&&ctx.setSinkId)await deviceOperation(()=>ctx.setSinkId!(''));
  return;
 }
 try{
  const devices=await deviceOperation(()=>navigator.mediaDevices.enumerateDevices());
  const chosen=devices.find(device=>device.kind==='audiooutput'&&device.label===label);
  if(chosen&&ctx.setSinkId){await deviceOperation(()=>ctx.setSinkId!(chosen.deviceId));return;}
 }catch{/* Permissions/device changes must not prevent default-device playback. */}
 if(ctx.sinkId&&ctx.setSinkId){
  try{await deviceOperation(()=>ctx.setSinkId!(''));}
  catch{throw new Error('Não consegui acessar a saída de áudio padrão. Confira o dispositivo e a permissão de som do navegador.');}
 }
 onWarning('A saída de áudio salva não está disponível neste navegador. Usando a saída padrão do Windows; escolha outra no painel Síntese de voz se precisar.');
}
