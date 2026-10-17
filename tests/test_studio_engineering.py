"""Premium delivery contracts use actual site code and the normal job pipeline."""
import json
import re
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.studio.engineering import plan, review
from cronos.studio.validation import validate
from test_backend import settings, AUTH
from test_studio import Builder, new, generate


def shop_files():
    from cronos.studio.catalog import starter
    files=starter('loja','Ateliê de teste')
    collection='''<section data-studio-collection aria-label="Catálogo">
<label>Pesquisar<input type="search" data-collection-search></label>
<label>Categoria<select data-collection-filter><option value="">Todas</option><option value="rosto">Rosto</option><option value="olhos">Olhos</option></select></label>
<label>Ordenar<select data-collection-sort><option value="default">Destaques</option><option value="price-asc">Menor preço</option><option value="price-desc">Maior preço</option><option value="name">Nome</option></select></label>
<p data-collection-count role="status"></p><p data-collection-empty hidden role="status">Nenhum resultado</p><div class="products">
<article data-item="a" data-title="Pó acetinado" data-category="rosto" data-price="19.90"><h2>Pó acetinado</h2><p>Produto fictício</p><button type="button" data-cart-add>Adicionar Pó acetinado</button></article>
<article data-item="b" data-title="Lápis macio" data-category="olhos" data-price="12.10"><h2>Lápis macio</h2><p>Produto fictício</p><button type="button" data-cart-add>Adicionar Lápis macio</button></article>
<article data-item="c" data-title="Base leve" data-category="rosto" data-price="21.50"><h2>Base leve</h2><p>Produto fictício</p><button type="button" data-cart-add>Adicionar Base leve</button></article>
</div></section><aside data-studio-cart aria-label="Sua sacola"><h2>Sacola de demonstração</h2><p>Sem compra ou pagamento conectado; o carrinho dura nesta página.</p><span data-cart-count></span><ul data-cart-items></ul><output data-cart-total></output></aside>'''
    # Use the real starter's valid forms and metadata without presenting it as new design.
    files['index.html']=files['index.html'].replace('</main>',collection+'</main>').replace('O que faz sentido para você faz parte de cada escolha.','Uma curadoria para a rotina de maquiagem.').replace('Conteúdo de demonstração. Substitua','Dados ilustrativos. Confirme')
    files['styles.css']+='\n[hidden]{display:none!important}.products{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:24px}.studio-cart-row{display:flex;gap:10px;flex-wrap:wrap}.studio-cart-row button{min-height:36px;padding:8px}'
    return files


def shop_plan(previous=None,request='Busca, filtros, ordenação e carrinho de demonstração com 3 produtos fictícios.'):
    return plan({'category':'loja','tier':'premium_2d','brief':''}, request, previous)


def test_contract_is_not_a_price_label_and_revisions_preserve_or_explicitly_remove_features():
    first=shop_plan()
    assert first['level']=='advanced' and len(first['features'])==4 and first['minimum_items']==3
    assert first['forms']==['contact']
    premium=plan({'category':'loja'},'Crie um projeto premium.')
    assert plan({'category':'loja'},'Mude só a cor.',premium)['level']=='advanced'
    next_plan=shop_plan(first,'Troque apenas a tipografia e a cor de fundo.')
    assert next_plan['features']==first['features'] and next_plan['minimum_items']==3
    assert 'cart' not in {f['id'] for f in shop_plan(first,'Remova o carrinho. Mantenha os filtros.')['features']}
    assert shop_plan(first,'Não remova o carrinho; mude só as cores.')['features']==first['features']
    assert not shop_plan(None,'Sem busca e sem filtros. Somente informação.')['features']
    assert {f['id'] for f in shop_plan(None,'Não apenas busca, mas filtros.')['features']}=={'search','filter'}
    assert not shop_plan(None,'Pesquise imagens na web para a página.')['features']
    assert shop_plan(None,'Sem formulários. Só catálogo.')['forms']==[]


def test_scope_exposes_connections_and_blocks_oversized_catalog_instead_of_silently_cutting():
    p=shop_plan(None,'Quero carrinho com 500 produtos, checkout Pix, login e estoque real.')
    assert p['minimum_items']==500 and p['blockers']
    assert {d['id'] for d in p['dependencies']}=={'payment','accounts','inventory'}


@pytest.mark.parametrize('mutate,expected',[
    (lambda s:s.replace('data-collection-search','data-collection-wrong'),'Busca'),
    (lambda s:s.replace('data-item="b"','data-item="a"'),'IDs dos itens'),
    (lambda s:s.replace('data-price="12.10"','data-price="R$12,10"'),'Valores'),
    (lambda s:s.replace('data-cart-total','data-cart-unknown'),'Painel'),
    (lambda s:s.replace('value="rosto"','value="fantasma"'),'Filtro'),
    (lambda s:s.replace('data-item="c"','data-unrelated="c"'),'Quantidade'),
])
def test_a_claim_or_comment_cannot_satisfy_actual_missing_components(mutate,expected):
    files=shop_files();files['index.html']=mutate(files['index.html'])+'<!-- data-collection-search data-cart-total -->'
    failures=[c['name'] for c in review(files,shop_plan()) if c['status']=='failed']
    assert any(expected in name for name in failures),failures


