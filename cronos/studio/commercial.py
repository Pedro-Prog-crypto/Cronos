"""Persistent commercial workflow for the existing Studio projects.

Only explicit user actions change negotiation or payment state. Public research
is evidence, never proof that a business wants to hire the user.
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from cronos.security import safe_path


STAGES = (
    'opportunity', 'verified', 'contact_prepared', 'contacted', 'waiting',
    'interested', 'proposal_sent', 'negotiating', 'contracted', 'developing',
    'reviewing', 'approved', 'delivered', 'maintenance', 'closed',
)
CURRENCIES = ('BRL', 'EUR', 'USD')
DELIVERY_STEPS = (
    'code_review', 'functional_test', 'mobile_test', 'images_and_rights',
    'seo', 'accessibility', 'domain', 'https', 'published', 'final_test',
    'client_handover',
)


def identifier(value):
    try:
        normalized = str(UUID(str(value)))
    except (TypeError, ValueError):
        raise KeyError(value) from None
    if normalized != value:
        raise KeyError(value)
    return normalized


def estimate_price(hours, hourly_cents, external_cents=0, margin_percent=30, uncertainty_percent=15):
    """Calculate a range from user-supplied costs, never a market-price claim."""
    if not 0 < hours <= 2000 or not 0 < hourly_cents <= 10_000_000 or not 0 <= external_cents <= 100_000_000:
        raise ValueError('Informe horas, valor por hora e custos reais dentro dos limites do formulário.')
    if not 0 <= margin_percent <= 70 or not 0 <= uncertainty_percent <= 50:
        raise ValueError('Margem e amplitude fora dos limites.')
    cost = (Decimal(str(hours)) * Decimal(hourly_cents) + Decimal(external_cents)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    low = (cost / (Decimal(1) - Decimal(margin_percent) / 100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    high = (low * (Decimal(1) + Decimal(uncertainty_percent) / 100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return {'cost_cents': int(cost), 'suggested_low_cents': int(low), 'suggested_high_cents': int(high),
            'margin_percent': margin_percent, 'uncertainty_percent': uncertainty_percent,
            'basis': 'Horas, valor por hora, custos, margem e amplitude informados pelo usuário. Não é preço de mercado nem acordo.'}


def opportunity_score(lead, audit=None, weights=None):
    """Score only findings actually measured on a public website."""
    weights = weights or {'no_viewport': 25, 'no_h1': 15, 'no_https': 20,
                          'missing_alt': 10, 'no_form': 10, 'no_nav': 5,
                          'no_description': 5, 'no_contact_link': 5, 'no_lang': 5}
    if not audit or not audit.get('html') or not 200 <= audit.get('status', 0) < 300:
        return {'score': None, 'priority': 'informações insuficientes', 'reasons': [],
                'limits': 'Sem auditoria HTML bem-sucedida; cadastro sem website não prova ausência de site ou interesse em contratar.'}
    checks = (
        ('no_viewport', not audit.get('viewport'), 'A página consultada não declarou viewport para celular.'),
        ('no_h1', not audit.get('h1'), 'Nenhum título H1 foi encontrado no HTML consultado.'),
        ('no_https', not audit.get('https'), 'A URL consultada não usa HTTPS.'),
        ('missing_alt', audit.get('images_without_alt', 0) > 0, 'Há imagens sem texto alternativo no HTML consultado.'),
        ('no_form', audit.get('forms', 0) == 0, 'Nenhum formulário foi encontrado no HTML consultado.'),
        ('no_nav', 'nav' in audit and audit['nav'] == 0, 'Nenhum elemento de navegação foi encontrado no HTML consultado.'),
        ('no_description', 'description' in audit and not audit['description'], 'Nenhuma descrição SEO foi encontrada no HTML consultado.'),
        ('no_contact_link', 'contact_links' in audit and audit['contact_links'] == 0, 'Nenhum link direto de e-mail, telefone ou WhatsApp foi encontrado no HTML consultado.'),
        ('no_lang', 'lang' in audit and not audit['lang'], 'O idioma não foi declarado no HTML consultado.'),
    )
    reasons = [{'finding': text, 'points': weights[key], 'source': audit['url']}
               for key, observed, text in checks if observed and weights[key] > 0]
    score = min(100, sum(item['points'] for item in reasons))
    return {'score': score, 'priority': 'alta para análise' if score >= 50 else 'intermediária' if score >= 25 else 'baixa',
            'reasons': reasons, 'limits': 'Pontuação de melhorias observáveis, não chance de venda. Não mede desempenho real em celular nem autorização do cliente.'}


def proposal_html(lead, proposal):
    """Printable, self-contained proposal; no third-party resources or scripts."""
    data = proposal['payload']
    text = lambda value: escape(str(value or ''))
    rows = ''.join('<li>' + text(item) + '</li>' for item in data.get('scope', []))
    amount = ('Valor proposto: ' + f"{data['currency']} {Decimal(data['price_cents']) / 100:,.2f}") if data.get('price_cents') is not None else 'Investimento: a definir com o cliente.'
    sections = [
        ('Problema observado ou relatado', data.get('problem') or 'A confirmar com o cliente.'),
        ('Objetivo', data.get('objective')),
        ('Solução proposta', data.get('solution') or 'Conforme o escopo abaixo, após validação com o cliente.'),
        ('Páginas', ', '.join(data.get('pages') or []) or 'A definir no briefing.'),
        ('Entregáveis', '<ul>' + rows + '</ul>'),
        ('Funcionalidades', ', '.join(data.get('features') or []) or 'Conforme os entregáveis acima.'),
        ('Etapas de desenvolvimento', ', '.join(data.get('stages') or []) or 'A combinar.'),
        ('Prazo estimado', data.get('delivery_date') or 'A combinar.'),
        ('Responsabilidades do cliente', data.get('client_responsibilities') or 'Fornecer e aprovar conteúdo, dados comerciais e direitos das imagens.'),
        ('Revisões incluídas', data.get('revisions') if data.get('revisions') is not None else 'A combinar.'),
        ('Hospedagem, domínio e manutenção', data.get('hosting') or 'Não definidos nesta proposta.'),
        ('Domínio', data.get('domain') or 'A definir.'),
        ('Manutenção', data.get('maintenance') or 'A definir.'),
        ('Investimento', amount),
        ('Condições de pagamento', data.get('payment_terms') or 'A combinar.'),
        ('Validade', data.get('valid_until') or 'Não definida.'),
    ]
    body = ''.join('<section><h2>' + text(title) + '</h2>' + (content if title == 'Entregáveis' else '<p>' + text(content) + '</p>') + '</section>' for title, content in sections)
    return ('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Proposta · ' + text(lead['name']) + '</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:820px;margin:auto;padding:48px;color:#172a31}'
            'h1{font-size:38px;line-height:1.15}h2{font-size:18px;margin:30px 0 4px;border-bottom:1px solid #ccd7d9}section{break-inside:avoid}'
            'small{color:#526a70}li{margin:6px 0}@media print{body{padding:0}}</style><main><small>CRONOS STUDIO · PROPOSTA EDITÁVEL</small>'
            '<h1>' + text(lead['name']) + '</h1><p>Versão ' + str(proposal['version']) + ' · ' + text(proposal['status']) + '</p>'
            + body + '<small>Proposta preparada para revisão. Não constitui contrato, venda confirmada ou publicação automática.</small></main></html>')


class CommercialStore:
    def __init__(self, studio_store):
        self.studio = studio_store
        self.dbpath = safe_path(studio_store.root, 'commercial.sqlite3', private=True)
        with self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version < 1:
                db.executescript('''
                    CREATE TABLE IF NOT EXISTS business_leads(id TEXT PRIMARY KEY, source_id TEXT UNIQUE, payload TEXT NOT NULL, stage TEXT NOT NULL, project_id TEXT, created REAL NOT NULL, updated REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS business_events(id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS digital_audits(id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS client_briefings(lead_id TEXT PRIMARY KEY, version INTEGER NOT NULL, payload TEXT NOT NULL, updated REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS business_proposals(id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, project_id TEXT, version INTEGER NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS proposal_versions(proposal_id TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(proposal_id,version));
                    CREATE TABLE IF NOT EXISTS outreach_drafts(id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS invoices(id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, proposal_id TEXT, amount_cents INTEGER NOT NULL, currency TEXT NOT NULL, due_date TEXT, description TEXT NOT NULL, created REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY, invoice_id TEXT NOT NULL, amount_cents INTEGER NOT NULL, note TEXT NOT NULL, recorded_at REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS recurring_services(id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, description TEXT NOT NULL, amount_cents INTEGER NOT NULL, currency TEXT NOT NULL, period TEXT NOT NULL, next_due TEXT NOT NULL, active INTEGER NOT NULL, created REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS project_deliveries(project_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS portfolio_entries(project_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated REAL NOT NULL);
                    CREATE TABLE IF NOT EXISTS commercial_settings(key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                    PRAGMA user_version=1;
                ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.dbpath, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('PRAGMA journal_mode=WAL')
            with db:
                yield db
        finally:
            db.close()

    def lead(self, lead_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM business_leads WHERE id=?', (identifier(lead_id),)).fetchone()
            agreement = db.execute('SELECT 1 FROM business_events WHERE lead_id=? AND kind=? LIMIT 1',
                                   (lead_id, 'agreement')).fetchone() if row else None
        if row is None: raise KeyError(lead_id)
        return {**json.loads(row['payload']), 'id':row['id'], 'stage':row['stage'], 'project_id':row['project_id'],
                'created':row['created'], 'updated':row['updated'], 'has_agreement':bool(agreement)}

    def leads(self):
        with self.connect() as db:
            rows = db.execute('SELECT id FROM business_leads ORDER BY updated DESC LIMIT 500').fetchall()
        return [self.lead(row['id']) for row in rows]

    def upsert_lead(self, data, source_id=None):
        now = time.time()
        with self.connect() as db:
            old = db.execute('SELECT * FROM business_leads WHERE source_id=?', (source_id,)).fetchone() if source_id else None
            if old:
                payload = {**json.loads(old['payload']), **{key:value for key,value in data.items() if value not in ('',None,[])}}
                db.execute('UPDATE business_leads SET payload=?,updated=? WHERE id=?', (json.dumps(payload,ensure_ascii=False),now,old['id']))
                lead_id = old['id']
            else:
                if db.execute('SELECT count(*) FROM business_leads').fetchone()[0] >= 500:
                    raise ValueError('Limite de 500 fichas comerciais; exporte seus dados antes de adicionar outras.')
                lead_id = str(uuid4())
                db.execute('INSERT INTO business_leads VALUES(?,?,?,?,?,?,?)',
                           (lead_id,source_id,json.dumps(data,ensure_ascii=False),'opportunity',None,now,now))
                db.execute('INSERT INTO business_events(lead_id,kind,payload,created) VALUES(?,?,?,?)',
                           (lead_id,'created',json.dumps({'source':data.get('source_label','Informado pelo usuário')},ensure_ascii=False),now))
        return self.lead(lead_id)

    def from_report(self, report, item):
        data = {'name':item['name'], 'category':item.get('category') or report.get('category',''),
                'city':item.get('city') or report.get('city',''), 'country':'BR',
                'address':item.get('address') or '', 'website':item.get('website') or '',
                'phone':item.get('phone') or '', 'site_status':item.get('site_status') or 'unverified',
                'source_label':'Pesquisa pública', 'evidence':item.get('evidence',[])[:12],
                'score':{'score':None,'priority':'informações insuficientes','reasons':[]}}
        return self.upsert_lead(data,source_id=item['id'])

    def link_project(self, lead_id, project_id):
        self.studio.get(project_id)
        now=time.time()
        with self.connect() as db:
            if not db.execute('SELECT id FROM business_leads WHERE id=?',(identifier(lead_id),)).fetchone():raise KeyError(lead_id)
            db.execute('UPDATE business_leads SET project_id=?,updated=? WHERE id=?',(project_id,now,lead_id))
            db.execute('INSERT INTO business_events(lead_id,kind,payload,created) VALUES(?,?,?,?)',
                       (lead_id,'project_linked',json.dumps({'project_id':project_id}),now))
        return self.lead(lead_id)

    def audit(self, lead_id, report, weights=None):
        lead=self.lead(lead_id);score=opportunity_score(lead,report,weights)
        with self.connect() as db:
            db.execute('INSERT INTO digital_audits VALUES(?,?,?,?)',(str(uuid4()),lead_id,json.dumps(report,ensure_ascii=False),time.time()))
            payload={k:v for k,v in lead.items() if k not in {'id','stage','project_id','created','updated','has_agreement'}}
            payload.update(score=score,site_status='verified' if score['score'] is not None else 'unavailable')
            db.execute('UPDATE business_leads SET payload=?,updated=? WHERE id=?',(json.dumps(payload,ensure_ascii=False),time.time(),lead_id))
        return {'lead':self.lead(lead_id),'audit':report}

    def latest_audit(self, lead_id):
        self.lead(lead_id)
        with self.connect() as db:
            row=db.execute('SELECT payload FROM digital_audits WHERE lead_id=? ORDER BY created DESC LIMIT 1',(lead_id,)).fetchone()
        return json.loads(row['payload']) if row else None

    def stage(self, lead_id, stage, note='', agreement=None):
        lead=self.lead(lead_id)
        if stage not in STAGES:raise ValueError('Etapa comercial desconhecida.')
        if stage in {'contracted','developing','reviewing','approved','delivered','maintenance'} and not (
            agreement or self.events(lead_id,'agreement')):
            raise ValueError('Registre os termos do acordo confirmado antes de marcar o negócio como contratado.')
        if stage == 'contracted' and not agreement:
            raise ValueError('Informe os termos realmente aceitos pelo cliente.')
        now=time.time()
        with self.connect() as db:
            db.execute('UPDATE business_leads SET stage=?,updated=? WHERE id=?',(stage,now,lead_id))
            db.execute('INSERT INTO business_events(lead_id,kind,payload,created) VALUES(?,?,?,?)',
                       (lead_id,'agreement' if agreement else 'stage',json.dumps({'from':lead['stage'],'to':stage,'note':note,'agreement':agreement},ensure_ascii=False),now))
        return self.lead(lead_id)

    def contact_preference(self, lead_id, do_not_contact, reason=''):
        lead=self.lead(lead_id);now=time.time()
        payload={k:v for k,v in lead.items() if k not in {'id','stage','project_id','created','updated','has_agreement'}}
        payload['do_not_contact']=bool(do_not_contact)
        with self.connect() as db:
            db.execute('UPDATE business_leads SET payload=?,updated=? WHERE id=?',
                       (json.dumps(payload,ensure_ascii=False),now,lead_id))
            db.execute('INSERT INTO business_events(lead_id,kind,payload,created) VALUES(?,?,?,?)',
                       (lead_id,'contact_preference',json.dumps({'do_not_contact':bool(do_not_contact),'reason':reason},ensure_ascii=False),now))
        return self.lead(lead_id)

    def record_reply(self, lead_id, message, stage=None):
        self.lead(lead_id)
        now=time.time()
        with self.connect() as db:
            db.execute('INSERT INTO business_events(lead_id,kind,payload,created) VALUES(?,?,?,?)',
                       (lead_id,'client_reply',json.dumps({'message':message,'source':'Relatado pelo usuário'},ensure_ascii=False),now))
        if stage:
            self.stage(lead_id,stage,'Resposta do cliente informada pelo usuário.')
        return {'lead':self.lead(lead_id),'events':self.events(lead_id)}

    def events(self, lead_id, kind=None):
        self.lead(lead_id)
        with self.connect() as db:
            rows=db.execute('SELECT kind,payload,created FROM business_events WHERE lead_id=?'+(' AND kind=?' if kind else '')+' ORDER BY created DESC LIMIT 100',
                            (lead_id,kind) if kind else (lead_id,)).fetchall()
        return [{'kind':row['kind'],'payload':json.loads(row['payload']),'created':row['created']} for row in rows]

    def briefing(self, lead_id):
        lead=self.lead(lead_id)
        with self.connect() as db:
            row=db.execute('SELECT version,payload,updated FROM client_briefings WHERE lead_id=?',(lead_id,)).fetchone()
        if row:return {'lead_id':lead_id,'version':row['version'],'fields':json.loads(row['payload']),'updated':row['updated']}
        # Each value has provenance; unknowns stay empty until supplied.
        return {'lead_id':lead_id,'version':0,'fields':{
            'business_name':{'value':lead['name'],'source':lead.get('source_label','Informado pelo usuário')},
            'category':{'value':lead.get('category',''),'source':lead.get('source_label','Informado pelo usuário')},
            'location':{'value':lead.get('city',''),'source':lead.get('source_label','Informado pelo usuário')},
            'objective':{'value':'','source':'pendente'},'audience':{'value':'','source':'pendente'},
            'products':{'value':'','source':'pendente'},'identity':{'value':'','source':'pendente'},
            'pages':{'value':'','source':'pendente'},'functions':{'value':'','source':'pendente'},
            'images':{'value':'','source':'pendente'},'deadline':{'value':'','source':'pendente'},
        },'updated':None}

    def save_briefing(self, lead_id, fields, base_version):
        current=self.briefing(lead_id)
        if current['version']!=base_version:raise ValueError('O briefing mudou. Reabra a ficha antes de salvar para preservar as edições.')
        now=time.time()
        with self.connect() as db:
            db.execute('INSERT INTO client_briefings VALUES(?,?,?,?) ON CONFLICT(lead_id) DO UPDATE SET version=excluded.version,payload=excluded.payload,updated=excluded.updated',
                       (lead_id,base_version+1,json.dumps(fields,ensure_ascii=False),now))
        return self.briefing(lead_id)

    def proposal(self, proposal_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM business_proposals WHERE id=?',(identifier(proposal_id),)).fetchone()
        if not row:raise KeyError(proposal_id)
        return {**dict(row),'payload':json.loads(row['payload'])}

    def proposals(self, lead_id=None):
        with self.connect() as db:
            rows=db.execute('SELECT id FROM business_proposals'+(' WHERE lead_id=?' if lead_id else '')+' ORDER BY updated DESC LIMIT 300',
                            (lead_id,) if lead_id else ()).fetchall()
        return [self.proposal(row['id']) for row in rows]

    def save_proposal(self, lead_id, payload, project_id=None, proposal_id=None, base_version=None):
        self.lead(lead_id)
        if project_id:self.studio.get(project_id)
        now=time.time()
        with self.connect() as db:
            if proposal_id:
                old=self.proposal(proposal_id)
                if old['lead_id']!=lead_id or old['version']!=base_version:raise ValueError('A proposta mudou. Reabra antes de revisar.')
                if old['status']=='accepted':raise ValueError('Uma proposta já aceita não pode ser alterada. Crie outra versão como nova proposta e confirme um novo acordo.')
                version=base_version+1;proposal_id=identifier(proposal_id)
                db.execute('UPDATE business_proposals SET payload=?,version=?,status=?,updated=? WHERE id=?',
                           (json.dumps(payload,ensure_ascii=False),version,'draft',now,proposal_id))
            else:
                proposal_id=str(uuid4());version=1
                db.execute('INSERT INTO business_proposals VALUES(?,?,?,?,?,?,?,?)',
                           (proposal_id,lead_id,project_id,version,'draft',json.dumps(payload,ensure_ascii=False),now,now))
            db.execute('INSERT INTO proposal_versions VALUES(?,?,?,?)',(proposal_id,version,json.dumps(payload,ensure_ascii=False),now))
        return self.proposal(proposal_id)

    def proposal_versions(self, proposal_id):
        self.proposal(proposal_id)
        with self.connect() as db:
            rows=db.execute('SELECT version,payload,created FROM proposal_versions WHERE proposal_id=? ORDER BY version DESC',
                            (proposal_id,)).fetchall()
        return [{'version':row['version'],'payload':json.loads(row['payload']),'created':row['created']} for row in rows]

    def set_proposal_status(self, proposal_id, status, agreement=''):
        proposal=self.proposal(proposal_id)
        if status not in {'draft','sent','accepted','declined'}:raise ValueError('Estado da proposta inválido.')
        if status=='accepted':
            if not agreement.strip() or not proposal['payload'].get('price_cents'):
                raise ValueError('Informe o acordo e o valor aceito antes de registrar a contratação.')
            self.stage(proposal['lead_id'],'contracted',agreement=agreement.strip())
        with self.connect() as db:
            db.execute('UPDATE business_proposals SET status=?,updated=? WHERE id=?',(status,time.time(),proposal_id))
        return self.proposal(proposal_id)

    def outreach(self, lead_id, payload):
        lead=self.lead(lead_id)
        if lead.get('do_not_contact'):raise ValueError('Este negócio está marcado para não receber contato.')
        now=time.time();draft_id=str(uuid4())
        with self.connect() as db:
            db.execute('INSERT INTO outreach_drafts VALUES(?,?,?,?,?,?)',(draft_id,lead_id,json.dumps(payload,ensure_ascii=False),'draft',now,now))
        return self.outreach_draft(draft_id)

    def outreach_draft(self, draft_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM outreach_drafts WHERE id=?',(identifier(draft_id),)).fetchone()
        if not row:raise KeyError(draft_id)
        return {**dict(row),'payload':json.loads(row['payload'])}

    def outreach_list(self, lead_id=None):
        with self.connect() as db:
            rows=db.execute('SELECT id FROM outreach_drafts'+(' WHERE lead_id=?' if lead_id else '')+' ORDER BY updated DESC LIMIT 300',
                            (lead_id,) if lead_id else ()).fetchall()
        return [self.outreach_draft(row['id']) for row in rows]

    def mark_outreach_sent(self, draft_id, note):
        draft=self.outreach_draft(draft_id)
        if self.lead(draft['lead_id']).get('do_not_contact'):
            raise ValueError('Este negócio está marcado para não receber contato.')
        with self.connect() as db:
            db.execute('UPDATE outreach_drafts SET status=?,updated=? WHERE id=?',('sent_by_user',time.time(),draft_id))
            db.execute('INSERT INTO business_events(lead_id,kind,payload,created) VALUES(?,?,?,?)',
                       (draft['lead_id'],'outreach_sent',json.dumps({'draft_id':draft_id,'note':note},ensure_ascii=False),time.time()))
        self.stage(draft['lead_id'],'contacted','Envio informado pelo usuário.')
        return self.outreach_draft(draft_id)

    def invoice(self, lead_id, amount_cents, currency, description, due_date=None, proposal_id=None):
        lead=self.lead(lead_id)
        if not self.events(lead_id,'agreement'):
            raise ValueError('Registre primeiro um acordo real antes de criar uma cobrança.')
        if proposal_id and self.proposal(proposal_id)['lead_id']!=lead_id:raise ValueError('Proposta de outro negócio.')
        invoice_id=str(uuid4());now=time.time()
        with self.connect() as db:
            db.execute('INSERT INTO invoices VALUES(?,?,?,?,?,?,?,?)',(invoice_id,lead_id,proposal_id,amount_cents,currency,due_date,description,now))
        return self.get_invoice(invoice_id)

    def get_invoice(self, invoice_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM invoices WHERE id=?',(identifier(invoice_id),)).fetchone()
            if not row:raise KeyError(invoice_id)
            paid=db.execute('SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE invoice_id=?',(invoice_id,)).fetchone()[0]
        return {**dict(row),'paid_cents':paid,'pending_cents':max(0,row['amount_cents']-paid)}

    def invoices(self):
        with self.connect() as db:rows=db.execute('SELECT id FROM invoices ORDER BY created DESC LIMIT 500').fetchall()
        return [self.get_invoice(row['id']) for row in rows]

    def payment(self, invoice_id, amount_cents, note):
        invoice=self.get_invoice(invoice_id)
        if amount_cents<=0 or amount_cents>invoice['pending_cents']:raise ValueError('Pagamento maior que o saldo pendente ou inválido.')
        payment_id=str(uuid4());now=time.time()
        with self.connect() as db:
            db.execute('INSERT INTO payments VALUES(?,?,?,?,?)',(payment_id,invoice_id,amount_cents,note,now))
        return {'id':payment_id,'invoice':self.get_invoice(invoice_id),'amount_cents':amount_cents,'recorded_at':now,
                'note':'Recebimento registrado manualmente pelo usuário; não houve verificação bancária.'}

    def recurring(self, lead_id, description, amount_cents, currency, period, next_due):
        lead=self.lead(lead_id)
        if not self.events(lead_id,'agreement'):
            raise ValueError('Serviço recorrente exige acordo confirmado.')
        service_id=str(uuid4());now=time.time()
        with self.connect() as db:
            db.execute('INSERT INTO recurring_services VALUES(?,?,?,?,?,?,?,?,?)',(service_id,lead_id,description,amount_cents,currency,period,next_due,1,now))
        return self.get_recurring(service_id)

    def get_recurring(self, service_id):
        with self.connect() as db:row=db.execute('SELECT * FROM recurring_services WHERE id=?',(identifier(service_id),)).fetchone()
        if not row:raise KeyError(service_id)
        return dict(row)

    def recurring_list(self):
        with self.connect() as db:rows=db.execute('SELECT * FROM recurring_services ORDER BY created DESC LIMIT 300').fetchall()
        return [dict(row) for row in rows]

    def update_recurring(self, service_id, next_due, active):
        self.get_recurring(service_id)
        with self.connect() as db:db.execute('UPDATE recurring_services SET next_due=?,active=? WHERE id=?',(next_due,int(active),service_id))
        return self.get_recurring(service_id)

    def delivery(self, project_id):
        self.studio.get(project_id)
        with self.connect() as db:row=db.execute('SELECT payload,updated FROM project_deliveries WHERE project_id=?',(project_id,)).fetchone()
        if row:return {'project_id':project_id,**json.loads(row['payload']),'updated':row['updated']}
        return {'project_id':project_id,'steps':{step:False for step in DELIVERY_STEPS},'due_date':None,'notes':'','updated':None}

    def save_delivery(self, project_id, steps, due_date, notes):
        current=self.delivery(project_id)
        if set(steps)!=set(DELIVERY_STEPS):raise ValueError('Lista de entrega incompleta.')
        payload={'steps':steps,'due_date':due_date,'notes':notes}
        with self.connect() as db:
            db.execute('INSERT INTO project_deliveries VALUES(?,?,?) ON CONFLICT(project_id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',
                       (project_id,json.dumps(payload,ensure_ascii=False),time.time()))
        return self.delivery(project_id)

    def portfolio(self, project_id, payload):
        project=self.studio.get(project_id)
        if project['revision']<1 or project['status']!='ready':raise ValueError('Somente uma versão pronta pode entrar no portfólio.')
        with self.connect() as db:
            db.execute('INSERT INTO portfolio_entries VALUES(?,?,?) ON CONFLICT(project_id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',
                       (project_id,json.dumps(payload,ensure_ascii=False),time.time()))
        return {'project_id':project_id,**payload}

    def portfolio_list(self):
        with self.connect() as db:rows=db.execute('SELECT * FROM portfolio_entries ORDER BY updated DESC LIMIT 100').fetchall()
        return [{'project_id':row['project_id'],**json.loads(row['payload']),'updated':row['updated']} for row in rows]

    def dashboard(self):
        invoices=self.invoices();recurring=self.recurring_list();proposals=self.proposals();leads=self.leads()
        agreed={lead['id'] for lead in leads if lead['has_agreement']}
        currencies={currency:{'invoiced_cents':sum(i['amount_cents'] for i in invoices if i['currency']==currency),
                              'received_cents':sum(i['paid_cents'] for i in invoices if i['currency']==currency),
                              'pending_cents':sum(i['pending_cents'] for i in invoices if i['currency']==currency),
                              'recurring_scheduled_cents':sum(i['amount_cents'] for i in recurring if i['currency']==currency and i['active'])}
                    for currency in CURRENCIES}
        paid=[i for i in invoices if i['paid_cents']>0]
        for currency in CURRENCIES:
            values=[i['paid_cents'] for i in paid if i['currency']==currency]
            currencies[currency]['average_paid_ticket_cents']=round(sum(values)/len(values)) if values else 0
        return {'currencies':currencies,'leads':len(leads),'contracted':len(agreed),
                'proposals':len(proposals),'proposals_sent':sum(p['status']=='sent' for p in proposals),
                'conversion_rate':round(100*len(agreed)/len(leads),1) if leads else 0,
                'basis':'Somente registros comerciais informados pelo usuário. Recebimentos não são verificação bancária; moedas não são convertidas.'}

    def notifications(self):
        today=datetime.now(ZoneInfo('America/Sao_Paulo')).date();horizon=today+timedelta(days=7);items=[]
        for proposal in self.proposals():
            value=proposal['payload'].get('valid_until')
            if proposal['status'] in {'draft','sent'} and value and date.fromisoformat(value)<=horizon:
                items.append({'kind':'proposal_due','reference':proposal['id'],'title':'Validade da proposta atingida','date':value})
        for invoice in self.invoices():
            if invoice['pending_cents'] and invoice['due_date'] and date.fromisoformat(invoice['due_date'])<=horizon:
                items.append({'kind':'invoice_due','reference':invoice['id'],'title':'Cobrança pendente registrada','date':invoice['due_date']})
        for recurring in self.recurring_list():
            if recurring['active'] and date.fromisoformat(recurring['next_due'])<=horizon:
                items.append({'kind':'recurring_due','reference':recurring['id'],'title':'Manutenção programada','date':recurring['next_due']})
        return sorted(items,key=lambda item:item['date'])[:100]

    def export_data(self):
        # Owner-initiated backup of the commercial database. Studio project
        # assets have their own export; credentials and Cronos memory stay out.
        tables = ('business_leads', 'business_events', 'digital_audits',
                  'client_briefings', 'business_proposals', 'proposal_versions',
                  'outreach_drafts', 'invoices', 'payments', 'recurring_services',
                  'project_deliveries', 'portfolio_entries', 'commercial_settings')
        with self.connect() as db:
            rows = {table: [dict(row) for row in db.execute('SELECT * FROM ' + table)]
                    for table in tables}
        return {'format': 'cronos-commercial-v1',
                'created_at': datetime.now().astimezone().isoformat(),
                'tables': rows, 'note': 'Backup dos dados comerciais. Projetos, recursos e sites são exportados separadamente.'}
