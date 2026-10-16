import asyncio
import base64
import io
import json
import sqlite3
import struct
import time
import zipfile
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cronos.app import create_app
from cronos.providers import ProviderError
from cronos.studio.catalog import catalog, starter, quote
from cronos.studio.network import public_fetch, public_target, PublicFetchError
from cronos.studio.service import backend_checks
from cronos.studio.validation import validate, InvalidProject
from test_backend import settings, AUTH, FakeProvider


class Builder:
    def __init__(self, outputs=None): self.calls = []; self.outputs = outputs
    async def reply(self, system, messages):
        self.calls.append((system, messages))
        if self.outputs:
            value = self.outputs[min(len(self.calls)-1, len(self.outputs)-1)]
            if isinstance(value, Exception): raise value
            return value
        data = json.loads(messages[-1]['content'])
        files = starter(data['business']['category'], data['business']['name'], [a['name'] for a in data.get('assets', []) if a['purpose']=='image'])
        files['index.html'] = files['index.html'].replace('Conteúdo de demonstração. Substitua por informações confirmadas do seu negócio.', 'Conteúdo específico preparado a partir do briefing de teste.').replace('O que faz sentido para você faz parte de cada escolha.', 'Uma proposta construída para este projeto de teste.')
        files['index.html'] = files['index.html'].replace('Uma cozinha de encontros.', 'Site criado com briefing verificado.')
        return {'reply': json.dumps({'summary': 'Senhor, composição editorial criada para este projeto. Dados pendentes devem ser confirmados.', 'files': files}), 'topics': []}


def new(c, **kw):
    r = c.post('/studio/projects', headers=AUTH, json={'name': 'Aurora teste', 'category': 'hotel', 'brief': 'Site de hotel com formulário e solicitação de horário.', **kw})
    assert r.status_code == 200, r.text
    return r.json()


def get(c, p): return c.get('/studio/projects/' + p['id'], headers=AUTH).json()


def generate(c, p, **kw):
    r = c.post('/studio/projects/' + p['id'] + '/generate', headers=AUTH, json={'mode': 'autonomous', 'prompt': 'Crie um projeto com identidade própria.', **kw})
    assert r.status_code == 200, r.text
    for _ in range(150):
        result = get(c, p)
        if result['status'] != 'running': return result
        time.sleep(.01)
    raise AssertionError('Job did not complete')


def test_catalog_drafts_and_persistence(settings):
    builder = Builder()
    with TestClient(create_app(settings, builder)) as c:
        assert c.get('/studio/catalog').status_code == 401
        assert len(c.get('/studio/catalog', headers=AUTH).json()['categories']) == 13
        p = new(c)
        assert not builder.calls and p['revision'] == 0
        assert validate(p['current']['files'])['passed']
        assert not p['current']['report']['browser']
        assert not list((settings.vault / 'Temas').glob('*.md'))
        with c.app.state.memory.connect() as db:
            assert not db.execute('SELECT count(*) FROM turns').fetchone()[0]
    with TestClient(create_app(settings, builder)) as c:
        assert get(c, p)['name'] == 'Aurora teste'
        assert len(c.get('/studio/projects', headers=AUTH).json()['projects']) == 1
    assert settings.personality.read_text() == 'Critique premissas e reconheça incerteza.'


def test_generation_and_restore_keep_history_and_chosen_provider(settings):
    builder = Builder()
    with TestClient(create_app(settings, builder)) as c:
        p = new(c); old = p['current']['files']; done = generate(c, p)
        assert done['status'] == 'ready' and done['revision'] == 1 and len(done['history']) == 2
        assert len(builder.calls) == 1 and 'senhor' in builder.calls[0][0]
        assert done['current']['report']['passed'] and all(v['status'] == 'passed' for v in done['current']['report']['backend'])
        assert not done['browser_reports']
        restored = c.post('/studio/projects/' + p['id'] + '/restore', headers=AUTH, json={'revision': 0}).json()
        assert restored['revision'] == 2 and restored['current']['files'] == old and len(restored['history']) == 3
        assert not c.post('/studio/projects/' + p['id'] + '/files', headers=AUTH, json={'files': old, 'base_revision': 0}).status_code == 200
        assert c.post('/studio/projects/' + p['id'] + '/files', headers=AUTH, json={'files': {**old, '../bad.py': 'x'}, 'base_revision': 2}).status_code == 422


