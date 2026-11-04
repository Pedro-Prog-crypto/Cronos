"""Commercial workflow assertions use local state; no simulated sale is counted."""
import json
import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.studio.commercial import estimate_price, opportunity_score
from test_backend import AUTH, settings


def post(client, path, data):
    return client.post('/studio/business' + path, headers=AUTH, json=data)


def get(client, path):
    return client.get('/studio/business' + path, headers=AUTH)


def lead(client):
    response = post(client, '/leads', {'name': 'Pizzaria da Vila', 'category': 'pizzaria',
                                       'city': 'Recife, PE', 'website': 'https://example.org'})
    assert response.status_code == 200, response.text
    return response.json()


def test_crm_proposal_finance_delivery_and_backup_are_persistent(settings):
    with TestClient(create_app(settings)) as client:
        card = lead(client)
        lead_id = card['id']
        assert card['stage'] == 'opportunity'
        assert get(client, '/overview').json()['dashboard']['currencies']['BRL']['received_cents'] == 0
        assert post(client, '/leads/' + lead_id + '/stage', {'stage': 'contracted'}).status_code == 409
        brief = get(client, '/leads/' + lead_id).json()['briefing']
        changed = post(client, '/leads/' + lead_id + '/briefing', {'base_version': brief['version'],
            'fields': {'objective': {'value': 'Receber pedidos por WhatsApp', 'source': 'cliente'}}})
        assert changed.status_code == 200, changed.text
        assert post(client, '/leads/' + lead_id + '/briefing', {'base_version': 0,
            'fields': {'objective': {'value': 'sobrescrever', 'source': 'sugestão'}}}).status_code == 409
        estimate = post(client, '/pricing', {'hours': 10, 'hourly_cents': 5000, 'external_cents': 10000})
        assert estimate.status_code == 200 and estimate.json()['suggested_low_cents'] >= 60000
        proposal = post(client, '/proposals', {'lead_id': lead_id, 'objective': 'Site de pizzaria com menu e pedidos',
            'scope': ['Cardápio responsivo', 'Contato por WhatsApp'], 'price_cents': 100000,
            'valid_until': '2099-01-01'}).json()
        assert proposal['status'] == 'draft' and proposal['version'] == 1
        revised = post(client, '/proposals', {'lead_id': lead_id, 'proposal_id': proposal['id'],
            'base_version': 1, 'objective': 'Site revisado com menu e pedidos',
            'scope': ['Cardápio responsivo', 'Contato por WhatsApp'], 'price_cents': 100000,
            'valid_until': '2099-01-01'})
        assert revised.status_code == 200 and revised.json()['version'] == 2
        versions = get(client, '/proposals/' + proposal['id'] + '/versions').json()['versions']
        assert [item['version'] for item in versions] == [2, 1]
        exported = get(client, '/proposals/' + proposal['id'] + '/export')
        assert exported.status_code == 200 and b'Card' in exported.content
        assert post(client, '/proposals/' + proposal['id'] + '/status', {'status': 'accepted'}).status_code == 409
        accepted = post(client, '/proposals/' + proposal['id'] + '/status',
                        {'status': 'accepted', 'agreement': 'Cliente confirmou o escopo e R$ 1.000.'})
        assert accepted.status_code == 200, accepted.text
        assert post(client, '/proposals', {'lead_id': lead_id, 'proposal_id': proposal['id'],
            'base_version': 2, 'objective': 'Alteração após aceite não deve mudar acordo',
            'scope': ['Outra página']}).status_code == 409
        invoice = post(client, '/invoices', {'lead_id': lead_id, 'proposal_id': proposal['id'],
            'amount_cents': 100000, 'description': 'Site contratado', 'due_date': '2099-02-01'}).json()
        assert invoice['paid_cents'] == 0
        assert post(client, '/invoices/' + invoice['id'] + '/payments',
                    {'amount_cents': 40000, 'confirmed_by_user': False}).status_code == 422
        payment = post(client, '/invoices/' + invoice['id'] + '/payments',
                       {'amount_cents': 40000, 'confirmed_by_user': True, 'note': 'PIX registrado pelo usuário'})
        assert payment.status_code == 200, payment.text
        assert post(client, '/invoices/' + invoice['id'] + '/payments',
                    {'amount_cents': 70000, 'confirmed_by_user': True}).status_code == 409
        recurring = post(client, '/recurring', {'lead_id': lead_id, 'description': 'Manutenção mensal',
            'amount_cents': 15000, 'next_due': '2099-03-01'})
        assert recurring.status_code == 200, recurring.text
        report = get(client, '/overview').json()['dashboard']
        assert report['currencies']['BRL']['received_cents'] == 40000
        assert report['currencies']['BRL']['pending_cents'] == 60000
        assert report['currencies']['BRL']['recurring_scheduled_cents'] == 15000
        backup = get(client, '/export')
        assert backup.status_code == 200 and backup.json()['tables']['payments']
        assert 'client_briefings' in backup.json()['tables']
    with TestClient(create_app(settings)) as client:
        assert get(client, '/leads/' + lead_id).json()['briefing']['fields']['objective']['value'] == 'Receber pedidos por WhatsApp'
        assert get(client, '/overview').json()['dashboard']['currencies']['BRL']['received_cents'] == 40000


