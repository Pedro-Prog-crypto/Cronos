import http from 'node:http';
import crypto from 'node:crypto';
import fs from 'node:fs';
const state=process.env.CRONOS_EYE_STATE;
const {localProviderPlugins}=await import('./server/providers/local.js');
const {keySetupEndpoint}=await import('./server/standalone/key-setup.js');
if(state&&fs.existsSync(state+'/.env'))process.loadEnvFile(state+'/.env');
const secret=Buffer.from(process.env.CRONOS_EYE_SECRET||'');
const routes=[];
const server=http.createServer((req,res)=>{
  const provided=Buffer.from(req.headers['x-cronos-eye-secret']||'');
  if(!secret.length||provided.length!==secret.length||!crypto.timingSafeEqual(provided,secret)){res.writeHead(401);res.end();return;}
  if(req.url==='/api/cronos/browser-config'){res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.end(JSON.stringify({googleApiKey:process.env.GOOGLE_MAPS_API_KEY||'',cesiumToken:process.env.CESIUM_ION_TOKEN||''}));return;}
  if(req.url==='/health'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({ready:true}));return;}
  // Voice stays with Cronos; no separate paid Realtime session is created.
  if(/^\/api\/(?:openai|realtime|chatgpt|local-receivers)(?:\/|\?|$)/.test(req.url)){res.writeHead(503,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Use the Cronos voice connection. This provider is disabled in the embedded application.'}));return;}
  req.originalUrl=req.url;
  let index=0;
  function next(error){
    if(error){if(!res.headersSent)res.writeHead(502,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Data provider failed.'}));return;}
    const route=routes[index++];
    if(!route){res.writeHead(404,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Unknown data endpoint.'}));return;}
    const pathname=req.url.split('?')[0];
    if(route.path&&pathname!==route.path&&!pathname.startsWith(route.path+'/')){next();return;}
    const before=req.url;
    if(route.path)req.url=req.url.slice(route.path.length)||'/';
    const done=(error)=>{req.url=before;next(error);};
    try{Promise.resolve(route.handler(req,res,done)).catch(done);}catch(error){done(error);}
  }
  next();
});
const adapter={httpServer:server,config:{root:state},middlewares:{use(path,handler){if(typeof path==='function'){handler=path;path='';}routes.push({path,handler});}},restart:async()=>{}};
for(const plugin of localProviderPlugins())if(!['gev-key-setup','openai-realtime-proxy','local-receivers-proxy'].includes(plugin.name))await plugin.configureServer?.(adapter);
await keySetupEndpoint({sourceRoot:state}).configureServer(adapter);
server.listen(Number(process.env.CRONOS_EYE_PORT),'127.0.0.1');
process.on('SIGTERM',()=>{server.close();setTimeout(()=>process.exit(0),500).unref();});