@pytest.mark.parametrize('reply', [
    {'reply': 'not json'},
    {'reply': json.dumps({'summary': 'bad', 'files': {**starter(), 'server.py': 'code'}})},
    {'reply': json.dumps({'summary': 'bad', 'files': {**starter(), 'app.js': 'fetch("http://127.0.0.1/status")'}})},
    {'reply': 'x', 'tool_calls': [{'name': 'file_write', 'arguments': {}}]},
])
def test_bad_generation_is_bounded_and_never_replaces_previous(settings, reply):
    builder = Builder([reply])
    with TestClient(create_app(settings, builder)) as c:
        p = new(c); old = p['current']['files']; done = generate(c, p)
        assert done['status'] == 'failed' and done['revision'] == 0 and done['current']['files'] == old
        assert len(builder.calls) == 2  # Initial generation + at most one explicit repair.
        assert any(e['phase'] == 'repair' for e in done['events'])
        assert len(done['history']) == 1


def test_repair_and_service_errors_are_not_unbounded_retries(settings):
    builder = Builder([{'reply': 'incomplete'}, Builder()])
    # Use a valid second package, not an implementation-shaped fake state transition.
    builder.outputs[1] = {'reply': json.dumps({'summary': 'Senhor, pacote corrigido.', 'files': starter()})}
    with TestClient(create_app(settings, builder)) as c:
        p = new(c); done = generate(c, p)
        assert done['status'] == 'ready' and len(builder.calls) == 2
    failing = Builder([ProviderError('Cota do provedor indisponível', 429)])
    with TestClient(create_app(settings, failing)) as c:
        p = new(c); done = generate(c, p)
        assert done['status'] == 'failed' and len(failing.calls) == 1


def test_cancel_and_global_generation_lock(settings):
    class Waiting:
        async def reply(self, *a): await asyncio.Event().wait()
    with TestClient(create_app(settings, Waiting())) as c:
        p = new(c); q = new(c, name='Segundo')
        body = {'mode': 'autonomous', 'prompt': 'Crie este site.'}
        assert c.post('/studio/projects/' + p['id'] + '/generate', headers=AUTH, json=body).status_code == 200
        assert c.post('/studio/projects/' + q['id'] + '/generate', headers=AUTH, json=body).status_code == 409
        assert c.post('/studio/projects/' + p['id'] + '/files', headers=AUTH, json={'files': starter(), 'base_revision': 0}).status_code == 409
        cancelled = c.post('/studio/projects/' + p['id'] + '/cancel', headers=AUTH, json={}).json()
        assert cancelled['status'] == 'cancelled' and cancelled['revision'] == 0


def test_reference_requires_input_and_never_sends_assets_without_generation(settings):
    builder = Builder()
    with TestClient(create_app(settings, builder)) as c:
        p = new(c)
        r = c.post('/studio/projects/' + p['id'] + '/generate', headers=AUTH, json={'mode': 'reference', 'prompt': 'Crie seguindo referência'})
        assert r.status_code == 409 and not builder.calls
        image = io.BytesIO(); Image.new('RGB', (80, 60), 'blue').save(image, 'PNG')
        r = c.post('/studio/projects/' + p['id'] + '/assets', headers=AUTH, json={'name': '../../.env.png', 'purpose': 'reference', 'data_base64': base64.b64encode(image.getvalue()).decode()})
        assert r.status_code == 200 and not builder.calls
        asset = r.json()['assets'][0]
        assert '..' not in asset['name'] and asset['mime'] == 'image/jpeg'
        assert c.get('/studio/projects/' + p['id'] + '/assets/' + asset['name']).status_code == 401
        assert c.get('/studio/projects/' + p['id'] + '/assets/' + asset['name'], headers=AUTH).status_code == 200


@pytest.mark.parametrize('html', ['<iframe src="http://127.0.0.1/status"></iframe>', '<script>alert(1)</script>', '<img src="https://example.com/test.jpg">', '<p onclick="alert(1)">X</p>', '<form action="https://example.com"></form>', '<meta http-equiv="refresh" content="0;http://example.com">'])
def test_untrusted_resources_and_navigation_rejected(html):
    files = starter(); files['index.html'] = files['index.html'].replace('</body>', html + '</body>')
    assert not validate(files)['passed']


