"""Release proposals, asynchronous staging and browser-authorized transactions."""
import asyncio
import hashlib
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from cronos.update_transaction import prepare_archive, managed_files, write_json, read_json, regular

def file_hash(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()


REPOSITORY='Pedro-Prog-crypto/Cronos'
CHANNEL='feat/cronos-test-ui'


def github_headers():
    token=os.getenv('CRONOS_UPDATE_GITHUB_TOKEN') or os.getenv('GITHUB_TOKEN','')
    return {'Accept':'application/vnd.github+json',**({'Authorization':'Bearer '+token} if token else {})}


async def archive_url(client,revision):
    if 'Authorization' not in github_headers():return f'https://codeload.github.com/{REPOSITORY}/zip/{revision}'
    async with client.stream('GET',f'https://api.github.com/repos/{REPOSITORY}/zipball/{revision}',headers=github_headers()) as response:
        if response.status_code not in {301,302,303,307,308}:
            response.raise_for_status();raise ValueError('O repositório não forneceu o endereço oficial do pacote.')
        location=response.headers.get('location','');parsed=urlsplit(location)
        if parsed.scheme!='https' or parsed.hostname!='codeload.github.com' or parsed.username or parsed.password or not parsed.path.startswith('/'+REPOSITORY+'/'):
            raise ValueError('Redirecionamento do pacote fora da origem permitida.')
        return location



class UpdateService:
    def __init__(self, app, root=None):
        self.app=app
        self.root=regular(root or Path(__file__).resolve().parents[1])
        self.folder=regular(self.root/'.cronos-local/updater')
        self.folder.mkdir(parents=True,exist_ok=True)
        self.task=None
        self.busy=asyncio.Lock()
        self.suggestions=[]
        self.last_check=-60
        self._revision=None
        self.next_remote=0

    def revision(self):
        path=self.root/'cronos/revision.txt'
        value=path.read_text().strip() if path.exists() else ''
        if re.fullmatch('[0-9a-f]{40}',value):return value
        installed=read_json(self.folder/'installed.json',{})
        if installed.get('revision'):return installed['revision']
        if self._revision:return self._revision
        try:
            self._revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.root,stderr=subprocess.DEVNULL,text=True,timeout=3).strip()
            return self._revision
        except (OSError,subprocess.SubprocessError):return None

    def managed(self):
        heartbeat=read_json(self.folder/'heartbeat.json',{})
        return (os.getenv('CRONOS_SUPERVISED')=='1' and str(heartbeat.get('pid'))==os.getenv('CRONOS_SUPERVISOR_PID')
                and time.time()-heartbeat.get('at',0)<20)

    def report(self):
        release=read_json(self.folder/'release.json',{})
        state=read_json(self.folder/'status.json',{'phase':'idle','message':'Nenhuma atualização em andamento.','progress':0})
        dismissed=read_json(self.folder/'dismissed.json',{})
        hidden={key for key,stamp in dismissed.items() if time.time()-stamp<86400}
        if state.get('phase') in {'completed','restored','failed','recovery_failed'} and state.get('id') in hidden:
            state={'phase':'idle','message':'Nenhuma atualização em andamento.','progress':0}
        release={**release,'available':bool(release.get('revision') and release['revision']!=self.revision())}
        can_rollback=bool(state.get('id') and state.get('phase')=='completed' and (self.folder/'transactions'/state['id']/'backup/cronos').is_dir())
        return {'can_rollback':can_rollback,'dismissed':list(hidden),'state':state,'release':release,'installed_revision':self.revision(),
                'managed':self.managed(), 'suggestions':self.suggestions,
                'scope':'Pacotes do repositório e propostas de código explicitamente solicitadas. Instalação exige autorização e supervisor.'}

    async def check(self):
        if self.app.state.engine.settings.privacy_mode!='online':
            raise ValueError('Consulta de atualização desativada no modo local.')
        if time.monotonic()-self.last_check<60:
            return self.report()
        self.last_check=time.monotonic()
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
            result=await client.get(f'https://api.github.com/repos/{REPOSITORY}/commits/{CHANNEL}',headers=github_headers())
            result.raise_for_status()
            data=result.json()
        if not isinstance(data,dict):raise ValueError('Resposta inválida do repositório.')
        revision=data.get('sha','')
        if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('O repositório não retornou uma revisão válida.')
        write_json(self.folder/'release.json',{'revision':revision,'available':revision!=self.revision(),
                   'source':f'https://github.com/{REPOSITORY}/commit/{revision}',
                   'summary':str(data.get('commit',{}).get('message','')).split('\n')[0][:300], 'checked_at':time.time()})
        return self.report()

    async def prepare(self, revision):
        if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Revisão inválida.')
        if self.task and not self.task.done():raise ValueError('Já existe uma preparação em andamento.')
        current=self.report()['state']
        if current['phase'] in {'queued','installing','testing'}:raise ValueError('Aguarde a transação atual terminar.')
        if self.app.state.engine.settings.privacy_mode!='online':raise ValueError('Download desativado no modo local.')
        ident=uuid4().hex
        transaction=regular(self.folder/'transactions'/ident)
        transaction.mkdir(parents=True)
        write_json(self.folder/'status.json',{'phase':'downloading','message':'Baixando a revisão autorizada do repositório.','progress':10,'id':ident})
        async def work():
            try:
                archive=transaction/'release.zip';size=0
                async with httpx.AsyncClient(timeout=90,follow_redirects=False) as client:
                    url=await archive_url(client,revision)
                    async with client.stream('GET',url) as response:
                        response.raise_for_status()
                        with archive.open('wb') as output:
                            async for chunk in response.aiter_bytes():
                                size+=len(chunk)
                                if size>128*1024*1024:raise ValueError('Download excede 128 MB.')
                                output.write(chunk)
                write_json(self.folder/'status.json',{'phase':'validating','message':'Conferindo código e arquivos da interface, sem executar o pacote.','progress':30,'id':ident})
                candidate=await asyncio.to_thread(prepare_archive,archive,transaction/'candidate',self.root)
                baseline=await asyncio.to_thread(managed_files,self.root)
                changed=sum(baseline.get(p)!=h for p,h in candidate.items())+len(baseline.keys()-candidate.keys())
                write_json(transaction/'prepared.json',{'revision':revision,'previous_revision':self.revision(),'candidate':candidate,'baseline':baseline,
                           'archive_sha256':await asyncio.to_thread(file_hash,archive),'changed_files':changed})
                write_json(self.folder/'status.json',{'phase':'ready','message':f'Cópia preparada: {changed} arquivos alterados. Aguarda autorização para backup e instalação.','progress':45,'id':ident,'revision':revision,'changed_files':changed})
            except asyncio.CancelledError:
                write_json(self.folder/'status.json',{'phase':'failed','message':'Preparação interrompida; instalação atual preservada.','progress':0,'id':ident})
                raise
            except Exception:
                write_json(self.folder/'status.json',{'phase':'failed','message':'O pacote não passou na preparação. A versão em uso não foi alterada.','progress':0,'id':ident})
        self.task=asyncio.create_task(work())
        return {'id':ident,'status':'preparing','installed':False}

    async def install(self, ident):
        if not self.managed():raise ValueError('Abra pelo Iniciar-Cronos-Web.bat atualizado para habilitar recuperação independente.')
        if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Transação inválida.')
        async with self.busy:
            state=self.report()['state']
            if state['phase']!='ready' or state.get('id')!=ident:raise ValueError('Esta cópia não está pronta para instalar.')
            transaction=regular(self.folder/'transactions'/ident)
            prepared=read_json(transaction/'prepared.json',{})
            if prepared.get('origin')=='ai':
                reviewed=read_json(transaction/'reviewed.json',{})
                fingerprint=hashlib.sha256(__import__('json').dumps(prepared.get('candidate'),sort_keys=True).encode()).hexdigest()
                if reviewed.get('fingerprint')!=fingerprint or time.time()-reviewed.get('at',0)>1800:
                    raise ValueError('Abra Revisar alterações e examine a proposta gerada por IA antes de autorizar a instalação.')
            # Existing consistent SQLite/Markdown backup is mandatory before requesting downtime.
            backup=await asyncio.to_thread(self.app.state.panels.backup)
            try:
                write_json(self.folder/'transactions'/ident/'memory-backup.json',{'vault':str(self.app.state.memory.vault),'name':backup['name']})
                write_json(self.folder/'status.json',{'phase':'queued','message':'Backup da memória concluído. Aguardando o supervisor instalar.','progress':50,'id':ident,'memory_backup':backup['name']})
                write_json(self.folder/'install.request.json',{'id':ident})
                self.app.state.engine.updating=True
            except OSError:
                self.app.state.engine.updating=False
                write_json(self.folder/'status.json',{'phase':'failed','message':'Não foi possível solicitar a instalação. Versão atual preservada.','progress':0,'id':ident})
                raise
        return {'queued':True,'id':ident,'note':'Instalação solicitada, ainda não concluída. Acompanhe a barra e recarregue após a confirmação.'}

    async def prepare_rollback(self,ident):
        import shutil
        from cronos.update_transaction import inventory, validate_candidate
        if not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('Transação inválida.')
        if self.task and not self.task.done():raise ValueError('Há uma preparação em andamento.')
        if self.report()['state']['phase'] in {'queued','installing','testing'}:raise ValueError('Aguarde a instalação atual.')
        previous=regular(self.folder/'transactions'/ident)
        journal=read_json(previous/'journal.json',{})
        metadata=read_json(previous/'prepared.json',{})
        if journal.get('phase')!='completed' or not metadata:raise ValueError('Não há instalação concluída com backup nesta transação.')
        if await asyncio.to_thread(inventory,previous/'backup/cronos')!=metadata['baseline']:raise ValueError('O backup do código não passou na verificação.')
        new_id=uuid4().hex;transaction=regular(self.folder/'transactions'/new_id)
        await asyncio.to_thread(shutil.copytree,previous/'backup/cronos',transaction/'candidate/cronos')
        await asyncio.to_thread(validate_candidate,transaction/'candidate')
        baseline=await asyncio.to_thread(managed_files,self.root)
        write_json(transaction/'prepared.json',{'revision':metadata.get('previous_revision') or metadata['revision'],'previous_revision':self.revision(),
                   'candidate':metadata['baseline'],'baseline':baseline,'origin':'rollback','changed_files':len(baseline),
                   'summary':'Retorno ao código anterior. Um novo backup será criado antes da instalação.'})
        write_json(self.folder/'status.json',{'phase':'ready','message':'Retorno ao código anterior preparado. Autorize para criar novo backup e restaurar.','progress':45,'id':new_id,'origin':'rollback'})
        return {'id':new_id,'installed':False,'status':'ready'}

    async def discover_models(self):
        from cronos.integrations import available_models, provider_catalog
        from cronos.providers import ProviderError
        settings=self.app.state.engine.settings
        if settings.privacy_mode!='online':return
        cache=read_json(self.folder/'model-catalogs.json',{'checked_at':0,'providers':{},'advice':[]})
        if time.time()-cache.get('checked_at',0)<86400:return
        limit=asyncio.Semaphore(2)
        async def listing(provider):
            async with limit:
                try:return provider['id'],await asyncio.wait_for(available_models(settings,provider['id']),30)
                except (ProviderError,TimeoutError,OSError):return provider['id'],None
        entries=[p for p in provider_catalog(settings) if p['configured'] and p['kind']!='ollama']
        results=await asyncio.gather(*(listing(p) for p in entries))
        advice=[];known=cache.get('providers',{})
        for ident,models in results:
            if models is None:continue
            previous=known.get(ident)
            added=sorted(set(models)-set(previous)) if previous is not None else []
            known[ident]=models
            if added:
                advice.append({'id':'models-'+ident,'title':f'A API {ident} passou a anunciar {len(added)} modelos adicionais: '+', '.join(added[:3])+'. Posso comparar documentação, compatibilidade e custos antes de propor uma integração.',
                               'status':'proposed','note':'Diferença entre listagens da API, sem teste de geração e sem afirmação de gratuidade.'})
        write_json(self.folder/'model-catalogs.json',{'checked_at':time.time(),'providers':known,'advice':advice})

    async def maintain(self):
        while True:
            await asyncio.sleep(60)
            if not self.app.state.panels.preferences.proactive_suggestions:
                self.suggestions=[];continue
            if getattr(self.app.state.engine,'phase','idle')!='idle' or self.app.state.lock.locked():continue
            try:
                from cronos.evolution import checkup
                report=await asyncio.to_thread(checkup,self.app.state.engine.settings)
                self.suggestions=[{'id':hashlib.sha256(p['title'].encode()).hexdigest()[:12],**p} for p in report['proposals']]
                configured=[p for p in report['providers'] if p['configured'] and p['kind']!='ollama']
                if len(configured)<2:
                    self.suggestions.append({'id':'integration-resilience','title':'Podemos configurar uma segunda IA para comparar respostas ou atender conversas de texto quando a principal estiver indisponível.','status':'proposed','note':'Requer conta/chave e avaliação de custos; nenhuma integração foi adicionada.'})
                stats=await asyncio.to_thread(self.app.state.memory.stats)
                if stats.get('pending_exports',0):
                    self.suggestions.append({'id':'memory-exports','title':f"Há {stats['pending_exports']} exportações de memória pendentes. Posso ajudar a revisar a sincronização.",'status':'proposed','note':'Contagem real do banco local; nenhuma nota foi alterada.'})
                try:await self.discover_models()
                except (ValueError,OSError):pass
                model_advice=read_json(self.folder/'model-catalogs.json',{})
                if time.time()-model_advice.get('checked_at',0)<86400:self.suggestions.extend(model_advice.get('advice',[]))
                cached=read_json(self.folder/'release.json',{})
                if time.time()-cached.get('checked_at',0)>86400 and time.monotonic()>=self.next_remote:
                    self.next_remote=time.monotonic()+86400
                    try:await self.check()
                    except (ValueError,OSError,httpx.HTTPError):pass
            except (ValueError,OSError):pass