def test_real_markup_and_contextual_forms_are_validated():
    files=shop_files()
    assert not [c for c in review(files,shop_plan()) if c['status']=='failed']
    files['index.html']=re.sub(r'<form\b[^>]*data-studio-form="booking"[\s\S]*?</form>','',files['index.html'])
    assert validate(files,required_forms=['contact'])['passed']
    assert not validate(files)['passed'] # Historical projects still require their original contract.


class ShopBuilder(Builder):
    async def reply(self,system,messages):
        self.calls.append((system,messages))
        files=shop_files()
        if json.loads(messages[-1]['content']).get('current_files'):files['styles.css']+='\nbody{background:#fff}'
        return {'reply':json.dumps({'summary':'Senhor, coleção com identidade própria e funções locais.','files':files})}


def test_job_saves_acceptance_contract_checks_pending_connections_and_exports_runtime(settings):
    builder=ShopBuilder()
    with TestClient(create_app(settings,builder)) as c:
        p=new(c,category='loja',tier='premium_2d',brief='Loja fictícia, busca, filtros, ordenação, carrinho e pagamento Pix.')
        done=generate(c,p,prompt='Construa a loja com 3 produtos fictícios e sem reservas.')
        assert done['status']=='ready',done.get('error')
        report=done['current']['report']
        assert report['engineering_plan']['forms']==['contact']
        assert report['requirements'] and all(check['status']=='passed' for check in report['requirements'])
        assert report['dependencies'][0]['status']=='unavailable'
        assert 'Conexões pendentes: Pagamento real' in done['current']['summary']
        payload=json.loads(builder.calls[0][1][-1]['content'])
        assert payload['engineering_plan']['minimum_items']==3
        content=c.get('/studio/projects/'+p['id']+'/export',headers=AUTH)
        assert content.status_code==200
        with zipfile.ZipFile(BytesIO(content.content)) as package:
            assert b'__studioFeatureTests' in package.read('site/studio-runtime.js')
            assert 'Busca no conteúdo' in package.read('VERIFICACOES.json').decode()
        edited={**done['current']['files'],'index.html':done['current']['files']['index.html'].replace('data-collection-search','data-removed-search')}
        response=c.post('/studio/projects/'+p['id']+'/files',headers=AUTH,json={'files':edited,'base_revision':1})
        assert response.status_code==422
        again=generate(c,done,prompt='Troque somente o fundo por branco.')
        assert again['status']=='ready' and len(again['current']['report']['engineering_plan']['features'])==4


def test_impossible_size_is_reported_before_spending_provider_quota(settings):
    builder=ShopBuilder()
    with TestClient(create_app(settings,builder)) as c:
        p=new(c,category='loja',brief='Faça um catálogo com filtros e 600 produtos fictícios.')
        done=generate(c,p,prompt='Crie o catálogo completo.')
        assert done['status']=='failed' and done['revision']==0 and not builder.calls
        assert '600' in done['error'] and '200' in done['error']


def test_missing_required_features_triggers_one_targeted_repair_before_commit(settings):
    class Repair(ShopBuilder):
        async def reply(self,system,messages):
            if not self.calls:
                result=await super().reply(system,messages)
                payload=json.loads(result['reply']);payload['files']['index.html']=payload['files']['index.html'].replace('data-collection-search','data-missing-search')
                return {'reply':json.dumps(payload)}
            return await super().reply(system,messages)
    builder=Repair()
    with TestClient(create_app(settings,builder)) as c:
        p=new(c,category='loja',brief='Busca, filtros, ordenação e carrinho para produtos fictícios.')
        done=generate(c,p,prompt='Faça um site premium com 3 produtos fictícios.')
        assert done['status']=='ready' and len(builder.calls)==2
        payload=json.loads(builder.calls[1][1][-1]['content'])
        assert 'Busca no conteúdo' in payload['validation_error']
        assert isinstance(payload['previous_candidate']['files'],dict)
        assert done['rejected_report']['requirements'] and len(done['history'])==2


def test_large_candidate_is_not_truncated_when_repairing_css_or_javascript(settings):
    from cronos.studio.catalog import starter
    valid=starter('hotel','Aurora')
    valid['index.html']=valid['index.html'].replace('O que faz sentido para você faz parte de cada escolha.','Atendimento planejado para este hotel.')
    valid['styles.css']+='\n/*'+'premium-layout '*3600+'*/'
    valid['app.js']+='\nconst fullCandidateTail = 92837;'
    invalid={**valid,'app.js':valid['app.js']+'\nconst broken = ;'}
    builder=Builder([{'reply':json.dumps({'summary':'Revisão.','files':invalid})},{'reply':json.dumps({'summary':'Corrigido.','files':valid})}])
    with TestClient(create_app(settings,builder)) as c:
        done=generate(c,new(c),prompt='Melhore o acabamento premium.')
        assert done['status']=='ready',done.get('error')
        payload=json.loads(builder.calls[1][1][-1]['content'])
        assert payload['previous_candidate']['files']==invalid
        assert len(json.dumps(payload['previous_candidate']))>40000
