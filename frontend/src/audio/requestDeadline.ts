/** A network deadline includes response headers and the consumed body. */
export async function withRequestDeadline<T>(parent:AbortSignal,ms:number,operation:(signal:AbortSignal)=>Promise<T>):Promise<T>{
  const child=new AbortController();
  const abort=()=>child.abort(parent.reason);
  if(parent.aborted)abort();else parent.addEventListener('abort',abort,{once:true});
  let timer:ReturnType<typeof setTimeout>;
  const deadline=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{reject(new Error('O serviço de voz não respondeu a tempo. A resposta escrita continua disponível.'));child.abort();},ms);});
  try{return await Promise.race([operation(child.signal),deadline]);}
  finally{clearTimeout(timer!);parent.removeEventListener('abort',abort);}
}
