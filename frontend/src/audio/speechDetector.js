// WebRTC's small classical VAD. No neural model, external service, or identity claim.
import createFvad from '@echogarden/fvad-wasm';

export async function createSpeechDetector(binary,mode=2){
  const module=await createFvad({wasmBinary:binary,locateFile:()=>'',print:()=>{},printErr:()=>{}});
  const handle=module._fvad_new(),pointer=module._malloc(640);
  if(!handle||!pointer)throw new Error('Não foi possível preparar o detector local de voz.');
  module._fvad_set_sample_rate(handle,16000);module._fvad_set_mode(handle,mode);
  return {
    process(samples){
      if(samples.length!==320)throw new Error('O detector requer quadros de 20 ms a 16 kHz.');
      module.HEAP16.set(samples,pointer>>1);const result=module._fvad_process(handle,pointer,samples.length);
      if(result<0)throw new Error('Quadro inválido do detector de voz.');
      // Broadband hiss can inherit VAD hangover from a preceding word. It
      // must not renew the phrase indefinitely; brief unvoiced consonants
      // remain in the buffered audio and are protected by the silence window.
      let crossings=0;for(let i=1;i<samples.length;i++)if((samples[i]<0)!==(samples[i-1]<0))crossings++;
      return result===1&&crossings<samples.length*.42;
    },
    mode(value){module._fvad_set_mode(handle,value);},
    reset(){module._fvad_reset(handle);},
    dispose(){module._free(pointer);module._fvad_free(handle);}
  };
}
