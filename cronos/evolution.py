"""Supervised, reversible integration configuration. Never executes downloaded code."""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from cronos.integrations import ProviderSpec, checked_url, specs, provider_catalog, available_models
from cronos.providers import ProviderError

_LOCK = threading.RLock()


class Routing(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fallbacks: list[str] = Field(default_factory=list)
    enabled: bool = False


def _path(settings):
    return settings.providers_file.with_name('evolution.json')


def read(settings):
    path = _path(settings)
    if not path.exists():
        return {'routing': Routing().model_dump(), 'previous': None, 'updated_at': None}
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
    return {'providers': catalog, 'routing': read(settings), 'last_client_timings_ms': timings,
            'proposals': proposals, 'scope': 'Leitura local, sem chamadas pagas, varredura em segundo plano ou alteração de voz/modelo.',
            'discovery': 'Use integrations_models para modelos anunciados pela API; novidades de outros provedores exigem pesquisa em fontes oficiais. Não há catálogo universal garantido.'}


class ResilientProvider:
    def __init__(self, settings, primary):
        self.settings, self.primary = settings, primary

    async def reply(self, system, messages):
        # Never replay raw mic audio to an incompatible API or silently change an explicit council request.
        from cronos.reply_stream import reply_sink, intro_sink
        delivered = False
        original_reply, original_intro = reply_sink.get(), intro_sink.get()
        async def observe_reply(value):
            nonlocal delivered
            delivered = True
            await original_reply(value)
        async def observe_intro(value):
            nonlocal delivered
            delivered = True
            await original_intro(value)
        reply_token = reply_sink.set(observe_reply) if original_reply else None
        intro_token = intro_sink.set(observe_intro) if original_intro else None
        try:
            try:
                return await self.primary.reply(system, messages)
            finally:
                if reply_token is not None: reply_sink.reset(reply_token)
                if intro_token is not None: intro_sink.reset(intro_token)
        except ProviderError as original:
            if delivered or any(m.get('audio_pcm') is not None or m.get('image') for m in messages):
                raise
            policy = Routing.model_validate(read(self.settings)['routing'])
            if not policy.enabled or not original.retryable:
                raise
            from dataclasses import replace
            from cronos.providers import make_provider
            usable = {p['id'] for p in provider_catalog(self.settings) if p['configured']}
            for provider_id in policy.fallbacks:
                if provider_id == self.settings.provider or provider_id not in usable:
                    continue
                try:
                    result = await make_provider(replace(self.settings, provider=provider_id)).reply(system, messages)
                    return {**result, 'provider_used': provider_id, 'fallback_used': True}
                except ProviderError:
                    continue
            raise original


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
