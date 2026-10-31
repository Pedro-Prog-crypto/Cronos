import React,{useEffect,useRef,useState} from 'react';
import {jsonApi} from '../api';
const labels:Record<string,string>={audio_received:'Áudio chegou ao servidor',recognition_requested:'Pedido de reconhecimento iniciado',recognition_http:'Retorno HTTP do reconhecimento',recognition_response:'Reconhecedor devolveu texto',recognition_error:'Falha do serviço de reconhecimento',question_recognized:'Pergunta reconhecida',question_received:'Pergunta chegou à conversa',answer_requested:'Pedido à IA iniciado',answer_received:'Resposta da IA recebida',voice_requested:'Texto enviado para preparar a voz',voice_received:'Áudio da voz recebido',playback_started:'Reprodução iniciada',failed:'Falha nesta etapa',cancelled:'Pedido interrompido no aplicativo'};
export function DeliveryStatus({microphone,voice}:{microphone:any;voice:any}){
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[loadError,setLoadError]=useState(''),[copied,setCopied]=useState(false),[showReport,setShowReport]=useState(false);
 useEffect(()=>{let live=true;const load=async()=>{try{const value=await jsonApi('/voice/delivery');if(live){setData(value);setLoadError('');}}catch{if(live)setLoadError('Não consegui consultar as etapas de entrega.');}};void load();const timer=setInterval(load,2000);return()=>{live=false;clearInterval(timer);};},[]);
 const latest=data?.turns?.[0];
 const [testing,setTesting]=useState(false),[probe,setProbe]=useState<any>(null);
 const alive=useRef(true);
 const audioUrl=useRef(''),probeStarted=useRef(0),resumeMic=useRef(false);
 const restoreMic=()=>{if(resumeMic.current){resumeMic.current=false;void microphone.start();}};
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;if(audioUrl.current)URL.revokeObjectURL(audioUrl.current);if(document.visibilityState==='visible')restoreMic();};},[]);
 const test=async()=>{
  probeStarted.current=performance.now();resumeMic.current=Boolean(microphone.recording);microphone.stop();voice.stop();
  setTesting(true);setError('');setProbe(null);
  try{const result=await jsonApi('/voice/check',{});if(!alive.current)return;if(audioUrl.current)URL.revokeObjectURL(audioUrl.current);
   audioUrl.current=URL.createObjectURL(new Blob([Uint8Array.from(atob(result.audio_base64),(c:string)=>c.charCodeAt(0))],{type:result.mime_type}));
   setProbe({url:audioUrl.current,turn:result.turn_id,answer:result.answer,prepared_ms:Math.round(performance.now()-probeStarted.current)});setData(await jsonApi('/voice/delivery'));
  }catch(error){if(!alive.current)return;restoreMic();setError(error instanceof Error?error.message:'O teste não terminou.');setData(await jsonApi('/voice/delivery').catch(()=>null));}
  finally{if(alive.current)setTesting(false);}
 };
 return <section className="panel-box"><h3>ENTREGA DA ÚLTIMA PERGUNTA</h3><p>Meta: começar a falar em até 25 segundos. As confirmações abaixo vêm desta instalação; uma saudação local não confirma resposta da IA.</p>{loadError&&<p role="alert">{loadError}</p>}{error&&<p role="alert">{error}</p>}
 {data&&<small>Chaves presentes: Gemini {data.configured.gemini?'sim':'não'} · Fish Audio {data.configured.fish?'sim':'não'}. Presença de chave não comprova acesso ou crédito.</small>}
 <button disabled={testing} onClick={()=>void test()}>{testing?'TESTANDO AS INTEGRAÇÕES…':'TESTAR IA E VOZ'}</button>
 <small>Executa uma pergunta nova nas integrações cadastradas. O áudio precisa conter a resposta da IA; a saudação local não é usada.</small>
 {probe&&<div><p>A IA respondeu: {probe.answer}. Ouça o áudio devolvido pelo Fish:</p><audio controls autoPlay src={probe.url} onEnded={restoreMic} onError={()=>{setError('O áudio retornou, mas não pôde ser reproduzido no dispositivo.');restoreMic();}} onPlaying={()=>{const elapsed=Math.round(performance.now()-probeStarted.current);void jsonApi('/panels/latency',{turn_id:probe.turn,source:'text',chat_ms:probe.prepared_ms,status:'responding',first_audio_ms:elapsed,response_ms:elapsed}).catch(()=>{});}}/></div>}
 {!latest&&<p>Envie uma pergunta pelo microfone para acompanhar a entrega.</p>}
 {latest&&<ol>{latest.events.map((event:any,index:number)=><li key={index}><b>{labels[event.stage]||event.stage}</b> · {(event.elapsed_ms/1000).toFixed(1)} s{event.provider?` · ${event.provider}`:''}{event.bytes!==undefined?` · ${event.bytes} bytes`:''}{event.characters!==undefined?` · ${event.characters} caracteres`:''}{event.http_status?` · status ${event.http_status}`:''}{event.error_type?` · ${event.error_type}`:''}</li>)}</ol>}
 <button disabled={!data} onClick={()=>{void(async()=>{try{if(!navigator.clipboard?.writeText)throw new Error('clipboard unavailable');await navigator.clipboard.writeText(JSON.stringify(data,null,2));setCopied(true);}catch{setShowReport(true);}})();}}>{copied?'DIAGNÓSTICO COPIADO':'COPIAR DIAGNÓSTICO'}</button>
 {showReport&&<label>Selecione e copie o diagnóstico<textarea aria-label="Diagnóstico de entrega" readOnly rows={8} value={JSON.stringify(data,null,2)} onFocus={event=>event.currentTarget.select()}/></label>}
 <small>O diagnóstico contém etapas e tempos, sem áudio, perguntas, respostas ou chaves.</small></section>;
}
