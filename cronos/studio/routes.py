import asyncio
import base64
import json
import re
import time
from html.parser import HTMLParser
from typing import Literal

import httpx
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cronos.integrations import provider_catalog
from .catalog import CATEGORY_IDS, catalog, starter
from .network import public_fetch, PublicFetchError
from .service import Studio, backend_checks
from .runtime import FormError, submit
from .validation import InvalidProject, validate


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class NewProject(Strict):
    name: str = Field(min_length=2, max_length=100)
    category: str = 'restaurante'
    brief: str = Field(default='', max_length=6000)
    contact: str = Field(default='', max_length=2000)
    reference_id: str = Field(default='', max_length=64)
    tier: Literal['reference', 'economy', 'standard', 'premium_2d', 'premium_3d'] = 'reference'
    model_type: Literal['auto', 'earbuds', 'airplane', 'hotel'] = 'auto'
    template: Literal['basic', 'standard', 'premium'] = 'premium'
    create_from_template: bool = False
    @field_validator('category')
    @classmethod
    def category_allowed(cls, value):
        if value not in CATEGORY_IDS: raise ValueError('Categoria desconhecida.')
        return value


class Generate(Strict):
    mode: Literal['autonomous', 'reference']
    prompt: str = Field(min_length=3, max_length=12000)
    provider: str = Field(default='', max_length=64)
    reference: str = Field(default='', max_length=10000)
    reference_asset: str = Field(default='', max_length=40, pattern=r'^(?:|[a-f0-9]{32}\.(?:jpg|png))$')
    research_images: bool = False


class Asset(Strict):
    name: str = Field(min_length=1, max_length=180)
    purpose: Literal['image', 'reference', 'model'] = 'image'
    data_base64: str = Field(min_length=4, max_length=11_200_000)


class FileEdit(Strict):
    files: dict[str, str]
    base_revision: int = Field(ge=0)


class Archive(Strict):
    archived: bool


class Revision(Strict):
    revision: int = Field(ge=0)


class BrowserReport(Revision):
    viewport: int = Field(ge=300, le=3000)
    checks: list[dict] = Field(max_length=20)


class Form(Strict):
    revision: int = Field(ge=0)
    kind: Literal['contact', 'booking']
    data: dict


class PublicURL(Strict):
    url: str = Field(min_length=10, max_length=2000)


class ImageQuery(Strict):
    query: str = Field(min_length=3, max_length=120)
    orientation: Literal['any', 'horizontal', 'vertical', 'square'] = 'any'


class ImagePick(Strict):
    title: str = Field(min_length=6, max_length=240)


class ImageCreate(Strict):
    provider: str = Field(min_length=1, max_length=64)
    model: Literal['gpt-image-1'] = 'gpt-image-1'
    orientation: Literal['horizontal', 'vertical'] = 'horizontal'
    purpose: Literal['image', 'reference'] = 'reference'
    prompt: str = Field(min_length=10, max_length=4000)
    approved: bool = False


class DirectionPick(Strict):
    direction_id: str = Field(min_length=1, max_length=16)


class PageSummary(HTMLParser):
    def __init__(self):
        super().__init__(); self.title = ''; self.in_title = False; self.images = []; self.forms = 0; self.viewport = False; self.h1 = 0; self.scripts = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title': self.in_title = True
        if tag == 'img': self.images.append(a)
        if tag == 'form': self.forms += 1
        if tag == 'h1': self.h1 += 1
        if tag == 'script': self.scripts += 1
        if tag == 'meta' and a.get('name') == 'viewport': self.viewport = True
    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
    def handle_data(self, text):
        if self.in_title: self.title += text


