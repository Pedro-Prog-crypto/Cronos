"""Supervised, reversible integration configuration. Never executes downloaded code."""
import json
import threading
import time
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from pydantic import BaseModel, ConfigDict, Field
from cronos.integrations import ProviderSpec, checked_url, specs, provider_catalog, available_models
from cronos.providers import ProviderError

_LOCK = threading.RLock()

# Bound silence before the first useful sentence, then allow the configured
# generation budget to finish a detailed answer. Five seconds is a UI target,
# not a deadline that truncates an active explanation.
FIRST_REPLY_TIMEOUT_SECONDS = 8
FIRST_OUTPUT_TIMEOUT_SECONDS = 30
FALLBACK_ATTEMPT_TIMEOUT_SECONDS = 45
FALLBACK_TOTAL_TIMEOUT_SECONDS = 300


class Routing(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fallbacks: list[str] = Field(default_factory=list)
    enabled: bool = False


def _path(settings):
    return settings.providers_file.with_name('evolution.json')


def read(settings):
    path = _path(settings)
    if not path.exists():
        # On a fresh install, use configured alternatives automatically after
        # a retryable failure. An existing evolution.json remains authoritative.
        alternatives = [provider_id for provider_id in explanation_providers(settings)
                        if provider_id != settings.provider]
        return {'routing': Routing(fallbacks=alternatives, enabled=bool(alternatives)).model_dump(),
                'previous': None, 'updated_at': None}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        data['routing'] = Routing.model_validate(data['routing']).model_dump()
        return data
    except (OSError, ValueError, KeyError, TypeError):
        raise ProviderError('Configuração de evolução inválida; nenhuma troca automática foi realizada.') from None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def routing(settings, policy):
    with _LOCK:
        ids = {p['id'] for p in provider_catalog(settings) if p['configured']}
        policy = Routing.model_validate(policy)
        policy.fallbacks = list(dict.fromkeys(policy.fallbacks))
        if any(p not in ids for p in policy.fallbacks):
            raise ValueError('Escolha somente provedores registrados, com credencial configurada e permitidos no modo atual.')
        old = read(settings)
        _write(_path(settings), {'routing': policy.model_dump(), 'previous': old['routing'],
                                'updated_at': datetime.now(timezone.utc).isoformat()})
        return {'saved': True, 'routing': policy.model_dump(), 'scope': 'Conversas de texto. Áudio Live e consultas a uma IA específica não trocam de provedor.'}


def rollback(settings):
    with _LOCK:
        old = read(settings)
        if old.get('previous') is None:
            raise ValueError('Não há configuração anterior para restaurar.')
        return routing(settings, old['previous'])


async def register(settings, spec):
    """Validate a real model listing before saving; never tests by generating text."""
    from dataclasses import replace
    import tempfile
    spec = ProviderSpec.model_validate(spec)
    if spec.id in {'gemini', 'ollama'}:
        raise ValueError('Use um ID diferente dos provedores principais.')
    if spec.kind != 'gemini':
        checked_url(spec.base_url)
    # Separate temporary manifest: no half-installed entry exposed to conversations.
    settings.providers_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=settings.providers_file.parent) as folder:
        path = Path(folder) / 'providers.json'
        _write(path, {'providers': [spec.model_dump()]})
        models = await available_models(replace(settings, providers_file=path), spec.id)
        if spec.model not in models:
            raise ValueError('O modelo não apareceu na listagem da API; integração não registrada.')
    with _LOCK:
        entries = specs(settings)
        if any(p.id == spec.id for p in entries):
            raise ValueError('Esse identificador já existe; nenhuma integração foi sobrescrita.')
        _write(settings.providers_file, {'providers': [p.model_dump() for p in entries] + [spec.model_dump()]})
    return {'registered': spec.id, 'model_listed': True, 'generation_tested': False,
            'note': 'Listagem não comprova cota gratuita, síntese de voz ou geração. Provedor principal preservado.'}


