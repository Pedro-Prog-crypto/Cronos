// Credencial apenas em RAM. Nunca incluir chaves de Gemini/Fish no frontend.
let token = '';
const listeners = new Set<() => void>();
export function connect(value: string) { token = value.trim(); listeners.forEach(listener => listener()); }
export function getToken() { return token; }
export function onConnection(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; }
declare global { interface Window { cronosConnect?: (token: string) => void; } }
window.cronosConnect = connect;
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
