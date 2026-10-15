"""On-demand host for the original God's Eye data providers. No shell console."""
import asyncio,hashlib,os,platform,secrets,shutil,socket,subprocess,time,zipfile
from pathlib import Path
import httpx
from fastapi import Depends,HTTPException,Request
from fastapi.responses import FileResponse,StreamingResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
ROOT=Path(__file__).resolve().parent.parent
STATE=ROOT/'.cronos-local'/'eye'
VERSION='24.14.0'


def node_executable():
    candidate=shutil.which('node')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    if candidate:
        try:
            version=subprocess.check_output([candidate,'--version'],creationflags=flags,timeout=5).decode().strip()
            if int(version.lstrip('v').split('.')[0])>=24:return candidate
        except (OSError,ValueError,subprocess.SubprocessError):pass
    if os.name!='nt':raise RuntimeError('Node.js 24 ou superior é necessário para os serviços do Olho de Deus.')
    arch='arm64' if platform.machine().lower() in {'arm64','aarch64'} else 'x64'
    name=f'node-v{VERSION}-win-{arch}';target=STATE/'runtime'/name/'node.exe'
    if target.is_file():return str(target)
    STATE.mkdir(parents=True,exist_ok=True);archive=STATE/(name+'.zip');base=f'https://nodejs.org/dist/v{VERSION}/'
    try:
        with httpx.Client(timeout=60,follow_redirects=False) as client:
            sums=client.get(base+'SHASUMS256.txt');sums.raise_for_status()
            expected=next(line.split()[0] for line in sums.text.splitlines() if line.split()[-1]==name+'.zip')
            digest=hashlib.sha256()
            with client.stream('GET',base+name+'.zip') as response:
                response.raise_for_status();size=0
                with archive.open('wb') as output:
                    for chunk in response.iter_bytes():
                        size+=len(chunk)
                        if size>80*1024*1024:raise ValueError('Runtime acima do limite esperado')
                        digest.update(chunk);output.write(chunk)
            if digest.hexdigest()!=expected:raise ValueError('Checksum inválido do runtime Node')
        destination=STATE/'runtime';destination.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as package:
            for entry in package.infolist():
                path=(destination/entry.filename).resolve()
                if not path.is_relative_to(destination.resolve()):raise ValueError('Caminho inválido no runtime')
            package.extractall(destination)
        return str(target)
    finally:archive.unlink(missing_ok=True)


