"""Failover exercises real Studio jobs with deterministic, non-billable adapters."""
import asyncio
import base64
import io
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cronos.app import create_app
from cronos.providers import ProviderError, Ollama
from cronos.integrations import CompatibleProvider, ProviderSpec
from cronos.studio.provider_pool import ProviderPool
from test_backend import settings, AUTH
from test_studio import Builder, new, generate, get
from test_studio_visuals import VisualBuilder, wait


def pool_for(adapters, *, cooldowns=None, timeout=1):
    project = {'provider': next(iter(adapters))}
    events = []
    pool = ProviderPool(project, [{'id': key, 'configured': True} for key in adapters],
                        adapters.__getitem__, lambda p, phase, text: events.append((phase, text)),
                        cooldowns if cooldowns is not None else {}, timeout=timeout)
    return pool, project, events


class Failing:
    def __init__(self, error=None): self.calls = []; self.error = error or ProviderError('private response must not be logged', 503)
    async def reply(self, system, messages):
        self.calls.append((system, messages))
        raise self.error


@pytest.mark.parametrize('error', [ProviderError('quota', 429), ProviderError('service', 503),
                                    ProviderError('bad JSON'), httpx.ConnectError('connection'), TimeoutError()])
def test_failed_provider_yields_without_retry_or_publishing_error(error):
    first, second = Failing(error), VisualBuilder()
    pool, project, events = pool_for({'gemini': first, 'mistral': second})
    assert not first.calls and not second.calls  # Preparing adapters consumes no quota.
    result = asyncio.run(pool.reply('EXATAMENTE três direções', [{'role': 'user', 'content': 'same request'}]))
    assert result['reply'] and len(first.calls) == len(second.calls) == 1
    assert first.calls[0] == second.calls[0]
    assert project['active_provider'] == 'mistral' and project['provider'] == 'gemini'
    assert any(phase == 'fallback' for phase, _ in events)
    assert all(phase != 'failed' for phase, _ in events)
    assert 'private response' not in str(events)


def test_all_registered_alternatives_are_attempted_serially_without_fixed_cap():
    adapters = {f'provider-{i}': Failing() for i in range(35)}
    adapters['last'] = VisualBuilder()
    pool, project, _ = pool_for(adapters)
    async def run():
        return await pool.reply('EXATAMENTE três direções', [{'role': 'user', 'content': 'brief'}])
    asyncio.run(run())
    assert project['active_provider'] == 'last'
    assert all(len(adapter.calls) == 1 for adapter in adapters.values())
    assert len(project['provider_queue']) == 36


