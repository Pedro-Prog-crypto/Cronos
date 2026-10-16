"""The complete user-supplied Studio material is exercised, with no live AI calls."""
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile
import io

import pytest
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.studio.catalog import catalog, quote
from cronos.studio.references import REFERENCE_SITES, get_reference, get_references_by_type
from cronos.studio.threed import (Site3DGenerator, MODEL_CATALOG, get_model, list_models,
    get_price_for_site, get_reference_site, get_default_scene_config, DEFAULT_3D_SETTINGS)
from cronos.studio.threed.integration import template_site, scene_code, pricing_options
from cronos.studio.validation import validate
from test_backend import settings, AUTH
from test_studio import Builder, new, generate

ROOT = Path(__file__).resolve().parents[1]


def test_all_eight_attachments_are_preserved_byte_for_byte():
    original = ROOT/'cronos/studio/mistral_original'
    hashes = json.loads((original/'SHA256.json').read_text())
    expected = {'references.py': '5bb6e73a2d0e127a7eca3e346d57b71c04560a5238d82576d1f24aa0d2d5135a', 'pricing_config.py': '289caccc255ab405a4e03914ca90dc48e094eb2e7920b6125776e3942e4fc5e7', 'models.py': 'b31a9c88295e97e23e5f97cbc18798ccdce39d7d674d1cdb70f63a145b94a917', 'generator.py': 'c6defb459f4531a302b9d5329f30bb3953001bdc75cb88cbe0aff60cccd1df3e', 'catalog.py': '38d038035c9170905033996bbf59fca22f9218c28f84ffeccfd47b043e794678', 'template-a.html': '8420d4aacf8ea78d74a208945381d5fc41283c0733a0f7f8bb9bec3acb9f6091', 'template-b.html': '33a5009b45def191f96eaa5a248bd64bc2a7f82c34eac659a28b6d7a0146ba73', 'template-c.html': 'd36cfde34ef7c539b0fbc0e2e09f2580e118e48a07443379225f86d86b71dfa2'}
    assert expected.keys() <= hashes.keys()
    for name,digest in expected.items():
        assert hashes[name] == digest
        assert hashlib.sha256((original/(name+'.txt')).read_bytes()).hexdigest() == digest
    # The originally invalid generator was retained, not silently discarded.
    assert len((original/'generator.py.txt').read_text().splitlines()) == 1548


def test_full_catalog_has_all_source_references_prices_images_and_palettes():
    items = catalog()
    assert len(items) == 13 and len(REFERENCE_SITES) == 17
    shown = {ref['id'] for item in items for ref in item['references']}
    assert shown == REFERENCE_SITES.keys()
    for item in items:
        assert item['sample_images'] and item['features'] and item['color_scheme']
        assert item['price_range'][0] == item['min_price'] == item['estimated_price']
        assert item['price_range'][1] == item['max_price']
    assert get_reference('unknown').category == 'personalizado'
    assert len(get_references_by_type('3d')) == 4


@pytest.mark.parametrize('identifier', list(REFERENCE_SITES))
def test_every_reference_builds_a_complete_valid_site(identifier):
    ref = REFERENCE_SITES[identifier]
    files = template_site(ref.category, 'Negócio de teste', reference=identifier)
    report = validate(files)
    assert report['passed'], report['checks']
    assert len(files) == 3 and 'data-studio-form="contact"' in files['index.html']
    assert 'data-studio-form="booking"' in files['index.html']
    assert 'alert(' not in files['app.js']
    assert files['index.html'].count('src="app.js"') == 1
    assert ('data-studio-procedural' in files['index.html']) == (ref.template_type == '3d')
    from html import escape
    assert escape(ref.sample_texts['hero_title'],quote=True) in files['index.html']
    assert ref.color_scheme['primary'] in files['styles.css']


@pytest.mark.parametrize('template',['basic','standard','premium'])
def test_all_supplied_templates_connect_forms_and_category_text(template):
    files = template_site('restaurante', 'Casa de teste', template=template)
    assert validate(files)['passed']
    assert 'Casa de teste' in files['index.html']
    assert '[NOME]' not in files['index.html']
    assert 'alert(' not in files['app.js'] and '<style' not in files['index.html']


def test_four_price_tiers_and_category_estimates_are_explicit_and_consistent():
    expected = {'economy':(200,500),'standard':(1000,4000),'premium_2d':(4000,5000),'premium_3d':(5000,15000)}
    assert {p['id']:p['price_range'] for p in pricing_options()} == expected
    for tier, price in expected.items():
        estimate = quote('restaurante','',tier=tier)
        assert (estimate['min'],estimate['max']) == price
        calculated = get_price_for_site('restaurante',quality=tier)
        assert (calculated['min_price'],calculated['max_price']) == price
    assert (quote('restaurante','')['min'],quote('restaurante','')['max']) == (400,800)
    assert (quote('imobiliaria','Site 3D')['min'],quote('imobiliaria','Site 3D')['max']) == (7000,15000)
    assert get_reference_site('hotel')['name'] == 'Hotel Standard'
    assert not quote('personalizado','Loja de vasos',tier='economy')['has_3d']
    assert 'R$1.000–R$4.000' in template_site('restaurante','Teste',tier='standard',template='standard')['index.html']