def checkup(settings):
    from cronos import conversation_metrics
    catalog = provider_catalog(settings)
    timings = conversation_metrics.read_client()
    proposals = []
    for field, title in [('recognition_ms', 'Revisar reconhecimento de fala'),
                         ('chat_ms', 'Revisar geração e chamadas de ferramentas'),
                         ('speech_request_ms', 'Revisar preparação da voz')]:
        value = timings.get(field)
        if isinstance(value, (int, float)) and value > 3000:
            proposals.append({'title': title, 'evidence_ms': value, 'status': 'proposed',
                              'note': 'Medição do último turno; não comprova a causa e não altera código.'})
    return {'providers': catalog, 'primary_provider': settings.provider,
            'routing': read(settings), 'last_client_timings_ms': timings,
            'proposals': proposals, 'scope': 'Leitura local, sem chamadas pagas, varredura em segundo plano ou alteração de voz/modelo.',
            'discovery': 'Use integrations_models para modelos anunciados pela API; novidades de outros provedores exigem pesquisa em fontes oficiais. Não há catálogo universal garantido.'}


@lru_cache(maxsize=64)
def _ollama_model_ready(url: str, model: str, interval: int) -> bool:
    """A local endpoint and the selected model must both exist before auto-routing."""
    del interval
    try:
        base = checked_url(url)
        parsed = urlsplit(base)
        if parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
            return False
        response = httpx.get(base.rstrip('/') + '/api/tags', timeout=.5, trust_env=False)
        response.raise_for_status()
        names = {str(item.get('name', '')).casefold() for item in response.json().get('models', [])
                 if isinstance(item, dict)}
        target = model.casefold()
        return target in names or ':' not in target and target + ':latest' in names
    except (ProviderError, httpx.HTTPError, ValueError, TypeError, AttributeError):
        return False