class EyeRuntime:
    def __init__(self):
        self.process=None;self.port=None;self.secret=secrets.token_urlsafe(32);self.cookie=secrets.token_urlsafe(32)
        self.lock=asyncio.Lock();self.generation=0;self.last_used=0
    async def start(self):
        self.last_used=time.monotonic()
        async with self.lock:
            if self.process is not None and self.process.poll() is None:return
            generation=self.generation
            try:node=await asyncio.to_thread(node_executable)
            except Exception:raise HTTPException(503,'Não foi possível preparar Node.js 24 para os dados do Olho de Deus. Execute a instalação ou confira a conexão.') from None
            if generation!=self.generation:raise HTTPException(409,'Olho de Deus fechado durante a preparação.')
            STATE.mkdir(parents=True,exist_ok=True)
            config=ROOT/'cronos/eye-server/config'
            if config.is_dir():
                for source in config.iterdir():
                    destination=STATE/'config'/source.name
                    if source.is_file() and not destination.exists():
                        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
            names={'PATH','SystemRoot','SYSTEMROOT','WINDIR','TEMP','TMP','SSL_CERT_FILE','NODE_EXTRA_CA_CERTS','HTTPS_PROXY','HTTP_PROXY','NO_PROXY'}
            env={key:value for key,value in os.environ.items() if key in names}
            env.update(CRONOS_EYE_PORT=str(self.port),CRONOS_EYE_SECRET=self.secret,CRONOS_EYE_STATE=str(STATE),NODE_USE_ENV_PROXY='1')
            self.process=subprocess.Popen([node,str(ROOT/'cronos/eye-server/cronos-service.mjs')],cwd=STATE,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            async with httpx.AsyncClient(timeout=1,trust_env=False) as client:
                for _ in range(100):
                    if self.process.poll() is not None:break
                    try:
                        if (await client.get(self.url+'/health',headers=self.headers)).status_code==200:return
                    except httpx.HTTPError:pass
                    await asyncio.sleep(.05)
            await self._stop();raise HTTPException(503,'O serviço de dados do Olho de Deus não iniciou. Confira os arquivos da atualização.')
    @property
    def url(self):return f'http://127.0.0.1:{self.port}'
    @property
    def headers(self):return {'X-Cronos-Eye-Secret':self.secret}
    async def _stop(self):
        process=self.process;self.process=None
        if process is not None and process.poll() is None:
            process.terminate()
            try:await asyncio.to_thread(process.wait,2)
            except subprocess.TimeoutExpired:process.kill();await asyncio.to_thread(process.wait,2)
    async def close(self):
        self.generation+=1;self.cookie=secrets.token_urlsafe(32)
        async with self.lock:await self._stop()
    async def maintain(self):
        while True:
            await asyncio.sleep(10)
            if self.process is not None and time.monotonic()-self.last_used>45:await self.close()


def install_eye(app,authenticate):
    app.state.eye=EyeRuntime()
    folder=ROOT/'cronos/eye-ui'
    app.mount('/eye',StaticFiles(directory=folder,check_dir=False),name='eye-assets')
    for name in ('models','events'):
        app.mount('/'+name,StaticFiles(directory=folder/name,check_dir=False),name='eye-'+name)
    @app.post('/world/eye/heartbeat',dependencies=[Depends(authenticate)])
    async def heartbeat():
        if app.state.engine.settings.privacy_mode!='online':raise HTTPException(403,'Modo local: Olho de Deus desativado.')
        app.state.eye.last_used=time.monotonic()
        response=JSONResponse({'active':True})
        response.set_cookie('cronos_eye_session',app.state.eye.cookie,path='/api',httponly=True,samesite='strict',max_age=180)
        return response
    @app.post('/world/close',dependencies=[Depends(authenticate)])
    async def close():
        await app.state.eye.close();return {'closed':True}
    async def eye_auth(request:Request):
        ticket=request.cookies.get('cronos_eye_session','')
        if ticket and secrets.compare_digest(ticket.encode(),app.state.eye.cookie.encode()):return
        await authenticate(request.headers.get('authorization'))
    @app.api_route('/api/{path:path}',methods=['GET','POST','PUT','DELETE','PATCH'],dependencies=[Depends(eye_auth)])
    async def proxy(path:str,request:Request):
        if request.app.state.engine.settings.privacy_mode!='online':raise HTTPException(403,'Modo local: fontes externas do Olho de Deus desativadas.')
        if '..' in path.split('/') or '\\' in path:raise HTTPException(400,'Caminho inválido.')
        runtime=app.state.eye;await runtime.start()
        headers={**runtime.headers}
        for name in ('content-type','range','accept','if-none-match'):
            if name in request.headers:headers[name]=request.headers[name]
        if request.headers.get('origin'):headers['Origin']=runtime.url
        client=httpx.AsyncClient(timeout=35,trust_env=False)
        try:
            upstream=await client.send(client.build_request(request.method,runtime.url+'/api/'+path,params=request.query_params,headers=headers,content=await request.body()),stream=True)
        except httpx.HTTPError:
            await client.aclose();raise HTTPException(502,'A fonte de dados do Olho de Deus não respondeu.') from None
        async def chunks():
            try:
                async for chunk in upstream.aiter_bytes():yield chunk
            finally:await upstream.aclose();await client.aclose()
        kept={key:value for key,value in upstream.headers.items() if key.lower() in {'content-type','cache-control','etag','content-range','accept-ranges'}}
        return StreamingResponse(chunks(),status_code=upstream.status_code,headers=kept)