def test_all_three_complete_procedural_models_and_generator_methods_remain_available(tmp_path):
    assert list_models() == ['earbuds','airplane','hotel'] and get_model('unknown') is None
    for name in MODEL_CATALOG:
        model = get_model(name)
        assert model.models and model.animations and model.interactions
        code = scene_code(name)
        target = tmp_path/(name+'.js');target.write_text(code)
        result = subprocess.run(['node','--check',str(target)],capture_output=True,text=True)
        assert result.returncode == 0, result.stderr
        assert 'roofGeometry' in code and 'antennaGeometry' in code and 'entranceGeometry' in code
        assert 'earbudPadGeometry' in code and 'windowGeometry' in code
    assert 'index.html' in Site3DGenerator().generate_3d_template('basic','Teste','loja')
    assert len(Site3DGenerator().generate_3d_template('standard','Teste','loja')) == 3
    scene = get_default_scene_config();scene['camera']['fov']=1
    assert DEFAULT_3D_SETTINGS['camera']['fov'] == 75


def test_template_generation_is_automatic_without_an_ai_and_exports_a_self_contained_renderer(settings):
    builder = Builder()
    with TestClient(create_app(settings,builder)) as client:
        made = client.post('/studio/projects',headers=AUTH,json={'category':'imobiliaria','name':'Edifício exemplo','brief':'Site 3D', 'create_from_template':True}).json()
        assert made['status'] == 'ready' and made['code_origin'] == 'template' and not builder.calls
        assert made['reference_id'] == 'imobiliaria_3d' and made['quote']['min'] == 7000
        assert not made['assets']  # No GLB is required for the supplied procedural scene.
        preview = client.post('/studio/projects/'+made['id']+'/preview',headers=AUTH,json={}).json()
        response = client.get(preview['url'])
        assert response.status_code == 200
        assert 'THREE' in response.text and 'hotel_3d' in response.text
        assert 'connect-src \'none\'' in response.headers['content-security-policy']
        assert settings.token not in response.text
        package = client.get('/studio/projects/'+made['id']+'/export',headers=AUTH)
        assert package.status_code == 200
        with ZipFile(io.BytesIO(package.content)) as archive:
            assert {'site/procedural-3d.js','LICENCAS-3D.txt'} <= set(archive.namelist())
            assert 'roofGeometry' in archive.read('site/procedural-3d.js').decode()
            assert 'src="procedural-3d.js"' in archive.read('site/index.html').decode()
            assert not any(name=='.env' or 'providers.json' in name for name in archive.namelist())


def test_wrong_reference_rejected_without_orphaning_project_and_category_edit_resets_reference(settings):
    with TestClient(create_app(settings,Builder())) as client:
        bad=client.post('/studio/projects',headers=AUTH,json={'category':'hotel','name':'Teste','reference_id':'restaurante'})
        assert bad.status_code == 409
        assert client.get('/studio/projects',headers=AUTH).json()['projects'] == []
        item=new(client)
        changed=client.post('/studio/projects/'+item['id']+'/settings',headers=AUTH,json={'name':item['name'],'category':'loja','brief':'Loja de vasos'}).json()
        assert changed['reference_id']=='loja'
        rejected=client.post('/studio/projects/'+item['id']+'/settings',headers=AUTH,json={'name':item['name'],'reference_id':'hotel','category':'loja'})
        assert rejected.status_code==422
        assert client.get('/studio/projects/'+item['id'],headers=AUTH).json()['reference_id']=='loja'


def test_status_returns_full_catalog_and_the_normal_generation_path_keeps_ai_reserves(settings):
    from uuid import uuid4
    builder=Builder()
    with TestClient(create_app(settings,builder)) as client:
        status=client.portal.call(client.app.state.registry.execute,'studio_status',{},uuid4())['result']
        assert len(status['catalog'])==13
        assert sum(len(c['references']) for c in status['catalog'])==17
        item=new(client)
        made=generate(client,item)
        assert made['status']=='ready'
        payload=json.loads(builder.calls[-1][1][-1]['content'])
        assert payload['template_reference'] is None  # Autonomous work is no longer tied to the sample palette.
        assert made['provider_queue'] and made['active_provider']=='gemini'


def test_procedural_contract_does_not_allow_arbitrary_scripts_or_unknown_models():
    files=template_site('imobiliaria','Teste',brief='3D')
    for replacement in ['unsupported','../private']:
        bad={**files,'index.html':files['index.html'].replace('data-studio-procedural="hotel"','data-studio-procedural="'+replacement+'"')}
        assert not validate(bad)['passed']
    assert not validate({**files,'index.html':files['index.html'].replace('</head>','<script src="https://example.com/malicious.js"></script></head>')})['passed']


def test_local_mode_does_not_load_the_reference_photos(settings):
    from dataclasses import replace
    with TestClient(create_app(replace(settings,privacy_mode='local'),Builder())) as client:
        listing=client.get('/studio/catalog',headers=AUTH).json()
        assert not any(c['remote_images'] for c in listing['categories'])
        assert all(not ref['remote_images'] for c in listing['categories'] for ref in c['references'])
        item=new(client,category='restaurante')
        preview=client.post('/studio/projects/'+item['id']+'/preview',headers=AUTH,json={}).json()
        response=client.get(preview['url'])
        assert 'https://images.unsplash.com' not in response.headers['content-security-policy']
        assert 'src="https://images.unsplash.com' not in response.text
        assert 'data:image/svg+xml;base64,' in response.text