def test_cancelling_an_inflight_call_does_not_launch_a_reserve():
    class Waiting:
        async def reply(self, *args): await asyncio.Event().wait()
    backup = VisualBuilder()
    pool, _, _ = pool_for({'gemini': Waiting(), 'mistral': backup})
    async def run():
        task = asyncio.create_task(pool.reply('system', []))
        await asyncio.sleep(.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(run())
    assert not backup.calls


def test_timeout_advances_to_next_provider_without_waiting_for_quota():
    class Waiting:
        async def reply(self, *args): await asyncio.Event().wait()
    backup = VisualBuilder()
    pool, project, _ = pool_for({'gemini': Waiting(), 'mistral': backup}, timeout=.01)
    asyncio.run(pool.reply('EXATAMENTE três direções', []))
    assert project['active_provider'] == 'mistral' and len(backup.calls) == 1


def test_recent_service_failure_is_skipped_and_retried_after_pause(monkeypatch):
    clock = [100]
    monkeypatch.setattr('cronos.studio.provider_pool.time.monotonic', lambda: clock[0])
    first, backup = Failing(), VisualBuilder()
    cooldowns = {}
    pool, _, _ = pool_for({'gemini': first, 'mistral': backup}, cooldowns=cooldowns)
    asyncio.run(pool.reply('EXATAMENTE três direções', []))
    assert cooldowns['gemini'] == 160
    pool, _, _ = pool_for({'gemini': first, 'mistral': backup}, cooldowns=cooldowns)
    asyncio.run(pool.reply('EXATAMENTE três direções', []))
    assert len(first.calls) == 1
    clock[0] = 161
    pool, _, _ = pool_for({'gemini': first, 'mistral': backup}, cooldowns=cooldowns)
    asyncio.run(pool.reply('EXATAMENTE três direções', []))
    assert len(first.calls) == 2


def configured(settings, monkeypatch, adapters):
    settings = replace(settings, gemini_key='fixture-not-a-key', providers_file=settings.vault.parent / 'providers.json')
    settings.providers_file.write_text(json.dumps({'providers': [
        {'id': name, 'kind': 'openai', 'model': 'fixture', 'base_url': 'https://example.com/v1', 'key_env': 'STUDIO_FALLBACK_KEY'}
        for name in adapters if name not in {'gemini', 'ollama'}]}))
    monkeypatch.setenv('STUDIO_FALLBACK_KEY', 'fixture-not-a-key')
    monkeypatch.setattr('cronos.studio.service.make_provider', lambda s: adapters[s.provider])
    return settings


def test_site_job_recovers_from_429_and_503_and_preserves_context_and_credentials(settings, monkeypatch):
    adapters = {'gemini': Failing(ProviderError('quota', 429)), 'mistral': Failing(), 'groq': Builder(), 'ollama': Failing()}
    settings = configured(settings, monkeypatch, adapters)
    before = settings.providers_file.read_bytes(), settings.personality.read_bytes()
    with TestClient(create_app(settings)) as client:
        p = new(client)
        done = generate(client, p, prompt='Crie uma versão exclusiva para este hotel.')
        assert done['status'] == 'ready' and done['revision'] == 1
        assert done['provider'] == 'gemini' and done['active_provider'] == 'groq'
        assert not done.get('error') and not any(e['phase'] == 'failed' for e in done['events'])
        assert [x['id'] for x in done['provider_attempts']] == ['gemini', 'mistral', 'groq']
        assert adapters['gemini'].calls[0] == adapters['mistral'].calls[0] == adapters['groq'].calls[0]
        assert not adapters['ollama'].calls
        assert done['last_request'] == 'Crie uma versão exclusiva para este hotel.'
        assert client.app.state.engine.settings.provider == 'gemini'
        assert client.app.state.engine.settings.provider_timeout == settings.provider_timeout
    assert before == (settings.providers_file.read_bytes(), settings.personality.read_bytes())


def test_bad_proposals_also_yield_and_keep_the_original_request(settings, monkeypatch):
    first = Builder([{'reply': '{"directions":[]}'}])
    adapters = {'gemini': first, 'mistral': VisualBuilder(), 'ollama': Failing()}
    settings = configured(settings, monkeypatch, adapters)
    with TestClient(create_app(settings)) as client:
        p = new(client)
        body = {'mode': 'autonomous', 'prompt': 'Proponha três composições para o hotel.'}
        assert client.post('/studio/projects/' + p['id'] + '/directions', headers=AUTH, json=body).status_code == 200
        done = wait(client, p)
        assert done['status'] == 'ideas_ready' and done['revision'] == 0
        assert len(done['directions']) == 3 and done['active_provider'] == 'mistral'
        assert done['last_request'] == body['prompt'] and len(first.calls) == 1


def test_invalid_code_gets_one_repair_then_yields_to_valid_reserve(settings, monkeypatch):
    first = Builder([{'reply': 'not a complete site'}])
    adapters = {'gemini': first, 'mistral': Builder(), 'ollama': Failing()}
    settings = configured(settings, monkeypatch, adapters)
    with TestClient(create_app(settings)) as client:
        p = new(client)
        done = generate(client, p)
        assert done['status'] == 'ready' and done['active_provider'] == 'mistral'
        assert len(first.calls) == 2 and len(adapters['mistral'].calls) == 1
        assert adapters['mistral'].calls[0] == first.calls[0]
        assert len(done['history']) == 2


def test_failure_during_repair_uses_next_provider_without_repeating_failed_one(settings, monkeypatch):
    first = Builder([{'reply': 'bad site'}, ProviderError('limit', 429)])
    adapters = {'gemini': first, 'mistral': Builder(), 'ollama': Failing()}
    settings = configured(settings, monkeypatch, adapters)
    with TestClient(create_app(settings)) as client:
        done = generate(client, new(client))
        assert done['status'] == 'ready' and done['active_provider'] == 'mistral'
        assert len(first.calls) == 2 and len(adapters['mistral'].calls) == 1
        assert 'validation_error' in json.loads(adapters['mistral'].calls[0][1][-1]['content'])


def test_all_failed_preserves_preexisting_revision_and_reports_one_final_failure(settings, monkeypatch):
    adapters = {'gemini': Builder(), 'mistral': Failing(), 'ollama': Failing()}
    settings = configured(settings, monkeypatch, adapters)
    with TestClient(create_app(settings)) as client:
        first = generate(client, new(client))
        assert first['status'] == 'ready'
        adapters['gemini'] = Failing(ProviderError('secret-server-body', 429))
        done = generate(client, first, prompt='Altere o layout para uma proposta nova.')
        assert done['status'] == 'failed' and done['revision'] == first['revision']
        assert done['current']['files'] == first['current']['files']
        assert done['last_request'] == 'Altere o layout para uma proposta nova.'
        assert '429' in done['error'] and 'secret-server-body' not in json.dumps(done)
        assert sum(e['phase'] == 'failed' for e in done['events']) == 1
        assert all(len(adapters[name].calls) == 1 for name in adapters)


def test_local_mode_skips_every_external_integration(settings, monkeypatch):
    adapters = {'gemini': Failing(), 'mistral': Failing(), 'ollama': Builder()}
    settings = replace(configured(settings, monkeypatch, adapters), privacy_mode='local', provider='ollama')
    with TestClient(create_app(settings)) as client:
        done = generate(client, new(client))
        assert done['status'] == 'ready' and done['provider_queue'] == ['ollama']
        assert not adapters['gemini'].calls and not adapters['mistral'].calls


def test_reference_analysis_can_use_a_reserve_and_keeps_cached_image_description(settings, monkeypatch):
    class VisionBuilder(Builder):
        async def reply(self, system, messages):
            if messages[0].get('image'):
                self.calls.append((system, messages))
                return {'reply': 'Composição editorial vertical com tipografia forte e fundo claro.'}
            return await super().reply(system, messages)
    adapters = {'gemini': Failing(ProviderError('quota', 429)), 'mistral': VisionBuilder(), 'ollama': Failing()}
    settings = configured(settings, monkeypatch, adapters)
    with TestClient(create_app(settings)) as client:
        p = new(client)
        image = io.BytesIO(); Image.new('RGB', (30, 50), 'blue').save(image, 'PNG')
        uploaded = client.post('/studio/projects/' + p['id'] + '/assets', headers=AUTH,
            json={'name': 'reference.png', 'purpose': 'reference', 'data_base64': base64.b64encode(image.getvalue()).decode()}).json()
        done = generate(client, uploaded, mode='reference', reference_asset=uploaded['assets'][-1]['name'])
        assert done['status'] == 'ready' and done['active_provider'] == 'mistral'
        assert done['assets'][-1]['analysis'].startswith('Composição editorial')
        payload = json.loads(adapters['mistral'].calls[-1][1][-1]['content'])
        assert payload['visual_reference'] == done['assets'][-1]['analysis']
        assert not adapters['ollama'].calls


@pytest.mark.parametrize('kind', ['openai', 'anthropic', 'ollama'])
def test_canonical_images_are_translated_for_each_backup_api(settings, monkeypatch, kind):
    sent = []
    def handler(request):
        sent.append(json.loads(request.content))
        reply = json.dumps({'reply': 'A imagem contém um exemplo.', 'topics': [], 'tool_calls': []})
        return httpx.Response(200, json={'content': [{'type': 'text', 'text': reply}]} if kind == 'anthropic' else
            {'message': {'content': reply}} if kind == 'ollama' else {'choices': [{'message': {'content': reply}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    provider = Ollama(settings) if kind == 'ollama' else CompatibleProvider(ProviderSpec(id='backup', kind=kind, model='vision', base_url='https://example.com/v1'))
    image = {'mime_type': 'image/jpeg', 'data': 'Zml4dHVyZQ=='}
    result = asyncio.run(provider.reply('describe', [{'role': 'user', 'content': 'same image', 'image': image}]))
    assert result['reply'].startswith('A imagem')
    last = sent[0]['messages'][-1]
    assert 'image' not in last
    if kind == 'ollama': assert last['images'] == [image['data']]
    elif kind == 'openai': assert last['content'][-1]['image_url']['url'] == 'data:image/jpeg;base64,' + image['data']
    else: assert last['content'][-1]['source']['data'] == image['data']


def test_missing_primary_key_uses_configured_reserve_without_reconfiguration(settings, monkeypatch):
    adapters = {'gemini': Failing(), 'mistral': Builder(), 'ollama': Failing()}
    settings = replace(configured(settings, monkeypatch, adapters), gemini_key='')
    with TestClient(create_app(settings)) as client:
        done = generate(client, new(client))
        assert done['status'] == 'ready' and done['active_provider'] == 'mistral'
        assert not adapters['gemini'].calls and not adapters['ollama'].calls


def test_local_mode_falls_back_to_local_even_if_saved_primary_was_external(settings, monkeypatch):
    adapters = {'gemini': Failing(), 'mistral': Failing(), 'ollama': Builder()}
    settings = replace(configured(settings, monkeypatch, adapters), privacy_mode='local')
    with TestClient(create_app(settings)) as client:
        done = generate(client, new(client), provider='gemini')
        assert done['status'] == 'ready' and done['active_provider'] == 'ollama'
        assert not adapters['gemini'].calls and not adapters['mistral'].calls


def test_chosen_provider_remains_first_and_only_configured_allowed_reserves_are_prepared():
    calls = []
    provider = VisualBuilder()
    project = {'provider': 'mistral'}
    entries = [{'id': 'gemini', 'configured': True}, {'id': 'missing-key', 'configured': False},
               {'id': 'blocked', 'configured': True, 'allowed': False},
               {'id': 'ollama', 'kind': 'ollama', 'configured': True}, {'id': 'mistral', 'configured': True}]
    pool = ProviderPool(project, entries, lambda identifier: calls.append(identifier) or provider,
                        lambda *args: None, {})
    assert calls == ['mistral', 'gemini', 'ollama'] and not provider.calls
    asyncio.run(pool.reply('EXATAMENTE três direções', []))
    assert project['active_provider'] == 'mistral' and len(provider.calls) == 1
