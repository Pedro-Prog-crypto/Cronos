// Trusted form adapter. The preview has an opaque origin and never receives a Cronos token.
(()=>{
 const config=window.__studioPreview;
 const pending=new Map();let serial=0;
 let errors=[];
 addEventListener('error',event=>{errors.push(String(event.message).slice(0,200));});
 addEventListener('unhandledrejection',event=>{errors.push(String(event.reason).slice(0,200));});
 function transport(kind,data){
  if(config)return new Promise((resolve,reject)=>{const id=String(++serial);const timer=setTimeout(()=>{pending.delete(id);reject(Error('O estúdio não respondeu. Tente novamente.'));},15000);pending.set(id,{resolve,reject,timer});parent.postMessage({studio:config.channel,type:'form',id,kind,data},'*');});
  return fetch('/api/session').then(r=>{if(!r.ok)throw Error('Sessão indisponível. Abra pelo servidor incluído na exportação.');return r.json();}).then(session=>fetch('/api/'+kind,{method:'POST',headers:{'Content-Type':'application/json','X-Studio-CSRF':session.csrf},body:JSON.stringify(data)})).then(async r=>{const result=await r.json();if(!r.ok)throw Error(result.error||'Envio recusado.');return result;});
 }
 addEventListener('message',event=>{
  if(!config||event.source!==parent||event.data?.studio!==config.channel)return;
  const value=event.data;
  if(value.type==='form-result'){const item=pending.get(value.id);if(!item)return;clearTimeout(item.timer);pending.delete(value.id);if(value.error)item.reject(Error(value.error));else item.resolve(value.result);}
  if(value.type==='test')test(value.id);
 });
 function install(){
  document.querySelectorAll('form[data-studio-form]').forEach(form=>{
   if(form.dataset.runtimeBound)return;form.dataset.runtimeBound='true';
   const trap=document.createElement('input');trap.name='company';trap.tabIndex=-1;trap.autocomplete='off';trap.hidden=true;trap.setAttribute('aria-hidden','true');form.append(trap);
   form.addEventListener('submit',async event=>{
    event.preventDefault();if(!form.reportValidity())return;
    let status=form.querySelector('[data-form-status]');if(!status){status=document.createElement('p');status.setAttribute('data-form-status','');status.setAttribute('role','status');form.append(status);}
    const data=Object.fromEntries(new FormData(form));data.consent=Boolean(form.querySelector('[name="consent"]:checked'));
    const submit=form.querySelector('[type="submit"]');if(submit)submit.disabled=true;status.textContent='Enviando…';
    try{const result=await transport(form.dataset.studioForm,data);status.textContent=(config?'TESTE LOCAL: ':'')+result.message;form.reset();}catch(error){status.textContent=error.message||'Não foi possível registrar.';}finally{if(submit)submit.disabled=false;}
   });
  });
  if(config)parent.postMessage({studio:config.channel,type:'ready'},'*');
 }
 async function test(id){
  if(document.querySelector('[data-studio-procedural]')){
   const deadline=Date.now()+8000;
   while(window.__studioProceduralState==='loading'&&Date.now()<deadline)await new Promise(resolve=>setTimeout(resolve,50));
  }
  if(window.__studioModel){
   const deadline=Date.now()+8000;
   while(window.__studioModelState==='loading'&&Date.now()<deadline)await new Promise(resolve=>setTimeout(resolve,50));
  }
  const checks=[];const add=(name,ok,detail)=>checks.push({name,status:ok?'passed':'failed',detail});
  const w=document.documentElement.clientWidth;
  if(document.querySelector('[data-studio-procedural]'))add('Modelo procedural no navegador',window.__studioProceduralState==='ready'&&Boolean(document.querySelector('[data-studio-procedural] canvas')),'Three.js iniciou a cena procedural no WebGL deste navegador.');
  add('Sem rolagem horizontal em '+w+' px',document.documentElement.scrollWidth<=w+2,'Viewport '+w+' px; largura do documento '+document.documentElement.scrollWidth+' px.');
  add('Imagens carregadas',[...document.images].every(image=>image.complete&&image.naturalWidth>0),document.images.length+' imagem(ns) observada(s).');
  add('Navegação interna',[...document.querySelectorAll('a[href^="#"]')].every(a=>a.hash.length>1&&document.getElementById(decodeURIComponent(a.hash.slice(1)))),'Destinos dos links verificados no DOM real.');
  add('Campos identificados',[...document.querySelectorAll('input:not([hidden]),textarea,select')].every(input=>input.type==='hidden'||input.labels?.length||input.getAttribute('aria-label')),'Labels ou nome acessível nos campos.');
  const forms=[...document.querySelectorAll('form[data-studio-form]')];
  add('Formulários conectados no navegador',forms.length>=2&&forms.every(form=>form.dataset.runtimeBound==='true'),'Adaptador instalado; testes adversos do backend aparecem separadamente.');
  let invalid=true;for(const form of forms){const email=form.querySelector('input[type="email"]');if(email){const old=email.value;email.value='email-invalido';invalid=invalid&&!email.checkValidity();email.value=old;}}
  add('E-mail inválido bloqueado pelo navegador',invalid&&forms.some(form=>form.querySelector('input[type="email"]')),'Validação HTML nativa; nenhum dado foi enviado.');
  add('Sem erros JavaScript observados',errors.length===0,errors.join('; ')||'Nenhum erro capturado desde a abertura desta prévia.');
  if(window.__studioModel)add('Modelo 3D carregado',window.__studioModelState==='ready'&&Boolean(document.querySelector('[data-studio-model] canvas')),'Observação do visualizador no navegador; não valida precisão técnica do produto.');
  parent.postMessage({studio:config.channel,type:'test-result',id,viewport:w,checks},'*');
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
