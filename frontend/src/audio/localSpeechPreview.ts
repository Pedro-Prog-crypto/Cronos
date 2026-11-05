// Incremental PCM recognition on Cronos's loopback server. The recorded audio
// remains available when the Portuguese model or socket is unavailable.
type SocketLike={readyState:number;bufferedAmount?:number;onopen:(()=>void)|null;onmessage:((event:{data:string})=>void)|null;
 onerror:(()=>void)|null;onclose:(()=>void)|null;send:(data:string|ArrayBuffer)=>void;close:()=>void};
type Host={WebSocket:new(url:string)=>SocketLike;location:{href:string}};

export function createLocalSpeechPreview(onUpdate:(text:string)=>void,token:string,host:Host=globalThis as unknown as Host){
 if(!token||!host.WebSocket||!host.location)return null;
 const endpoint=new URL('/voice/live-transcript',host.location.href);
 endpoint.protocol=endpoint.protocol==='https:'?'wss:':'ws:';
 let socket:SocketLike;
 try{socket=new host.WebSocket(endpoint.href);}catch{return null;}
 let ready=false,failed=false,closed=false,complete=false,finalText='',finishRequested=false;
 let pending:ArrayBuffer[]=[],pendingBytes=0;
 let finished:(()=>void)|null=null;
 const resolve=()=>finished?.();
 const flush=()=>{
  if(!ready||closed||failed)return;
  try{
   for(const frame of pending)socket.send(frame);
   pending=[];pendingBytes=0;
   if(finishRequested)socket.send(JSON.stringify({type:'finish'}));
  }catch{failed=true;resolve();}
 };
 socket.onopen=()=>{if(closed)return;try{socket.send(JSON.stringify({token}));}catch{failed=true;resolve();}};
 socket.onmessage=event=>{
  if(closed)return;
  let data:{type?:string;text?:string};
  try{data=JSON.parse(event.data);}catch{return;}
  if(data.type==='ready'){ready=true;flush();return;}
  if(data.type==='partial'&&typeof data.text==='string'){onUpdate(data.text);return;}
  if(data.type==='final'){finalText=typeof data.text==='string'?data.text.trim():'';complete=true;onUpdate(finalText);resolve();return;}
  if(data.type==='unavailable'){failed=true;resolve();}
 };
 socket.onerror=()=>{failed=true;resolve();};
 socket.onclose=()=>{if(!complete){failed=true;resolve();}};
 return {
  push(samples:Int16Array){
   if(closed||failed||finishRequested||!samples.length)return;
   const frame=new ArrayBuffer(samples.byteLength);
   new Int16Array(frame).set(samples);
   if(ready){
    if((socket.bufferedAmount||0)>256000){failed=true;socket.close();resolve();return;}
    try{socket.send(frame);}catch{failed=true;resolve();}return;
   }
   pendingBytes+=frame.byteLength;
   if(pendingBytes>256000){failed=true;pending=[];socket.close();resolve();return;}
   pending.push(frame);
  },
  async finish(durationSeconds:number){
   if(closed)return null;
   finishRequested=true;flush();
   if(!complete&&!failed){
    let timeout:ReturnType<typeof setTimeout>|undefined;
    try{await Promise.race([
     new Promise<void>(resolve=>{finished=resolve;}),
     new Promise<void>(resolve=>{timeout=setTimeout(resolve,2500);}),
    ]);}finally{clearTimeout(timeout);}
   }
   closed=true;finished=null;pending=[];socket.close();
   const words=finalText.split(/\s+/).filter(Boolean);
   return !failed&&complete&&words.length>=Math.max(3,Math.floor(durationSeconds*.75))?finalText:null;
  },
  abort(){closed=true;finished=null;pending=[];socket.close();},
 };
}
