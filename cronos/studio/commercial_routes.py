"""Authenticated, local commercial workflow attached to Studio projects.

Nothing here sends mail, publishes a site, charges a card or invents a customer.
"""
import asyncio
import json
import re
import time
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .commercial import CURRENCIES, DELIVERY_STEPS, STAGES, estimate_price, proposal_html
from .network import PublicFetchError, public_fetch


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class LeadBody(Strict):
    name: str = Field(min_length=2, max_length=150)
    category: str = Field(default='', max_length=100)
    city: str = Field(default='', max_length=140)
    country: str = Field(default='BR', max_length=2)
    address: str = Field(default='', max_length=350)
    website: str = Field(default='', max_length=500)
    phone: str = Field(default='', max_length=80)
    note: str = Field(default='', max_length=2000)

    @field_validator('country')
    @classmethod
    def country_code(cls, value):
        if not re.fullmatch(r'[A-Z]{2}', value):
            raise ValueError('Informe o código de país com duas letras maiúsculas, como BR, PT ou US.')
        return value

    @field_validator('website')
    @classmethod
    def public_website(cls, value):
        from cronos.prospects import website
        if value and not website(value):
            raise ValueError('Informe uma URL HTTP/HTTPS pública válida.')
        return value


class FromReport(Strict):
    report_id: UUID
    lead_id: str = Field(min_length=1, max_length=150)


class LinkProject(Strict):
    project_id: UUID


class StageBody(Strict):
    stage: Literal[*STAGES]
    note: str = Field(default='', max_length=3000)
    agreement: str = Field(default='', max_length=5000)


class ContactPreference(Strict):
    do_not_contact: bool
    reason: str = Field(default='', max_length=1000)


class ClientReply(Strict):
    message: str = Field(min_length=2, max_length=5000)
    stage: Literal['waiting', 'interested', 'negotiating', 'closed'] | None = None


class Provenance(Strict):
    value: str = Field(default='', max_length=3000)
    source: Literal['cliente', 'fonte pública', 'sugestão', 'pendente'] = 'pendente'


class BriefingBody(Strict):
    base_version: int = Field(ge=0)
    fields: dict[str, Provenance] = Field(min_length=1, max_length=30)


class PriceBody(Strict):
    hours: float = Field(gt=0, le=2000)
    hourly_cents: int = Field(gt=0, le=10_000_000)
    external_cents: int = Field(default=0, ge=0, le=100_000_000)
    margin_percent: int = Field(default=30, ge=0, le=70)
    uncertainty_percent: int = Field(default=15, ge=0, le=50)
    currency: Literal['BRL', 'EUR', 'USD'] = 'BRL'


class ProposalBody(Strict):
    lead_id: UUID
    project_id: UUID | None = None
    proposal_id: UUID | None = None
    base_version: int | None = Field(default=None, ge=1)
    objective: str = Field(min_length=5, max_length=5000)
    problem: str = Field(default='', max_length=3000)
    solution: str = Field(default='', max_length=3000)
    pages: list[str] = Field(default_factory=list, max_length=30)
    scope: list[str] = Field(min_length=1, max_length=30)
    features: list[str] = Field(default_factory=list, max_length=30)
    stages: list[str] = Field(default_factory=list, max_length=20)
    currency: Literal['BRL', 'EUR', 'USD'] = 'BRL'
    price_cents: int | None = Field(default=None, ge=1, le=1_000_000_000)
    delivery_date: date | None = None
    revisions: int | None = Field(default=None, ge=0, le=100)
    client_responsibilities: str = Field(default='', max_length=3000)
    hosting: str = Field(default='', max_length=3000)
    domain: str = Field(default='', max_length=1000)
    maintenance: str = Field(default='', max_length=1000)
    payment_terms: str = Field(default='', max_length=3000)
    valid_until: date | None = None
    notes: str = Field(default='', max_length=5000)

    @field_validator('scope', 'pages', 'features', 'stages')
    @classmethod
    def scope_limits(cls, values):
        if any(len(item) > 600 for item in values):
            raise ValueError('Cada entregável deve ter no máximo 600 caracteres.')
        return values