def install_studio(app, authenticate):
    auth = [Depends(authenticate)]
    def service():
        if app.state.studio is None: raise HTTPException(503, app.state.studio_error)
        return app.state.studio
    def project(identifier):
        try: return service().store.get(identifier)
        except KeyError: raise HTTPException(404, 'Projeto não encontrado.') from None
    def mutable(identifier):
        item = project(identifier)
        if item.get('archived'): raise HTTPException(409, 'Reative o projeto arquivado antes de alterá-lo.')
        if item['status'] == 'running': raise HTTPException(409, 'Cancele ou aguarde a criação antes de editar esta versão.')
        return item
    def online():
        if app.state.engine.settings.privacy_mode != 'online' or not app.state.panels.preferences.web_enabled:
            raise HTTPException(403, 'Pesquisa online desativada pelo modo local ou pela permissão de busca.')

    @app.get('/studio/catalog', dependencies=auth)
    async def get_catalog():
        from .image_generation import image_providers
        from .threed.integration import pricing_options, MODEL_NAMES
        from .threed.config import FREE_3D_MODEL_SOURCES
        settings = app.state.engine.settings
        entries = provider_catalog(settings)
        for entry in entries:
            if entry['id'] == 'gemini': entry['model'] = settings.gemini_model
        photos = settings.privacy_mode == 'online' and app.state.panels.preferences.web_enabled
        categories = [{**entry, 'remote_images': photos, 'references': [{**ref, 'remote_images': photos} for ref in entry['references']]} for entry in catalog()]
        return {'categories': categories, 'providers': entries, 'selected': settings.provider,
                'pricing_tiers': pricing_options(), 'procedural_models': MODEL_NAMES,
                'model_sources': FREE_3D_MODEL_SOURCES,
                'image_providers': image_providers(app.state.engine.settings),
                'storage': str(service().store.root), 'capabilities': ['HTML/CSS/JavaScript', 'Contato e solicitação de horário em SQLite', 'Prévia isolada', 'Edição por conversa', 'GLB autocontido', 'Exportação e versões'],
                'limits': ['Sem geração de credenciais ou acesso a código proprietário de outras IAs.', 'Pagamentos, login de clientes e estoque precisam de implementação específica antes de publicar.']}

    @app.get('/studio/projects', dependencies=auth)
    async def projects(archived: bool = False): return {'projects': service().store.list(archived=archived)}

    @app.post('/studio/projects', dependencies=auth)
    async def create(body: NewProject):
        try: return service().new(body)
        except ValueError as exc: raise HTTPException(409, str(exc)) from None

    @app.get('/studio/projects/{identifier}', dependencies=auth)
    async def get_project(identifier: str):
        project(identifier); return service().detail(identifier)

    @app.post('/studio/projects/{identifier}/archive', dependencies=auth)
    async def archive_project(identifier: str, body: Archive):
        item = project(identifier)
        if item['status'] == 'running': raise HTTPException(409, 'Cancele ou aguarde a criação antes de arquivar.')
        if not body.archived and item.get('archived') and len(service().store.list()) >= 80:
            raise HTTPException(409, 'Arquive outro projeto antes de reativar; até 80 projetos ativos.')
        item['archived'] = body.archived
        service().store.event(item, 'archive', 'Projeto arquivado sem apagar versões ou recursos.' if body.archived else 'Projeto reativado.')
        return service().detail(identifier)

    @app.post('/studio/projects/{identifier}/duplicate', dependencies=auth)
    async def duplicate(identifier: str):
        import shutil
        original = project(identifier); current = service().store.revision(original)
        try:
            copy = service().store.new({k: v for k, v in original.items() if k not in {'id', 'events', 'current', 'history', 'revision', 'created', 'updated', 'error', 'browser_reports', 'checks', 'rejected_report'}})
        except ValueError as exc: raise HTTPException(409, str(exc)) from None
        try:
            copy['name'] = original['name'][:90] + ' · cópia'
            copy['assets'] = original['assets']; copy['status'] = 'ready'
            for asset in copy['assets']:
                shutil.copyfile(service().store.asset_path(original, asset['name']), service().store.asset_path(copy, asset['name']))
            service().store.commit(copy, current['files'], 'Cópia da versão ' + str(original['revision']) + ' de ' + original['name'] + '. Histórico anterior mantido no projeto original.', current['report'])
            service().store.event(copy, 'duplicate', 'Projeto duplicado. Os dados de teste de formulários não foram copiados.')
        except (OSError, ValueError):
            with service().store.connect() as db:
                db.execute('DELETE FROM revisions WHERE project=?', (copy['id'],))
                db.execute('DELETE FROM projects WHERE id=?', (copy['id'],))
            folder = service().store.directory(copy)
            shutil.rmtree(folder)
            raise HTTPException(409, 'Não foi possível duplicar os recursos. O projeto original foi preservado.') from None
        return service().detail(copy['id'])

    @app.post('/studio/projects/{identifier}/generate', dependencies=auth)
    async def generate(identifier: str, body: Generate):
        try: return service().start(project(identifier), body)
        except ValueError as exc: raise HTTPException(409, str(exc)) from None

    @app.post('/studio/projects/{identifier}/directions', dependencies=auth)
    async def directions(identifier: str, body: Generate):
        try: return service().start_directions(project(identifier), body)
        except ValueError as exc: raise HTTPException(409, str(exc)) from None

    @app.post('/studio/projects/{identifier}/direction', dependencies=auth)
    async def choose_direction(identifier: str, body: DirectionPick):
        item = mutable(identifier)
        chosen = next((d for d in item.get('directions', []) if d['id'] == body.direction_id), None)
        if not chosen: raise HTTPException(422, 'Proposta não encontrada. Gere as propostas e escolha uma direção.')
        item['direction_id'] = chosen['id']
        service().store.event(item, 'direction', 'Direção aprovada pelo senhor: ' + chosen['name'] + '. O código só muda ao iniciar a construção.')
        return service().detail(identifier)

    @app.post('/studio/projects/{identifier}/images/generate', dependencies=auth)
    async def create_image(identifier: str, body: ImageCreate):
        try: return service().start_image(project(identifier), body)
        except ValueError as exc: raise HTTPException(409, str(exc)) from None

    @app.post('/studio/projects/{identifier}/cancel', dependencies=auth)
    async def cancel(identifier: str):
        item = project(identifier)
        if item['status'] == 'running' and service().task and not service().task.done():
            service().task.cancel(); await asyncio.gather(service().task, return_exceptions=True)
        return service().detail(identifier)

    @app.post('/studio/projects/{identifier}/settings', dependencies=auth)
    async def project_settings(identifier: str, body: NewProject):
        from .catalog import quote
        from .threed.integration import reference_id
        item = mutable(identifier)
        changes = body.model_dump(exclude_unset=True)
        if changes.get('category', item['category']) != item['category'] and 'reference_id' not in changes:
            changes['reference_id'] = ''
        candidate = {**item, **changes}
        try:
            candidate['reference_id'] = reference_id(candidate['category'], candidate['brief'], candidate.get('reference_id', ''))
            candidate['quote'] = quote(candidate['category'], candidate['brief'], candidate.get('tier', 'reference'), candidate['reference_id'])
        except ValueError as exc: raise HTTPException(422, str(exc)) from None
        item = candidate
        service().store.event(item, 'brief', 'Dados do negócio atualizados. Gere uma revisão para aplicar as mudanças ao site.')
        return service().detail(identifier)

    @app.post('/studio/projects/{identifier}/files', dependencies=auth)
    async def save_files(identifier: str, body: FileEdit):
        item = mutable(identifier)
        if item['revision'] != body.base_revision: raise HTTPException(409, 'A versão mudou. Reabra o projeto antes de salvar para não sobrescrever outra edição.')
        try: report = await asyncio.to_thread(validate, body.files, [a['name'] for a in item['assets'] if a['purpose'] != 'reference'])
        except ValueError as exc: raise HTTPException(422, str(exc)) from None
        item = mutable(identifier)
        if item['revision'] != body.base_revision: raise HTTPException(409, 'A versão mudou durante a verificação. Reabra o projeto antes de salvar.')
        if not report['passed']: raise HTTPException(422, {'message': 'A versão foi preservada; corrija as verificações que falharam.', 'report': report})
        report['backend'] = await asyncio.to_thread(backend_checks)
        report['origin'] = 'edited'
        item = mutable(identifier)
        if item['revision'] != body.base_revision: raise HTTPException(409, 'Outra versão foi salva durante os testes. Reabra o projeto antes de salvar.')
        item['status'] = 'ready'; item['error'] = None
        try: service().store.commit(item, body.files, 'Edição manual; versão anterior preservada.', report)
        except ValueError as exc: raise HTTPException(409, str(exc)) from None
        service().store.event(item, 'saved', 'Alterações salvas. Execute os testes no navegador para esta nova versão.')
        return service().detail(identifier)

    @app.post('/studio/projects/{identifier}/restore', dependencies=auth)
    async def restore(identifier: str, body: Revision):
        item = mutable(identifier)
        try:
            previous = service().store.revision(item, body.revision)
            item['status'] = 'ready'; item['error'] = None
            service().store.commit(item, previous['files'], 'Restauração da versão ' + str(body.revision), previous['report'])
        except KeyError: raise HTTPException(404, 'Versão não encontrada.') from None
        except ValueError as exc: raise HTTPException(409, str(exc)) from None
        service().store.event(item, 'restored', 'Restaurada a versão ' + str(body.revision) + '; o histórico foi mantido.')
        return service().detail(identifier)

    @app.post('/studio/projects/{identifier}/assets', dependencies=auth)
    async def upload(identifier: str, body: Asset):
        item = mutable(identifier)
        try: return await service().add_asset(item, base64.b64decode(body.data_base64, validate=True), body.purpose, body.name)
        except ValueError as exc: raise HTTPException(422, str(exc)) from None

    @app.post('/studio/projects/{identifier}/assets/{name}/remove', dependencies=auth)
    async def remove_asset(identifier: str, name: str):
        item = mutable(identifier)
        asset = next((a for a in item['assets'] if a['name'] == name), None)
        if not asset: raise HTTPException(404, 'Recurso não encontrado.')
        for revision in service().store.history(item):
            files = service().store.revision(item, revision['revision'])['files']
            if any('assets/' + name in content for content in files.values()) or (asset['purpose'] == 'model' and 'data-studio-model' in files['index.html']):
                raise HTTPException(409, 'O recurso faz parte de uma versão salva. Ele é preservado para não quebrar o histórico; crie outro projeto para outra seleção de modelos.')
        item['assets'] = [a for a in item['assets'] if a['name'] != name]
        service().store.save(item)
        service().store.asset_path(item, name).unlink(missing_ok=True)
        return service().detail(identifier)

    @app.get('/studio/projects/{identifier}/assets/{name}', dependencies=auth)
    async def asset(identifier: str, name: str):
        item = project(identifier); info = next((a for a in item['assets'] if a['name'] == name), None)
        if not info: raise HTTPException(404, 'Recurso não encontrado.')
        return Response(service().store.asset_path(item, name).read_bytes(), media_type=info['mime'])

    @app.post('/studio/projects/{identifier}/preview', dependencies=auth)
    async def preview(identifier: str): return service().preview(project(identifier))

    # Only this short-lived ticket endpoint is public, not any project or asset API.
    @app.get('/studio/preview/{ticket}')
    async def preview_document(ticket: str):
        try:
            data = service().tickets.get(ticket)
            if not data or data['expires'] <= time.time(): raise KeyError(ticket)
            await service().prepare_reference_photos(service().store.get(data['project']), data['revision'])
            html, nonce = service().render(ticket)
        except KeyError: raise HTTPException(404, 'Prévia expirada. Reabra o projeto no estúdio.') from None
        return Response(html, media_type='text/html', headers={'X-Studio-Nonce': nonce})

    @app.post('/studio/projects/{identifier}/forms', dependencies=auth)
    async def submit_form(identifier: str, body: Form):
        item = project(identifier)
        if item['revision'] != body.revision: raise HTTPException(409, 'Prévia de uma versão antiga. Atualize a prévia para enviar.')
        now = time.monotonic(); service().forms = [t for t in service().forms if now - t < 60]
        if len(service().forms) >= 12: raise HTTPException(429, 'Aguarde um minuto antes de enviar outro teste.')
        service().forms.append(now)
        try:
            result = await asyncio.to_thread(submit, service().store.directory(item) / 'preview.sqlite3', body.kind, body.data)
            return {**result, 'preview': True, 'message': 'Teste registrado na base local da prévia. Não foi enviado a nenhum cliente.'}
        except FormError as exc: raise HTTPException(422, str(exc)) from None

    @app.get('/studio/projects/{identifier}/submissions', dependencies=auth)
    async def submissions(identifier: str):
        import sqlite3
        item = project(identifier); path = service().store.directory(item) / 'preview.sqlite3'
        if not path.exists(): return {'submissions': []}
        with sqlite3.connect(path) as db:
            rows = db.execute('SELECT id,kind,payload,created FROM submissions ORDER BY created DESC LIMIT 30').fetchall()
        return {'submissions': [{'id': r[0], 'kind': r[1], 'data': json.loads(r[2]), 'created': r[3]} for r in rows], 'preview': True}

    @app.post('/studio/projects/{identifier}/checks', dependencies=auth)
    async def checks(identifier: str):
        item = project(identifier); current = service().store.revision(item)
        report = await asyncio.to_thread(validate, current['files'], [a['name'] for a in item['assets'] if a['purpose'] != 'reference'])
        report['backend'] = await asyncio.to_thread(backend_checks)
        latest = project(identifier)
        if latest['revision'] != item['revision']: raise HTTPException(409, 'A versão mudou durante os testes. Abra a nova prévia para verificá-la.')
        latest['checks'] = report; service().store.save(latest)
        return report

    @app.post('/studio/projects/{identifier}/browser-report', dependencies=auth)
    async def report(identifier: str, body: BrowserReport):
        item = project(identifier)
        if item['revision'] != body.revision: raise HTTPException(409, 'Teste pertence a outra versão.')
        checks = []
        for c in body.checks:
            if c.get('status') not in {'passed', 'failed', 'unavailable'}: raise HTTPException(422, 'Resultado inválido.')
            checks.append({'name': str(c.get('name', ''))[:120], 'status': c['status'], 'detail': str(c.get('detail', ''))[:500]})
        entry = {'revision': body.revision, 'viewport': body.viewport, 'checks': checks, 'at': time.time(), 'source': 'Observações do iframe no navegador do usuário; não é auditoria de segurança.'}
        item['browser_reports'] = [*(item.get('browser_reports') or [])[-5:], entry]; service().store.save(item)
        return entry

    @app.get('/studio/projects/{identifier}/export', dependencies=auth)
    async def export(identifier: str, draft: bool = False):
        item = project(identifier)
        detail = service().detail(identifier)
        if item['status'] == 'running': raise HTTPException(409, 'Aguarde ou cancele a criação antes de exportar.')
        if detail['code_origin'] == 'starter' and not draft:
            raise HTTPException(409, 'Este projeto ainda contém apenas o exemplo inicial. Crie uma versão com IA ou escolha explicitamente exportar o rascunho.')
        await service().prepare_reference_photos(item)
        package = await asyncio.to_thread(service().export, item)
        return Response(package, media_type='application/zip', headers={'Content-Disposition': 'attachment; filename="Cronos-Site-' + identifier[:8] + '.zip"'})

    @app.post('/studio/audit', dependencies=auth)
    async def audit(body: PublicURL):
        online(); started = time.perf_counter()
        try: page = await asyncio.to_thread(public_fetch, body.url)
        except PublicFetchError as exc: raise HTTPException(422, str(exc)) from None
        doc = PageSummary()
        is_html = 'text/html' in page['headers'].get('content-type', '')
        if is_html: doc.feed(page['body'].decode('utf-8', errors='replace'))
        return {'url': page['url'], 'status': page['status'], 'elapsed_ms': round((time.perf_counter() - started) * 1000),
                'title': doc.title[:300], 'https': page['url'].startswith('https:'), 'viewport': doc.viewport, 'h1': doc.h1,
                'images_without_alt': sum('alt' not in a for a in doc.images), 'forms': doc.forms, 'scripts': doc.scripts,
                'checked_at': time.time(), 'html': is_html,
                'limits': 'Leitura pública do HTML, sem executar scripts nem contornar login. Não prova interesse em contratar, orçamento, segurança ou desempenho real no celular.'}

    @app.post('/studio/images/search', dependencies=auth)
    async def images(body: ImageQuery):
        from .images import search_images
        online()
        try:
            return {'images': await search_images(body.query, orientation=body.orientation), 'note': 'Confira licença, autoria, marcas e autorização de pessoas antes de usar comercialmente.'}
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
            raise HTTPException(502, 'A fonte de imagens não respondeu. Use uma imagem própria ou tente mais tarde.') from None

    @app.post('/studio/projects/{identifier}/images/pick', dependencies=auth)
    async def pick(identifier: str, body: ImagePick):
        from .images import download_image
        online(); item = mutable(identifier)
        try:
            raw, source = await download_image(body.title)
            return await service().add_asset(item, raw, 'image', body.title, source)
        except (ValueError, TypeError, KeyError, AttributeError, httpx.HTTPError) as exc: raise HTTPException(422, str(exc)[:500]) from None