def test_preview_ticket_auth_and_capability_isolation(settings):
    with TestClient(create_app(settings, Builder())) as c:
        p = new(c)
        ticket = c.post('/studio/projects/' + p['id'] + '/preview', headers=AUTH, json={}).json()
        page = c.get(ticket['url'])
        assert page.status_code == 200 and 'data-studio-form' in page.text
        csp = page.headers['content-security-policy']
        assert "sandbox allow-scripts" in csp and "connect-src 'none'" in csp and "frame-ancestors 'self'" in csp
        assert "'unsafe-inline'" not in csp and 'test-token' not in page.text
        assert 'allow-same-origin' not in csp and 'window.__studioPreview' in page.text
        assert c.get('/studio/preview/' + 'x' * 43).status_code == 404
        assert c.get('/studio/preview/' + 'x' * 43 + '/anything').status_code == 401
        assert c.get('/studio/projects/' + p['id']).status_code == 401
        c.app.state.studio.tickets[ticket['url'].split('/')[-1]]['expires'] = 0
        assert c.get(ticket['url']).status_code == 404


def test_forms_browser_reports_and_clean_export(settings):
    with TestClient(create_app(settings, Builder())) as c:
        p = new(c)
        prefix = '/studio/projects/' + p['id']
        data = {'name': "<script>test</script>", 'email': 'test@example.com', 'message': "'); DROP TABLE submissions;--", 'consent': True}
        assert c.post(prefix + '/forms', headers=AUTH, json={'revision': 0, 'kind': 'contact', 'data': data}).status_code == 200
        assert c.post(prefix + '/forms', headers=AUTH, json={'revision': 0, 'kind': 'contact', 'data': {**data, 'email': 'invalid'}}).status_code == 422
        booking = {**data, 'date': str(date.today() + timedelta(days=1)), 'time': '14:00', 'service': 'Teste'}
        assert c.post(prefix + '/forms', headers=AUTH, json={'revision': 0, 'kind': 'booking', 'data': booking}).status_code == 200
        assert c.post(prefix + '/forms', headers=AUTH, json={'revision': 0, 'kind': 'booking', 'data': booking}).status_code == 422
        rows = c.get(prefix + '/submissions', headers=AUTH).json()['submissions']
        assert len(rows) == 2 and rows[-1]['data']['message'] == data['message']
        assert c.post(prefix + '/browser-report', headers=AUTH, json={'revision': 1, 'viewport': 390, 'checks': []}).status_code == 409
        assert c.post(prefix + '/browser-report', headers=AUTH, json={'revision': 0, 'viewport': 390, 'checks': [{'name': 'DOM', 'status': 'passed'}]}).status_code == 200
        assert c.get(prefix + '/export', headers=AUTH).status_code == 409
        raw = c.get(prefix + '/export?draft=true', headers=AUTH)
        assert raw.status_code == 200
        with zipfile.ZipFile(io.BytesIO(raw.content)) as z:
            assert z.testzip() is None
            assert {'server.py', 'site/index.html', 'site/styles.css', 'site/app.js', 'site/studio-runtime.js', 'VERIFICACOES.json'} <= set(z.namelist())
            assert not any('.sqlite' in name or '.env' in name or 'vault' in name for name in z.namelist())
            assert 'studio-runtime.js' in z.read('site/index.html').decode()
            assert len(json.loads(z.read('VERIFICACOES.json'))['browser_observations']) == 1
            assert all(b'test-token' not in z.read(name) for name in z.namelist())


@pytest.mark.parametrize('url', ['http://127.0.0.1:80/', 'http://169.254.169.254/', 'https://localhost/', 'http://[::1]/', 'https://user:pass@example.com', 'file:///etc/passwd', 'https://example.com:444/', 'https://example.com\\@127.0.0.1/'])
def test_public_reader_blocks_private_targets(url):
    with pytest.raises(PublicFetchError): public_target(url)