class ProposalStatus(Strict):
    status: Literal['draft', 'sent', 'accepted', 'declined']
    agreement: str = Field(default='', max_length=5000)


class OutreachBody(Strict):
    lead_id: UUID
    channel: Literal['email', 'whatsapp', 'other']
    subject: str = Field(default='', max_length=200)
    message: str = Field(min_length=5, max_length=8000)
    recipient: str = Field(default='', max_length=200)


class SentBody(Strict):
    confirmed_by_user: bool
    note: str = Field(default='', max_length=1000)


class InvoiceBody(Strict):
    lead_id: UUID
    proposal_id: UUID | None = None
    amount_cents: int = Field(gt=0, le=1_000_000_000)
    currency: Literal['BRL', 'EUR', 'USD'] = 'BRL'
    description: str = Field(min_length=3, max_length=1000)
    due_date: date | None = None


class PaymentBody(Strict):
    amount_cents: int = Field(gt=0, le=1_000_000_000)
    note: str = Field(default='', max_length=1000)
    confirmed_by_user: bool


class RecurringBody(Strict):
    lead_id: UUID
    description: str = Field(min_length=3, max_length=1000)
    amount_cents: int = Field(gt=0, le=1_000_000_000)
    currency: Literal['BRL', 'EUR', 'USD'] = 'BRL'
    period: Literal['monthly', 'quarterly', 'yearly'] = 'monthly'
    next_due: date


class RecurringUpdate(Strict):
    next_due: date
    active: bool


class DeliveryBody(Strict):
    steps: dict[str, bool]
    due_date: date | None = None
    notes: str = Field(default='', max_length=3000)


class PortfolioBody(Strict):
    title: str = Field(min_length=2, max_length=200)
    summary: str = Field(min_length=10, max_length=3000)
    outcomes: str = Field(default='', max_length=3000)
    published_url: str = Field(default='', max_length=500)
    show_publicly: bool = False
    client_permission: bool = False

    @field_validator('published_url')
    @classmethod
    def safe_published_url(cls, value):
        if value and not value.startswith(('https://', 'http://')):
            raise ValueError('Use um endereço HTTP ou HTTPS completo.')
        return value