def install_updates(app,authenticate):
    service=UpdateService(app);app.state.updater=service
    class Revision(BaseModel):
        model_config=ConfigDict(extra='forbid')
        revision:str=Field(pattern='^[0-9a-f]{40}$')
    class Transaction(BaseModel):
        model_config=ConfigDict(extra='forbid')
        id:str=Field(pattern='^[0-9a-f]{32}$')
    class Dismissal(BaseModel):
        key:str=Field(min_length=1,max_length=100)
    auth=[Depends(authenticate)]
    @app.post('/updates/dismiss',dependencies=auth)
    async def dismiss(body:Dismissal):
        entries=read_json(service.folder/'dismissed.json',{})
        entries={k:v for k,v in entries.items() if time.time()-v<86400}
        entries[body.key]=time.time()
        write_json(service.folder/'dismissed.json',entries)
        return {'dismissed':body.key}

    @app.get('/updates',dependencies=auth)
    async def report():return await asyncio.to_thread(service.report)
    @app.get('/updates/health',dependencies=auth)
    async def health():
        try:
            app.state.memory.stats()
            html=(service.root/'cronos/ui/index.html').read_text(encoding='utf-8')
            return {'ready':bool(html and app.state.registry.tools and app.state.panels.preferences),'revision':service.revision()}
        except (OSError,ValueError):raise HTTPException(503,'Inicialização incompleta.') from None
    @app.post('/updates/check',dependencies=auth)
    async def check():
        try:return await service.check()
        except (ValueError,OSError,httpx.HTTPError):raise HTTPException(409,'Não foi possível consultar o repositório; nenhuma atualização aplicada.') from None
    @app.post('/updates/prepare',dependencies=auth)
    async def prepare(body:Revision):
        try:return await service.prepare(body.revision)
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
    @app.get('/updates/proposal/{ident}',dependencies=auth)
    async def proposal(ident:str):
        import difflib
        if not re.fullmatch('[0-9a-f]{32}',ident):raise HTTPException(422,'Proposta inválida.')
        transaction=regular(service.folder/'transactions'/ident)
        prepared=read_json(transaction/'prepared.json')
        if not prepared:raise HTTPException(404,'Cópia ainda não está pronta.')
        diffs=[]
        for path,digest in prepared['candidate'].items():
            if prepared['baseline'].get(path)==digest or not path.endswith('.py'):continue
            before=(service.root/'cronos'/path).read_text(encoding='utf-8') if (service.root/'cronos'/path).is_file() else ''
            after=(transaction/'candidate/cronos'/path).read_text(encoding='utf-8')
            diffs.append({'path':'cronos/'+path,'diff':''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='atual',tofile='proposta'))[:100000]})
        if prepared.get('origin')=='ai':
            fingerprint=hashlib.sha256(__import__('json').dumps(prepared.get('candidate'),sort_keys=True).encode()).hexdigest()
            write_json(transaction/'reviewed.json',{'at':time.time(),'fingerprint':fingerprint})
        return {'id':ident,'origin':prepared.get('origin','repository'),'summary':prepared.get('summary','Pacote do repositório'),
                'test_plan':prepared.get('test_plan','Verificação de inicialização pelo supervisor após autorização.'),
                'functional_tests_run':prepared.get('functional_tests_run',False),'diffs':diffs}

    @app.post('/updates/rollback',dependencies=auth)
    async def rollback(body:Transaction):
        try:return await service.prepare_rollback(body.id)
        except (ValueError,OSError) as exc:raise HTTPException(409,str(exc)) from None
    @app.post('/updates/install',dependencies=auth)
    async def install(body:Transaction):
        async with app.state.lock:
            try:return await service.install(body.id)
            except (ValueError,OSError) as exc:raise HTTPException(409,str(exc)) from None
