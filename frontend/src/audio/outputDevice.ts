/** Route existing Jarvis audio; an obsolete device preference must not mute it. */
export async function routeVoiceOutput(context:AudioContext,label:string|undefined,onWarning:(message:string)=>void){
 const ctx=context as AudioContext&{setSinkId?:(id:string)=>Promise<void>};
 if(!label){if(ctx.setSinkId)await ctx.setSinkId('');return;}
 try{
  const devices=await navigator.mediaDevices.enumerateDevices();
  const chosen=devices.find(device=>device.kind==='audiooutput'&&device.label===label);
  if(chosen&&ctx.setSinkId){await ctx.setSinkId(chosen.deviceId);return;}
 }catch{/* Permissions/device changes must not prevent default-device playback. */}
 if(ctx.setSinkId){
  try{await ctx.setSinkId('');}
  catch{throw new Error('Não consegui acessar a saída de áudio padrão. Confira o dispositivo e a permissão de som do navegador.');}
 }
 onWarning('A saída de áudio salva não está disponível neste navegador. Usando a saída padrão do Windows; escolha outra no painel Síntese de voz se precisar.');
}
