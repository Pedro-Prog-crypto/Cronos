// Credencial apenas em RAM. Nunca incluir chaves de Gemini/Fish no frontend.
let token = '';
const listeners = new Set<() => void>();
export function connect(value: string) { token = value.trim(); listeners.forEach(listener => listener()); }
export function getToken() { return token; }
export function onConnection(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; }
declare global { interface Window { cronosConnect?: (token: string) => void; } }
window.cronosConnect = connect;
// O iniciador local envia uma credencial temporária pelo fragmento, nunca ao servidor.
const launch = new URLSearchParams(window.location.hash.slice(1));
const browserToken = launch.get('cronos-session');
if (browserToken) {
  history.replaceState(null, '', window.location.pathname + window.location.search);
  connect(browserToken);
}
export class ApiError extends Error {
  constructor(message: string, public status: number, public detail?: any) { super(message); }
}
export async function api(path: string, options: RequestInit = {}) {
  if (!token) throw new ApiError('Conecte o backend para usar esta função.', 401);
  const response = await fetch(path, {...options, headers: {...options.headers, Authorization: `Bearer ${token}`}});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(typeof body.detail === 'string' ? body.detail : body.detail?.message || `A operação falhou (HTTP ${response.status}).`, response.status, body.detail);
  }
  return response;
}
export async function jsonApi(path: string, body?: unknown) {
  return (await api(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})).json();
}

// The native bridge may become ready before or after React loads.
async function nativeConnection(){
 const bridge=(window as any).pywebview?.api;
 if(!bridge?.connection)return;
 try{const result=await bridge.connection();if(result?.token)connect(result.token);}catch{/* Startup injection remains a fallback. */}
}
window.addEventListener('pywebviewready',()=>void nativeConnection());
void nativeConnection();
// Only an HttpOnly, same-host cookie established by an authenticated managed session
// may restore the in-memory token after a page reload. No localStorage credentials.
if(!getToken())void fetch('/connection',{headers:{Accept:'application/json'}}).then(async response=>{
 if(response.ok&&!getToken()){const data=await response.json();if(typeof data.token==='string')connect(data.token);}
}).catch(()=>{});


// Deliver the finished answer while its memory metadata is still arriving.
// No automatic retry: a repeated request could repeat tools or consume quota.
export async function streamChat(body:unknown,signal:AbortSignal,onReply:(reply:string)=>void,onIntro?:(reply:string)=>void,onTranscript?:(text:string)=>void,audio?:Blob){
  const session=(body as any)?.session_id;
  const heardContext=(body as any)?.heard_context;
  const path=audio?'/chat/audio/stream'+(session?'?session_id='+encodeURIComponent(session):''):'/chat/stream';
  const response=await api(path,{method:'POST',headers:{'Content-Type':audio?'audio/wav':'application/json',...(audio&&heardContext?{'X-Cronos-Heard-Context':encodeURIComponent(String(heardContext))}:{})},body:audio||JSON.stringify(body),signal});
  const reader=response.body?.getReader();
  let buffer='',result:any=null;
  const event=(line:string)=>{
    if(!line.trim())return;
    const data=JSON.parse(line);
    if(data.type==='transcript')onTranscript?.(data.text);
    if(data.type==='intro')onIntro?.(data.reply);
    if(data.type==='reply')onReply(data.reply);
    if(data.type==='result')result=data.result;
    if(data.type==='error')throw new ApiError(data.detail?.message||'Não foi possível conversar.',data.status,data.detail);
  };
  if(reader){
    const decoder=new TextDecoder();
    try{while(true){const next=await reader.read();buffer+=decoder.decode(next.value,{stream:!next.done});let end;while((end=buffer.indexOf('\n'))>=0){event(buffer.slice(0,end));buffer=buffer.slice(end+1);}if(next.done)break;}event(buffer);}
    finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
  }else{for(const line of (await response.text()).split('\n'))event(line);}
  if(!result)throw new ApiError('A resposta foi interrompida antes da conclusão.',502);
  return result;
}