def install_commercial(app, authenticate):
    auth = [Depends(authenticate)]

    def store():
        if app.state.studio is None:
            raise HTTPException(503, app.state.studio_error)
        return app.state.studio.commercial

    def action(callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except KeyError:
            raise HTTPException(404, 'Registro não encontrado.') from None
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    def online():
        if app.state.engine.settings.privacy_mode != 'online' or not app.state.panels.preferences.web_enabled:
            raise HTTPException(403, 'Pesquisa online desativada pelo modo local ou pela permissão de busca.')

    @app.get('/studio/business/overview', dependencies=auth)
    async def overview():
        db = store()
        return {'dashboard': db.dashboard(), 'notifications': db.notifications(),
                'stages': STAGES, 'currencies': CURRENCIES, 'delivery_steps': DELIVERY_STEPS,
                'capabilities': {'automatic_outreach': False, 'payment_gateway': False,
                                 'automatic_publication': False, 'performance_audit': False}}

    @app.get('/studio/business/leads', dependencies=auth)
    async def list_leads():
        return {'leads': store().leads()}

    @app.post('/studio/business/leads', dependencies=auth)
    async def add_lead(body: LeadBody):
        payload = body.model_dump() | {'source_label': 'Informado pelo usuário',
                                       'site_status': 'unverified', 'evidence': [],
                                       'score': {'score': None, 'priority': 'informações insuficientes', 'reasons': []}}
        return action(store().upsert_lead, payload)

    @app.post('/studio/business/leads/from-report', dependencies=auth)
    async def from_report(body: FromReport):
        online()
        report = app.state.prospects.reports.get(str(body.report_id))
        lead = next((item for item in (report or {}).get('leads', []) if item['id'] == body.lead_id), None)
        if lead is None:
            raise HTTPException(404, 'Pesquisa expirada; pesquise novamente para confirmar a fonte.')
        return action(store().from_report, report, lead)

    @app.get('/studio/business/leads/{lead_id}', dependencies=auth)
    async def get_lead(lead_id: str):
        db = store()
        lead = action(db.lead, lead_id)
        return {'lead': lead, 'briefing': db.briefing(lead_id), 'audit': db.latest_audit(lead_id),
                'events': db.events(lead_id), 'proposals': db.proposals(lead_id),
                'outreach': db.outreach_list(lead_id)}

    @app.post('/studio/business/leads/{lead_id}/project', dependencies=auth)
    async def link_project(lead_id: str, body: LinkProject):
        return action(store().link_project, lead_id, str(body.project_id))

    @app.post('/studio/business/leads/{lead_id}/audit', dependencies=auth)
    async def audit_lead(lead_id: str):
        online()
        db = store()
        lead = action(db.lead, lead_id)
        if not lead.get('website'):
            raise HTTPException(409, 'Adicione o site à ficha antes de analisar seu HTML público.')
        started = time.perf_counter()
        try:
            page = await asyncio.to_thread(public_fetch, lead['website'])
        except PublicFetchError as exc:
            raise HTTPException(422, str(exc)) from None
        from .routes import PageSummary
        doc = PageSummary()
        is_html = 'text/html' in page['headers'].get('content-type', '')
        if is_html:
            doc.feed(page['body'].decode('utf-8', errors='replace'))
        report = {'url': page['url'], 'status': page['status'],
                  'elapsed_ms': round((time.perf_counter() - started) * 1000),
                  'title': doc.title[:300], 'https': page['url'].startswith('https:'),
                  'viewport': doc.viewport, 'h1': doc.h1,
                  'images_without_alt': sum('alt' not in attrs for attrs in doc.images),
                  'forms': doc.forms, 'scripts': doc.scripts, 'nav': doc.nav,
                  'description': doc.description, 'lang': doc.lang,
                  'contact_links': doc.contact_links, 'checked_at': time.time(),
                  'html': is_html,
                  'limits': 'Somente HTML público. Não é teste de desempenho, segurança ou consentimento do cliente.'}
        return action(db.audit, lead_id, report)

    @app.post('/studio/business/leads/{lead_id}/stage', dependencies=auth)
    async def change_stage(lead_id: str, body: StageBody):
        return action(store().stage, lead_id, body.stage, body.note, body.agreement or None)

    @app.post('/studio/business/leads/{lead_id}/contact-preference', dependencies=auth)
    async def contact_preference(lead_id: str, body: ContactPreference):
        return action(store().contact_preference, lead_id, body.do_not_contact, body.reason)

    @app.post('/studio/business/leads/{lead_id}/reply', dependencies=auth)
    async def client_reply(lead_id: str, body: ClientReply):
        return action(store().record_reply, lead_id, body.message, body.stage)

    @app.post('/studio/business/leads/{lead_id}/briefing', dependencies=auth)
    async def save_briefing(lead_id: str, body: BriefingBody):
        existing = action(store().briefing, lead_id)
        fields = {**existing['fields'], **{key: value.model_dump() for key, value in body.fields.items()}}
        return action(store().save_briefing, lead_id, fields, body.base_version)

    @app.post('/studio/business/pricing', dependencies=auth)
    async def price(body: PriceBody):
        return action(estimate_price, body.hours, body.hourly_cents, body.external_cents,
                      body.margin_percent, body.uncertainty_percent) | {'currency': body.currency}

    @app.get('/studio/business/proposals', dependencies=auth)
    async def proposals():
        return {'proposals': store().proposals()}

    @app.post('/studio/business/proposals', dependencies=auth)
    async def save_proposal(body: ProposalBody):
        payload = body.model_dump(mode='json', exclude={'lead_id', 'project_id', 'proposal_id', 'base_version'})
        payload['scope'] = [item.strip() for item in body.scope if item.strip()][:30]
        if not payload['scope']:
            raise HTTPException(422, 'Informe pelo menos um entregável concreto.')
        return action(store().save_proposal, str(body.lead_id), payload,
                      str(body.project_id) if body.project_id else None,
                      str(body.proposal_id) if body.proposal_id else None,
                      body.base_version)

    @app.post('/studio/business/proposals/{proposal_id}/status', dependencies=auth)
    async def proposal_status(proposal_id: str, body: ProposalStatus):
        return action(store().set_proposal_status, proposal_id, body.status, body.agreement)

    @app.get('/studio/business/proposals/{proposal_id}/versions', dependencies=auth)
    async def proposal_versions(proposal_id: str):
        return {'versions': action(store().proposal_versions, proposal_id)}

    @app.get('/studio/business/proposals/{proposal_id}/export', dependencies=auth)
    async def export_proposal(proposal_id: str):
        db = store()
        proposal = action(db.proposal, proposal_id)
        lead = action(db.lead, proposal['lead_id'])
        return Response(proposal_html(lead, proposal), media_type='text/html; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename="Cronos-Proposta-' + proposal_id[:8] + '.html"'})

    @app.get('/studio/business/outreach', dependencies=auth)
    async def outreach():
        return {'drafts': store().outreach_list()}

    @app.post('/studio/business/outreach', dependencies=auth)
    async def draft_outreach(body: OutreachBody):
        return action(store().outreach, str(body.lead_id), body.model_dump(mode='json', exclude={'lead_id'}))

    @app.post('/studio/business/outreach/{draft_id}/sent', dependencies=auth)
    async def outreach_sent(draft_id: str, body: SentBody):
        if not body.confirmed_by_user:
            raise HTTPException(422, 'Confirme somente após enviar a mensagem por conta própria.')
        return action(store().mark_outreach_sent, draft_id, body.note)

    @app.get('/studio/business/invoices', dependencies=auth)
    async def invoices():
        return {'invoices': store().invoices()}

    @app.post('/studio/business/invoices', dependencies=auth)
    async def invoice(body: InvoiceBody):
        return action(store().invoice, str(body.lead_id), body.amount_cents, body.currency,
                      body.description, body.due_date.isoformat() if body.due_date else None,
                      str(body.proposal_id) if body.proposal_id else None)

    @app.post('/studio/business/invoices/{invoice_id}/payments', dependencies=auth)
    async def payment(invoice_id: str, body: PaymentBody):
        if not body.confirmed_by_user:
            raise HTTPException(422, 'Confirme apenas um recebimento que ocorreu de fato.')
        return action(store().payment, invoice_id, body.amount_cents, body.note)

    @app.get('/studio/business/recurring', dependencies=auth)
    async def recurring():
        return {'services': store().recurring_list()}

    @app.post('/studio/business/recurring', dependencies=auth)
    async def add_recurring(body: RecurringBody):
        return action(store().recurring, str(body.lead_id), body.description, body.amount_cents,
                      body.currency, body.period, body.next_due.isoformat())

    @app.post('/studio/business/recurring/{service_id}', dependencies=auth)
    async def update_recurring(service_id: str, body: RecurringUpdate):
        return action(store().update_recurring, service_id, body.next_due.isoformat(), body.active)

    @app.get('/studio/business/deliveries/{project_id}', dependencies=auth)
    async def delivery(project_id: str):
        return action(store().delivery, project_id)

    @app.post('/studio/business/deliveries/{project_id}', dependencies=auth)
    async def save_delivery(project_id: str, body: DeliveryBody):
        return action(store().save_delivery, project_id, body.steps,
                      body.due_date.isoformat() if body.due_date else None, body.notes)

    @app.get('/studio/business/portfolio', dependencies=auth)
    async def portfolio():
        return {'entries': store().portfolio_list()}

    @app.post('/studio/business/portfolio/{project_id}', dependencies=auth)
    async def save_portfolio(project_id: str, body: PortfolioBody):
        if body.show_publicly and not body.client_permission:
            raise HTTPException(409, 'Registre a autorização do cliente antes de marcar para uso público.')
        return action(store().portfolio, project_id, body.model_dump())

    @app.get('/studio/business/export', dependencies=auth)
    async def backup():
        content = json.dumps(store().export_data(), ensure_ascii=False, indent=2)
        return Response(content, media_type='application/json; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename="Cronos-Studio-Comercial.json"'})