def test_public_research_and_outreach_are_not_fabricated_or_sent(settings):
    with TestClient(create_app(settings)) as client:
        assert get(client, '/leads').status_code == 200
        assert client.get('/studio/business/leads').status_code == 401
        assert post(client, '/leads/from-report', {'report_id': str(uuid4()), 'lead_id': 'fake'}).status_code == 404
        card = lead(client)
        lead_id = card['id']
        draft = post(client, '/outreach', {'lead_id': lead_id, 'channel': 'email',
            'subject': 'Site da pizzaria', 'message': 'Olá, gostaria de conversar sobre o site.'}).json()
        assert draft['status'] == 'draft'
        assert get(client, '/leads/' + lead_id).json()['lead']['stage'] == 'opportunity'
        assert post(client, '/outreach/' + draft['id'] + '/sent', {'confirmed_by_user': False}).status_code == 422
        assert post(client, '/outreach/' + draft['id'] + '/sent', {'confirmed_by_user': True}).status_code == 200
        assert get(client, '/leads/' + lead_id).json()['lead']['stage'] == 'contacted'
        reply = post(client, '/leads/' + lead_id + '/reply',
                     {'message': 'O cliente pediu um orçamento.', 'stage': 'interested'})
        assert reply.status_code == 200 and reply.json()['lead']['stage'] == 'interested'
        assert any(event['kind'] == 'client_reply' for event in reply.json()['events'])
        assert post(client, '/leads/' + lead_id + '/contact-preference',
                    {'do_not_contact': True, 'reason': 'Pedido do cliente'}).status_code == 200
        assert post(client, '/outreach', {'lead_id': lead_id, 'channel': 'email',
                                         'message': 'Uma segunda mensagem indesejada.'}).status_code == 409


def test_project_delivery_portfolio_requires_real_version_and_permission(settings):
    with TestClient(create_app(settings)) as client:
        project = client.post('/studio/projects', headers=AUTH, json={
            'name': 'Pizzaria da Vila', 'category': 'restaurante', 'brief': 'Cardápio com fotos.'}).json()
        pid = project['id']
        empty = get(client, '/deliveries/' + pid).json()
        assert len(empty['steps']) >= 10
        steps = {key: False for key in empty['steps']}
        steps['code_review'] = True
        saved = post(client, '/deliveries/' + pid, {'steps': steps, 'notes': 'Revisão inicial'})
        assert saved.status_code == 200 and saved.json()['steps']['code_review']
        portfolio = {'title': 'Pizzaria da Vila', 'summary': 'Site com cardápio e contato.',
                     'show_publicly': True, 'client_permission': False}
        assert post(client, '/portfolio/' + pid, portfolio).status_code == 409
        assert post(client, '/portfolio/' + pid, portfolio | {'show_publicly': False}).status_code == 409
        assert get(client, '/portfolio').json()['entries'] == []


def test_closing_an_unsold_lead_does_not_create_a_contract_or_allow_billing(settings):
    with TestClient(create_app(settings)) as client:
        card = lead(client)
        lead_id = card['id']
        assert post(client, '/leads/' + lead_id + '/stage', {'stage': 'closed', 'note': 'Sem resposta'}).status_code == 200
        assert get(client, '/overview').json()['dashboard']['contracted'] == 0
        assert post(client, '/invoices', {'lead_id': lead_id, 'amount_cents': 50000,
                                         'description': 'Cobrança indevida'}).status_code == 409
        assert post(client, '/recurring', {'lead_id': lead_id, 'amount_cents': 10000,
                                          'description': 'Serviço indevido', 'next_due': '2099-01-01'}).status_code == 409


def test_score_has_limits_and_proposal_export_escapes_html(settings):
    assert opportunity_score({'name': 'Exemplo'})['score'] is None
    score = opportunity_score({}, {'url': 'https://example.org', 'html': True, 'status': 200,
                                   'viewport': False, 'h1': 0, 'https': True,
                                   'images_without_alt': 1, 'forms': 0})
    assert score['score'] == 60 and 'não chance de venda' in score['limits']
    assert estimate_price(8, 10000)['suggested_low_cents'] >= 80000
    with TestClient(create_app(settings)) as client:
        card = lead(client)
        response = post(client, '/proposals', {'lead_id': card['id'],
            'objective': '<script>alert(1)</script> Criar site', 'scope': ['<img src=x onerror=alert(1)>']})
        assert response.status_code == 200, response.text
        html = get(client, '/proposals/' + response.json()['id'] + '/export').text
        assert '<script>' not in html and '<img src=x' not in html
        assert '&lt;script&gt;' in html and '&lt;img' in html


def test_voice_tools_read_actual_crm_and_only_prepare_local_drafts(settings):
    with TestClient(create_app(settings)) as client:
        card = lead(client)
        registry = client.app.state.registry
        session = uuid4()
        result = asyncio.run(registry.execute('studio_business_read', {}, session))
        assert result['status'] == 'completed'
        assert result['result']['leads'][0]['id'] == card['id']
        proposal = asyncio.run(registry.execute('studio_business_proposal_draft', {
            'lead_id': card['id'], 'objective': 'Mostrar o cardápio da pizzaria',
            'scope': ['Cardápio', 'Contato']}, session))
        assert proposal['status'] == 'completed'
        assert get(client, '/proposals').json()['proposals'][0]['status'] == 'draft'
        draft = asyncio.run(registry.execute('studio_business_message_draft', {
            'lead_id': card['id'], 'message': 'Olá, posso compartilhar uma ideia de site?'}, session))
        assert draft['status'] == 'completed'
        assert get(client, '/outreach').json()['drafts'][0]['status'] == 'draft'
        pending = asyncio.run(registry.execute('studio_business_stage', {
            'lead_id': card['id'], 'stage': 'interested', 'note': 'Ele disse que tem interesse.'}, session))
        assert pending['status'] == 'pending_confirmation'
        assert get(client, '/leads/' + card['id']).json()['lead']['stage'] == 'opportunity'
        declined = asyncio.run(registry.resolve(pending['approval_id'], False, session))
        assert declined['status'] == 'cancelled'
        assert get(client, '/leads/' + card['id']).json()['lead']['stage'] == 'opportunity'