def test_public_reader_blocks_mixed_dns_and_redirect_to_private(monkeypatch):
    def addresses(host, port, **kwargs):
        return [(2, 1, 6, '', ('93.184.216.34', port)), (2, 1, 6, '', ('127.0.0.1', port))]
    monkeypatch.setattr('socket.getaddrinfo', addresses)
    with pytest.raises(PublicFetchError): public_target('https://example.com/')
    seen=[]
    class Reply:
        status=302
        def getheaders(self): return [('Location', 'http://127.0.0.1/private')]
    class Conn:
        def __init__(self,host,ip,port): seen.append(ip)
        def request(self,*a,**kw): pass
        def getresponse(self): return Reply()
        def close(self): pass
    monkeypatch.setattr('socket.getaddrinfo', lambda host,port,**kw:[(2,1,6,'',('93.184.216.34' if host=='example.com' else '127.0.0.1',port))])
    monkeypatch.setattr('cronos.studio.network.PinnedHTTPS', Conn)
    with pytest.raises(PublicFetchError): public_fetch('https://example.com')
    assert seen == ['93.184.216.34']


def test_catalog_all_and_backend_adversarial_checks():
    for category in catalog(): assert validate(starter(category['id']))['passed']
    assert all(item['status'] == 'passed' for item in backend_checks())
    assert quote('hotel', 'pagamento e estoque')['max'] == 15000
    assert quote('restaurante', '')['min'] == 400


def test_new_business_categories_generate_tag_specific_queries(settings, monkeypatch):
    from test_prospects import PLACE
    seen=[]; original=httpx.AsyncClient
    def handle(request):
        if request.url.host=='nominatim.openstreetmap.org': return httpx.Response(200,json=[PLACE])
        seen.append(request.content.decode()); return httpx.Response(200,json={'elements':[{'type':'node','id':9,'tags':{'name':'Lava Jato Amostra','amenity':'car_wash'}}]})
    monkeypatch.setattr('cronos.prospects.httpx.AsyncClient', lambda **kw:original(transport=httpx.MockTransport(handle),trust_env=False,**kw))
    with TestClient(create_app(settings)) as c:
        for category,tag in [('hotel','tourism'),('lava_jato','amenity'),('loja','shop'),('imobiliaria','office')]:
            r=c.post('/prospects/search',headers=AUTH,json={'city':'Manaus, AM','category':category})
            assert r.status_code==200,r.text
            from urllib.parse import unquote_plus
            assert '"'+tag+'"' in unquote_plus(seen[-1])
            assert r.json()['leads'][0]['project']['financial_status'].startswith('Não informado')


def test_export_runtime_real_http_security_and_form_persistence(tmp_path):
    import threading
    from http.server import ThreadingHTTPServer
    from cronos.studio.runtime import Handler
    root=tmp_path/'deployment';(root/'site').mkdir(parents=True);(root/'private').mkdir()
    (root/'site/index.html').write_text('<h1>Site exportado de teste</h1>')
    (root/'private/do-not-serve.txt').write_text('private')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.site_root=root/'site';server.database=root/'private/contacts.sqlite3';server.hostnames={'127.0.0.1','localhost'}
    server.csrf='csrf-test-only';server.rates={};server.rate_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with httpx.Client(base_url=base,trust_env=False) as c:
            assert 'Site exportado' in c.get('/').text
            assert c.get('/private/do-not-serve.txt').status_code==404
            assert c.get('/../private/do-not-serve.txt').status_code==404
            assert c.get('/%2e%2e/private/do-not-serve.txt').status_code==404
            assert c.get('/',headers={'Host':'attacker.example'}).status_code==403
            assert c.get('/api/session',headers={'Origin':'https://attacker.example'}).status_code==403
            csrf=c.get('/api/session').json()['csrf']
            data={'name':'SQL <script>test</script>', 'email':'test@example.com','message':"'); DROP TABLE submissions;--",'consent':True}
            assert c.post('/api/contact',json=data).status_code==403
            headers={'Origin':base,'X-Studio-CSRF':csrf}
            assert c.post('/api/contact',json=data,headers=headers).status_code==201
            assert c.post('/api/contact',json={**data,'consent':False},headers=headers).status_code==422
            booking={**data,'date':str(date.today()+timedelta(days=1)),'time':'16:30','service':'Teste'}
            assert c.post('/api/booking',json=booking,headers=headers).status_code==201
            assert c.post('/api/booking',json=booking,headers=headers).status_code==422
            assert c.post('/api/contact',content=b'x'*8193,headers={**headers,'Content-Type':'application/json'}).status_code==413
            for _ in range(6): c.post('/api/contact',json=data,headers=headers)
            assert c.post('/api/contact',json=data,headers=headers).status_code==429
            assert "frame-ancestors 'none'" in c.get('/').headers['content-security-policy']
        with sqlite3.connect(server.database) as db:
            row=db.execute('SELECT payload FROM submissions ORDER BY created LIMIT 1').fetchone()
            assert json.loads(row[0])['message']==data['message']
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_metadata_resource_removal_and_internal_status(settings):
    from uuid import uuid4
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c)
        changed=c.post('/studio/projects/'+p['id']+'/settings',headers=AUTH,json={'name':'Novo nome','category':'lava_jato','brief':'Autônomo com agendamento','contact':'Telefone público confirmado'}).json()
        assert changed['name']=='Novo nome' and changed['revision']==0
        image=io.BytesIO();Image.new('RGB',(20,20),'red').save(image,'PNG')
        payload={'name':'photo.png','purpose':'image','data_base64':base64.b64encode(image.getvalue()).decode()}
        a=c.post('/studio/projects/'+p['id']+'/assets',headers=AUTH,json=payload).json()['assets'][0]
        assert c.post('/studio/projects/'+p['id']+'/assets/'+a['name']+'/remove',headers=AUTH,json={}).status_code==200
        assert not get(c,p)['assets']
        output=c.portal.call(c.app.state.registry.execute,'studio_status',{'project_id':p['id']},uuid4())
        assert output['status']=='completed' and output['result']['name']=='Novo nome'
        assert 'files' in output['result'] and 'test-token' not in json.dumps(output)


