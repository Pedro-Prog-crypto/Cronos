import React,{useEffect,useState} from 'react';
import './ResponseClock.css';

const seconds=(ms:number)=>`${(ms/1000).toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})} s`;

export function ResponseClock({turn,onDetails}:{turn:any;onDetails:()=>void}) {
  const [now,setNow]=useState(performance.now());
  const waiting=turn?.status==='waiting';
  useEffect(()=>{
    if(!waiting)return;
    setNow(performance.now());
    const timer=setInterval(()=>setNow(performance.now()),100);
    return()=>clearInterval(timer);
  },[waiting,turn?.turn_id]);
  if(!turn)return null;
  const offset=(turn.endpoint_ms||0)+(turn.recognitionBeforeSend||0);
  const elapsed=waiting?Math.max(0,now-turn.started)+offset:(turn.elapsed_ms||0)+offset;
  const failed=turn.status==='failed',cancelled=turn.status==='cancelled';
  const measured=turn.response_ms??(turn.first_text_ms===undefined?undefined:turn.first_text_ms+offset);
  const label=failed?'Resposta interrompida':cancelled?'Interrompido pelo senhor':waiting?(turn.stage==='recognition'?'Transcrevendo':turn.first_text_ms===undefined?'Preparando resposta':'Preparando voz'):turn.response_ms!==undefined?'Voz começou em':'Texto chegou em';
  return <button className="response-clock" onClick={onDetails} aria-label="Ver tempos das respostas" title="Meta: começar a responder em até 25 segundos. Clique para ver o histórico medido.">
    <span>{label}</span><b>{seconds(failed||cancelled||waiting?elapsed:measured??elapsed)}</b>
  </button>;
}

export function ResponseHistory({rows}:{rows:any[]}) {
  if(!rows?.length)return null;
  const status:Record<string,string>={waiting:'Aguardando',responding:'Iniciou',completed:'Concluiu',cancelled:'Cancelado',failed:'Falhou'};
  return <div className="panel-box response-history"><h3>TEMPO DE CADA PERGUNTA</h3>
    <p>Meta: iniciar a voz em até 25 s. Nas perguntas faladas, o total inclui detecção de silêncio e transcrição. Cancelamentos e falhas também ficam registrados.</p>
    <table><thead><tr><th>Horário</th><th>Entrada</th><th>Até iniciar a voz</th><th>Resultado</th></tr></thead><tbody>
      {[...rows].reverse().map(row=><tr key={row.turn_id}><td>{row.recorded_at?new Date(row.recorded_at).toLocaleTimeString('pt-BR'):'—'}</td><td>{row.source==='voice'?'Voz':'Texto'}</td><td>{row.response_ms===undefined||row.response_ms===null?'—':seconds(row.response_ms)}</td><td>{status[row.status]||'Registrado'}</td></tr>)}
    </tbody></table><small>Últimas {rows.length} perguntas. Registro local, sem guardar o conteúdo da conversa neste histórico de tempos. “—” significa que o início da voz não foi medido.</small>
  </div>;
}
