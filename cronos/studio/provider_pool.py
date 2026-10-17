"""Serial failover for a Studio job; preparing adapters never sends a request."""
import asyncio
import time

import httpx

from cronos.providers import ProviderError


class ProviderPool:
    def __init__(self, project, entries, factory, event, cooldowns, *, injected=None, timeout=240):
        self.project = project
        self.event = event
        self.cooldowns = cooldowns
        self.timeout = timeout
        self.adapters = {}
        self.index = 0
        self.failures = []
        chosen = project['provider']
        # Keep an explicitly supplied test/custom adapter isolated from real APIs.
        candidates = [{'id': chosen}] if injected is not None else [p for p in entries if p['configured'] and p.get('allowed', True)]
        candidates.sort(key=lambda p: (p['id'] != chosen, p.get('kind') == 'ollama'))
        self.ids = [p['id'] for p in candidates]
        project['provider_queue'] = self.ids
        project['provider_attempts'] = []
        project['active_provider'] = None
        for identifier in self.ids:
            if cooldowns.get(identifier, 0) > time.monotonic():
                self.failures.append((identifier, 'pausa após falha recente'))
                continue
            try:
                self.adapters[identifier] = injected if injected is not None else factory(identifier)
            except (ProviderError, ValueError, OSError):
                self.failures.append((identifier, 'configuração indisponível'))
        self.ids = [identifier for identifier in self.ids if identifier in self.adapters]

    def exhausted(self):
        details = '; '.join(identifier + ': ' + reason for identifier, reason in self.failures)
        raise ProviderError('Nenhuma integração disponível conseguiu concluir esta etapa. '
                            'Pedido, recursos e última versão preservados.' + (' ' + details if details else ''))

    @property
    def current(self):
        if self.index >= len(self.ids): self.exhausted()
        return self.ids[self.index]

    def reject(self, reason, *, cooldown=0):
        identifier = self.current
        self.failures.append((identifier, reason))
        if cooldown: self.cooldowns[identifier] = time.monotonic() + cooldown
        self.project['provider_attempts'].append({'id': identifier, 'status': 'unavailable', 'reason': reason, 'at': time.time()})
        self.index += 1
        self.project['active_provider'] = None
        if self.index < len(self.ids):
            self.event(self.project, 'fallback', identifier + ' não concluiu esta etapa. Continuando com ' + self.ids[self.index] + '; pedido e versão salva mantidos.')

    async def reply(self, system, messages, *, transform=None, allow_partial=False):
        while True:
            identifier = self.current
            self.project['active_provider'] = identifier
            self.event(self.project, 'provider', 'IA ativa: ' + identifier + '. As demais integrações configuradas permanecem de reserva, sem chamadas paralelas.')
            try:
                result = await self.receive(identifier,system,messages)
                if transform is not None: result = transform(result)
            except asyncio.CancelledError:
                raise  # Explicit cancellation never starts another provider.
            except (ProviderError, TimeoutError, httpx.HTTPError, OSError, ValueError) as exc:
                if allow_partial and getattr(exc,'kind',None) in {'output_limit','output_interrupted','format'} and (getattr(exc,'partial_output',None) or '').lstrip().startswith(('{','```json')):
                    self.project['provider_attempts'].append({'id':identifier,'status':'partial','reason':'parte recebida; continuação necessária','at':time.time()})
                    self.event(self.project,'checkpoint',identifier+' entregou parte do código. Preservando esse trecho para continuar sem reiniciar o projeto.')
                    return {'reply':exc.partial_output,'incomplete':True,'tool_calls':[],'topics':[]}
                # No raw server response, prompt or credential reaches the event log.
                quota = isinstance(exc, ProviderError) and exc.status == 429
                reason = 'limite de uso (HTTP 429)' if quota else {400:'requisição rejeitada (HTTP 400)',401:'chave rejeitada (HTTP 401)',403:'acesso negado (HTTP 403)',404:'modelo ou endereço indisponível (HTTP 404)',422:'parâmetros incompatíveis (HTTP 422)'}.get(getattr(exc,'http_status',None) or getattr(exc,'status',None),'sem resposta utilizável nesta tentativa')
                if getattr(exc,'kind',None)=='output_limit':reason='código interrompido pelo limite de saída do modelo'
                elif getattr(exc,'kind',None)=='format':reason='resposta incompleta ou formato JSON inválido'
                elif isinstance(exc,(TimeoutError,httpx.TimeoutException)):reason='tempo de resposta esgotado'
                self.reject(reason, cooldown=0 if isinstance(exc, ValueError) else 60)
                await asyncio.sleep(0)
                continue
            self.cooldowns.pop(identifier, None)
            self.project['provider_attempts'].append({'id': identifier, 'status': 'responded', 'at': time.time()})
            return result

    async def receive(self,identifier,system,messages):
        from cronos.structured_stream import progress_sink,checkpoint_sink
        started=time.monotonic();last_event=started;last_size=0;last_raw=''
        async def progress(size,prefix=None):
            nonlocal last_event,last_size,last_raw
            now=time.monotonic()
            if not last_size or now-last_event>=8 or size-last_size>=8192:
                self.event(self.project,'receiving',f'{identifier}: recebendo a entrega, {size:,} caracteres nesta parte.'.replace(',','.'))
                if prefix:
                    last_raw=prefix()
                    save=checkpoint_sink.get()
                    if save:await save(last_raw)
                last_event=now;last_size=size
        token=progress_sink.set(progress)
        task=asyncio.create_task(getattr(self.adapters[identifier],'reply_structured',self.adapters[identifier].reply)(system,messages))
        try:
            while True:
                remaining=self.timeout-(time.monotonic()-started)
                if remaining<=0:raise TimeoutError()
                done,_=await asyncio.wait({task},timeout=min(15,remaining))
                if task in done:return task.result()
                if time.monotonic()-last_event>=15:
                    self.event(self.project,'waiting',identifier+': aguardando a integração, '+str(int(time.monotonic()-started))+' segundos nesta parte. A tarefa continua ativa.')
                    last_event=time.monotonic()
        except TimeoutError:
            if last_raw:raise ProviderError('A integração excedeu o tempo desta parte. O trecho recebido pode ser continuado.',504,kind='output_interrupted',partial_output=last_raw) from None
            raise
        finally:
            progress_sink.reset(token)
            if not task.done():task.cancel()
            await asyncio.gather(task,return_exceptions=True)