def test_glb_rejects_remote_uris_and_resource_limits(settings):
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c)
        def glb(doc):
            raw=json.dumps(doc).encode();raw+=b' '*(-len(raw)%4)
            return b'glTF'+struct.pack('<IIII',2,20+len(raw),len(raw),0x4e4f534a)+raw
        for doc in [{'buffers':[{'uri':'http://127.0.0.1/private'}]}, {'extensionsRequired':['KHR_draco_mesh_compression']},{'accessors':[{'count':2_000_000}]}]:
            result=c.post('/studio/projects/'+p['id']+'/assets',headers=AUTH,json={'name':'model.glb','purpose':'model','data_base64':base64.b64encode(glb(doc)).decode()})
            assert result.status_code==422,result.text
        assert not get(c,p)['assets']


def test_restart_marks_unfinished_jobs_without_paid_retry(settings):
    builder=Builder()
    with TestClient(create_app(settings,builder)) as c:
        p=new(c);item=c.app.state.studio.store.get(p['id']);item['status']='running';c.app.state.studio.store.save(item)
    with TestClient(create_app(settings,builder)) as c:
        item=get(c,p)
        assert item['status']=='interrupted' and item['revision']==0 and not builder.calls


def test_current_voice_keys_and_personality_never_rewritten_by_studio(settings,tmp_path):
    env=tmp_path/'.env';env.write_text('EXISTING_TEST_KEY=fixture-do-not-export\n')
    before=settings.personality.read_bytes()
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c);generate(c,p)
    assert env.read_text()=='EXISTING_TEST_KEY=fixture-do-not-export\n'
    assert settings.personality.read_bytes()==before


def test_user_address_is_appended_without_overwriting_personality(settings):
    provider=FakeProvider();settings.personality.write_text('Personalidade original: seja próximo do Pedro.')
    with TestClient(create_app(settings,provider)) as c:
        r=c.post('/chat',headers=AUTH,json={'message':'Explique o que é programação.'})
        assert r.status_code==200
        system=provider.calls[0][0]
        assert 'Personalidade original: seja próximo do Pedro.' in system
        assert 'dirija-se ao usuário como senhor' in system
        assert 'studio_status' in system
    assert settings.personality.read_text()=='Personalidade original: seja próximo do Pedro.'


