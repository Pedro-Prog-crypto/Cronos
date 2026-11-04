"""Natural-language entry points into the same persistent commercial workflow.

These tools expose evidence and local drafts. External contact, payment and
publication stay outside the model's authority.
"""
from typing import Literal
from uuid import UUID

from pydantic import Field

from cronos.tools import Arguments, Tool
from .commercial import STAGES


class BusinessRead(Arguments):
    lead_id: UUID | None = None


class BusinessStage(Arguments):
    lead_id: UUID
    stage: Literal[*STAGES]
    note: str = Field(default='', max_length=1000)
    agreement: str = Field(default='', max_length=3000)


class BusinessProposal(Arguments):
    lead_id: UUID
    objective: str = Field(min_length=5, max_length=3000)
    scope: list[str] = Field(min_length=1, max_length=20)
    project_id: UUID | None = None
    price_cents: int | None = Field(default=None, ge=1, le=1_000_000_000)
    currency: Literal['BRL', 'EUR', 'USD'] = 'BRL'


class BusinessMessage(Arguments):
    lead_id: UUID
    message: str = Field(min_length=5, max_length=5000)
    subject: str = Field(default='', max_length=200)
    channel: Literal['email', 'whatsapp', 'other'] = 'email'


def register_business_tools(app, studio):
    db = studio.commercial

    def read(args):
        if args.lead_id:
            ident = str(args.lead_id)
            lead = db.lead(ident)
            brief = db.briefing(ident)
            return {'lead': lead, 'briefing': brief, 'audit': db.latest_audit(ident),
                    'proposals': db.proposals(ident)[:5], 'history': db.events(ident)[:12],
                    'studio_project': lead.get('project_id')}
        return {'dashboard': db.dashboard(),
                'leads': [{key: lead.get(key) for key in ('id', 'name', 'category', 'city', 'stage', 'project_id', 'score')}
                          for lead in db.leads()[:20]], 'notifications': db.notifications()[:20],
                'note': 'Dados locais reais; pagamentos são lançamentos manuais, nunca confirmação bancária.'}

    def update_stage(args):
        return db.stage(str(args.lead_id), args.stage, args.note, args.agreement or None)

    def draft_proposal(args):
        lead = db.lead(str(args.lead_id))
        if any(not item.strip() or len(item) > 600 for item in args.scope):
            raise ValueError('Entregáveis vazios ou longos demais.')
        if args.project_id and lead.get('project_id') != str(args.project_id):
            raise ValueError('O projeto escolhido não está vinculado à ficha. Vincule-o pelo Studio antes.')
        payload = {'objective': args.objective, 'scope': args.scope, 'currency': args.currency,
                   'price_cents': args.price_cents, 'delivery_date': None, 'revisions': None,
                   'client_responsibilities': '', 'hosting': '', 'payment_terms': '',
                   'valid_until': None, 'notes': 'Sugestão da IA; confirme fatos, escopo e preço com o cliente antes de enviar.'}
        proposal = db.save_proposal(str(args.lead_id), payload,
                                    str(args.project_id) if args.project_id else lead.get('project_id'))
        return {'proposal_id': proposal['id'], 'status': 'draft', 'version': proposal['version'],
                'note': 'Rascunho local. Nada foi enviado ao cliente. Revise no Studio.'}

    def draft_message(args):
        draft = db.outreach(str(args.lead_id), {'channel': args.channel, 'subject': args.subject,
                       'message': args.message, 'recipient': '',
                       'note': 'Sugestão da IA para revisão; não foi enviada.'})
        return {'draft_id': draft['id'], 'status': 'draft',
                'note': 'Mensagem preparada no Studio. Nada foi enviado.'}

    app.state.registry.register(Tool(
        'studio_business_read',
        'Consulta o CRM real do Estúdio de Sites. Sem lead_id lista fichas e indicadores; com lead_id lê briefing, auditoria, propostas e histórico daquela ficha.',
        BusinessRead, read))
    app.state.registry.register(Tool(
        'studio_business_stage',
        'Registra uma etapa comercial real no CRM. Contratação exige termos aceitos; esta ferramenta pede confirmação do usuário antes de mudar os dados.',
        BusinessStage, update_stage, confirm=True))
    app.state.registry.register(Tool(
        'studio_business_proposal_draft',
        'Salva uma proposta comercial sugerida como rascunho local editável. Não envia, não fecha venda e não deve inventar necessidades ou preços.',
        BusinessProposal, draft_proposal))
    app.state.registry.register(Tool(
        'studio_business_message_draft',
        'Prepara uma mensagem comercial local para revisão humana; jamais envia automaticamente. Use apenas fatos verificados ou formulações neutras.',
        BusinessMessage, draft_message))