def ollama_ready(settings) -> bool:
    return _ollama_model_ready(settings.ollama_url, settings.ollama_model, int(time.monotonic() // 15))


def explanation_providers(settings):
    """Rotate real configured text providers; keep local Ollama as the last option.

    One model answers each successful turn. Calling every paid API for every
    sentence would multiply both latency and usage without improving the voice.
    """
    available = [item for item in provider_catalog(settings)
                 if item['configured'] and (item['id'] != 'ollama' or ollama_ready(settings))]
    return [item['id'] for item in available if item['id'] not in {'gemini', 'ollama'}] + [
        item['id'] for item in available if item['id'] in {'gemini', 'ollama'}
    ]


class ResilientProvider:
    def __init__(self, settings, primary, *, all_configured=False):
        self.settings, self.primary = settings, primary
        self.all_configured = all_configured

    async def reply(self, system, messages):
        """Hedge a slow request without destroying a still usable answer.

        Only generation is raced. Engine executes tools after the winning result;
        no losing result can speak, write memory or execute its proposed tools.
        """
        import asyncio
        from dataclasses import replace
        from cronos.reply_stream import reply_sink, intro_sink
        from cronos.conversation_transport import conversation_provider
        from cronos.delivery import mark
        original_reply, original_intro = reply_sink.get(), intro_sink.get()
        tasks = {}; winner = None; errors = []; policy_loaded = False; attempted = []
        reserves = []; next_start = 0.; reserve_deadline = None
        # All registered conversation adapters encode the shared image format.
        # Raw Live microphone audio still cannot be replayed to text-only APIs.
        raw_input = any(m.get('audio_pcm') is not None for m in messages)
        loop = asyncio.get_running_loop()
        progress = asyncio.Event()

        async def receive(provider, provider_id, timeout):
            route_task = asyncio.current_task()
            async with asyncio.timeout(min(timeout, FIRST_OUTPUT_TIMEOUT_SECONDS)) as first_output:
                published = False
                async def publish(value, sink):
                    nonlocal winner, published
                    # Only silence has the short deadline. Once the model starts
                    # a real answer, allow its configured generation budget.
                    if not published:
                        published = True
                        first_output.reschedule(loop.time() + timeout)
                    task = route_task
                    if winner is None:
                        winner = task
                        for other in tasks:
                            if other is not task and not other.done(): other.cancel()
                        progress.set()
                    if winner is task and sink is not None: await sink(value)
                async def on_reply(value): await publish(value, original_reply)
                async def on_intro(value): await publish(value, original_intro)
                a = reply_sink.set(on_reply); b = intro_sink.set(on_intro)
                try:
                    mark('answer_route_requested', provider=provider_id)
                    return await provider.reply(system, messages)
                finally:
                    reply_sink.reset(a); intro_sink.reset(b)

        def start(provider, provider_id, timeout):
            attempted.append(provider_id)
            task = asyncio.create_task(receive(provider, provider_id, timeout))
            tasks[task] = provider_id
            return task

        def load_reserves():
            nonlocal policy_loaded, reserves, reserve_deadline
            if policy_loaded: return
            policy_loaded = True
            if raw_input: return
            if self.all_configured:
                reserves = [provider_id for provider_id in explanation_providers(self.settings)
                            if provider_id != self.settings.provider]
                reserve_deadline = loop.time() + FALLBACK_TOTAL_TIMEOUT_SECONDS
                return
            try: policy = Routing.model_validate(read(self.settings)['routing'])
            except (ProviderError,ValueError):
                # Broken legacy routing cannot erase a working primary answer.
                mark('answer_route_failed',provider='routing',error_type='configuration')
                return
            if policy.enabled:
                usable = set(explanation_providers(self.settings))
                reserves = list(dict.fromkeys(p for p in policy.fallbacks if p != self.settings.provider and p in usable))
            reserve_deadline = loop.time() + FALLBACK_TOTAL_TIMEOUT_SECONDS

        start(self.primary, self.settings.provider, float(self.settings.provider_timeout))
        next_start = loop.time() + FIRST_REPLY_TIMEOUT_SECONDS
        try:
            while tasks:
                if winner is None and loop.time() >= next_start:
                    load_reserves()
                    if reserves and len(tasks) < 2 and loop.time() < reserve_deadline:
                        provider_id = reserves.pop(0)
                        timeout = min(FALLBACK_ATTEMPT_TIMEOUT_SECONDS, reserve_deadline - loop.time())
                        if provider_id == 'ollama': timeout = min(timeout, 8)
                        try: provider = conversation_provider(replace(self.settings, provider=provider_id,
                                             gemini_transport='rest' if self.all_configured and provider_id=='gemini' else self.settings.gemini_transport))
                        except ProviderError as exc: errors.append(exc); next_start = loop.time(); continue
                        start(provider, provider_id, timeout)
                        next_start = loop.time() + FIRST_REPLY_TIMEOUT_SECONDS
                # No busy loop when both slots are occupied or reserves exhausted.
                timeout = max(0., next_start-loop.time()) if winner is None and (not policy_loaded or reserves and len(tasks)<2 and loop.time()<reserve_deadline) else None
                notification = asyncio.create_task(progress.wait())
                try:
                    done, _ = await asyncio.wait([*tasks, notification], timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    notification.cancel()
                    await asyncio.gather(notification, return_exceptions=True)
                progress.clear()
                for task in list(tasks):
                    if task not in done: continue
                    provider_id = tasks.pop(task)
                    try:
                        result = task.result()
                    except asyncio.CancelledError:
                        if winner is task: raise
                        continue
                    except (ProviderError, asyncio.TimeoutError) as exc:
                        error = exc if isinstance(exc, ProviderError) else ProviderError('A integração demorou demais e atingiu seu limite de geração.', 504)
                        mark('answer_route_failed', provider=provider_id, http_status=error.http_status or error.status)
                        if winner is task: raise error
                        if provider_id == self.settings.provider and not error.retryable and not self.all_configured: raise error
                        errors.append(error); load_reserves(); next_start = loop.time()
                        continue
                    except Exception as exc:
                        # SDKs sometimes raise an unclassified runtime error.
                        # Preserve the type in diagnostics, never the private
                        # provider body, and let an unused reserve answer.
                        mark('answer_route_failed', provider=provider_id,
                             error_type=type(exc).__name__, http_status=502)
                        error = ProviderError('A integração falhou antes de concluir a resposta; tentando outra opção configurada.', 502)
                        if winner is task: raise error from None
                        errors.append(error); load_reserves(); next_start = loop.time()
                        continue
                    if winner is not None and winner is not task: continue
                    if (not isinstance(result, dict) or not isinstance(result.get('reply'), str)
                            or not result['reply'].strip() and not result.get('tool_calls')):
                        error = ProviderError('A integração retornou uma resposta inválida.', 502)
                        mark('answer_route_failed', provider=provider_id, error_type='invalid_reply', http_status=502)
                        if winner is task: raise error
                        errors.append(error); load_reserves(); next_start = loop.time()
                        continue
                    # Providers validate their result before returning. One result
                    # leaves this layer; tools and persistence stay with Engine.
                    return {**result, 'provider_used':provider_id,
                            'fallback_used':provider_id != self.settings.provider,
                            'provider_calls':len(attempted), 'routes_attempted':attempted.copy()}
                while not tasks and reserves and winner is None and loop.time() < reserve_deadline:
                    provider_id = reserves.pop(0)
                    timeout = min(FALLBACK_ATTEMPT_TIMEOUT_SECONDS, reserve_deadline-loop.time())
                    if provider_id == 'ollama': timeout=min(timeout,8)
                    try: provider = conversation_provider(replace(self.settings, provider=provider_id,
                                         gemini_transport='rest' if self.all_configured and provider_id=='gemini' else self.settings.gemini_transport))
                    except ProviderError as exc: errors.append(exc); continue
                    start(provider, provider_id, timeout)
                    next_start = loop.time() + FIRST_REPLY_TIMEOUT_SECONDS
            if errors: raise errors[-1]
            raise ProviderError('Nenhuma integração configurada concluiu a resposta.', 503)
        finally:
            for task in tasks:
                if not task.done(): task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


def install_api(app, authenticate):
    from fastapi import Depends, HTTPException
    from pydantic import SecretStr

    class Credential(BaseModel):
        provider_id: str
        key: SecretStr

    # SecretStr is resolved by FastAPI from the module namespace for postponed inspection.
    @app.get('/evolution', dependencies=[Depends(authenticate)])
    async def report():
        try:
            return checkup(app.state.engine.settings)
        except ProviderError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post('/evolution/credential', dependencies=[Depends(authenticate)])
    async def credential(body: Credential):
        import os
        from dotenv import set_key
        settings = app.state.engine.settings
        spec = next((p for p in specs(settings) if p.id == body.provider_id), None)
        if spec is None or not spec.key_env or spec.key_env.upper() in {'GEMINI_API_KEY', 'FISH_API_KEY', 'FISH_REFERENCE_ID', 'FISH_MODEL'}:
            raise HTTPException(422, 'Escolha uma integração registrada que utilize variável de chave.')
        value = body.key.get_secret_value().strip()
        if not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
            raise HTTPException(422, 'Chave inválida; nenhuma alteração realizada.')
        async with app.state.lock:
            try:
                path = Path('.env')
                if path.is_symlink():
                    raise OSError()
                # Keys go only into the existing local credential store, never into model context.
                with _LOCK:
                    if not path.exists():
                        path.touch(mode=0o600)
                    if os.name != 'nt':
                        path.chmod(0o600)
                    set_key(str(path), spec.key_env, value)
                    os.environ[spec.key_env] = value
            except OSError:
                raise HTTPException(409, 'Não foi possível salvar a credencial local.') from None
        return {'configured': spec.id, 'generation_tested': False}