def test_autonomous_image_research_is_optional_and_keeps_source(settings,monkeypatch):
    calls=[];image=io.BytesIO();Image.new('RGB',(40,30),'green').save(image,'PNG')
    async def suggest(category, orientation='any'):
        calls.append((category, orientation))
        return image.getvalue(),'File:Owned test.png',{'url':'https://commons.wikimedia.org/wiki/File:Test.png','author':'Autor de teste','license':'CC0'}
    monkeypatch.setattr('cronos.studio.images.suggest_image',suggest)
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c);done=generate(c,p,research_images=True)
        assert done['status']=='ready' and calls==[('hotel','horizontal'),('hotel','vertical')]
        assert done['assets'][0]['source']['license']=='CC0'
        q=new(c,name='Sem pesquisa');generate(c,q)
        assert calls==[('hotel','horizontal'),('hotel','vertical')]
    with TestClient(create_app(replace(settings,privacy_mode='local'),Builder())) as c:
        p=new(c,name='Modo local');generate(c,p,research_images=True)
        assert calls==[('hotel','horizontal'),('hotel','vertical')]


def test_form_contract_is_checked_per_form():
    files=starter()
    files['index.html']=files['index.html'].replace('name="message"','name="unknown_field"')
    report=validate(files)
    assert not report['passed']
    assert any(c['status']=='failed' and c['name']=='Contrato de cada formulário' for c in report['checks'])


def test_archive_restore_and_duplicate_preserve_original(settings):
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c);done=generate(c,p)
        copy=c.post('/studio/projects/'+p['id']+'/duplicate',headers=AUTH,json={}).json()
        assert copy['id']!=p['id'] and copy['revision']==0 and copy['current']['files']==done['current']['files']
        assert get(c,p)['revision']==1
        r=c.post('/studio/projects/'+p['id']+'/archive',headers=AUTH,json={'archived':True})
        assert r.status_code==200
        active=c.get('/studio/projects',headers=AUTH).json()['projects'];archived=c.get('/studio/projects?archived=true',headers=AUTH).json()['projects']
        assert [x['id'] for x in active]==[copy['id']] and [x['id'] for x in archived]==[p['id']]
        assert c.post('/studio/projects/'+p['id']+'/generate',headers=AUTH,json={'mode':'autonomous','prompt':'Mude este site'}).status_code==409
        assert c.get('/studio/projects/'+p['id']+'/export',headers=AUTH).status_code==200
        assert c.post('/studio/projects/'+p['id']+'/archive',headers=AUTH,json={'archived':False}).status_code==200
        assert len(c.get('/studio/projects',headers=AUTH).json()['projects'])==2


@pytest.mark.parametrize('endpoint',['checks','files'])
def test_slow_verification_cannot_revert_a_newer_revision(settings,monkeypatch,endpoint):
    import threading
    import cronos.studio.routes as routes
    entered=threading.Event();release=threading.Event();responses=[]
    actual=routes.backend_checks
    def blocked():
        entered.set();release.wait(timeout=6);return actual()
    monkeypatch.setattr(routes,'backend_checks',blocked)
    with TestClient(create_app(settings,Builder())) as c:
        p=new(c)
        body={} if endpoint=='checks' else {'files':p['current']['files'],'base_revision':0}
        thread=threading.Thread(target=lambda:responses.append(c.post('/studio/projects/'+p['id']+'/'+endpoint,headers=AUTH,json=body)))
        thread.start()
        try:
            assert entered.wait(timeout=3)
            done=generate(c,p)
            assert done['revision']==1 and done['status']=='ready'
        finally:
            release.set();thread.join(timeout=4)
        assert responses and responses[0].status_code==409
        latest=get(c,p)
        assert latest['revision']==1 and latest['status']=='ready'


def test_unreadable_studio_database_does_not_disable_conversation(settings):
    folder=settings.vault/'.cronos/studio';folder.mkdir(parents=True)
    database=folder/'projects.sqlite3';original=b'not a sqlite database - preserve this file';database.write_bytes(original)
    with TestClient(create_app(settings,FakeProvider())) as c:
        assert c.get('/health').status_code==200
        assert c.get('/studio/projects',headers=AUTH).status_code==503
        assert c.post('/chat',headers=AUTH,json={'message':'Explique Sócrates e equações.'}).status_code==200
    assert database.read_bytes()==original


def test_autonomous_plan_does_not_reuse_a_previous_reference(settings):
    builder=Builder()
    with TestClient(create_app(settings,builder)) as c:
        p=new(c);done=generate(c,p,reference='Referência de outro cliente: não reutilizar.')
        assert done['status']=='ready' and done['reference']==''
        sent=json.loads(builder.calls[0][1][-1]['content'])
        assert sent['reference_description']=='' and not sent['visual_reference']
