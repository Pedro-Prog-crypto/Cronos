"""Phase 1: a pizzeria travels from customer photographs to a runnable export."""
import base64
import io
import json
import re
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from cronos.app import create_app
from cronos.studio.pizza import PIZZAS, build_pizzeria, whatsapp_number
from test_backend import AUTH, settings


class PizzaEditor:
    def __init__(self):
        self.calls = 0

    async def reply(self, system, messages):
        self.calls += 1
        payload = json.loads(messages[-1]['content'])
        files = dict(payload['current_files'])
        assert files['index.html'].count('data-item=') == 12
        files['index.html'] = files['index.html'].replace('Uma seleção de sabores para apresentar a marca.', 'Sabores artesanais para apresentar a marca.', 1)
        files['styles.css'] += '\n.hero-mark{transform:rotate(7deg)}'
        return {'reply': json.dumps({'summary': 'A introdução e o selo da abertura foram ajustados.', 'files': files})}


def photo(index):
    image = Image.new('RGB', (640 + index, 420), (70 + 12 * index, 30 + index, 20))
    output = io.BytesIO()
    image.save(output, 'JPEG')
    return output.getvalue()


def test_pizza_site_assets_edit_preview_and_complete_export(settings):
    editor = PizzaEditor()
    with TestClient(create_app(settings, editor)) as client:
        created = client.post('/studio/projects', headers=AUTH, json={
            'name': 'Pizzaria Forno Vivo', 'category': 'restaurante',
            'brief': 'Pizzaria artesanal com fotos dos produtos, cardápio e carrinho.',
            'contact': 'WhatsApp (11) 98765-4321',
        }).json()
        identifier = created['id']
        for index, product in enumerate(PIZZAS[:8]):
            data = base64.b64encode(photo(index)).decode()
            uploaded = client.post(f'/studio/projects/{identifier}/assets', headers=AUTH,
                                   json={'name': f'{product[0]}.jpg', 'purpose': 'image', 'data_base64': data})
            assert uploaded.status_code == 200, uploaded.text
            asset = uploaded.json()['assets'][-1]
            linked = client.post(f'/studio/projects/{identifier}/assets/{asset["name"]}/link',
                                 headers=AUTH, json={'product': product[0]})
            assert linked.status_code == 200, linked.text
        first = client.get(f'/studio/projects/{identifier}', headers=AUTH).json()
        assert len(first['assets']) == 8
        assert len({a['sha256'] for a in first['assets']}) == 8
        duplicate = client.post(f'/studio/projects/{identifier}/assets', headers=AUTH,
                                json={'name': 'copy.jpg', 'purpose': 'image', 'data_base64': base64.b64encode(photo(0)).decode()})
        assert duplicate.status_code == 200 and len(duplicate.json()['assets']) == 8
        built = client.post(f'/studio/projects/{identifier}/pizza/build', headers=AUTH, json={'revision': 0})
        assert built.status_code == 200, built.text
        page = built.json()
        assert page['status'] == 'ready' and page['revision'] == 1
        assert page['current']['report']['passed']
        assert all(check['status'] == 'passed' for check in page['current']['report']['requirements'])
        html = page['current']['files']['index.html']
        assert html.count('data-item=') == 12
        assert html.count('data-cart-size') == 12
        assert html.count('src="assets/') >= 8
        assert 'https://wa.me/5511987654321' in html
        assert 'DEMONSTRATIVO' in html and 'exemplos de demonstração' in html
        assert all(f'assets/{a["name"]}' in html for a in page['assets'])
        ticket = client.post(f'/studio/projects/{identifier}/preview', headers=AUTH).json()['url']
        preview = client.get(ticket)
        assert preview.status_code == 200 and 'Pizzaria Forno Vivo' in preview.text
        assert 'data-studio-cart' in preview.text
        changed = client.post(f'/studio/projects/{identifier}/generate', headers=AUTH,
                              json={'mode': 'autonomous', 'prompt': 'Altere o texto da seção de introdução e a rotação do selo para sete graus. Preserve cardápio e carrinho.', 'research_images': False})
        assert changed.status_code == 200, changed.text
        import time
        for _ in range(100):
            changed = client.get(f'/studio/projects/{identifier}', headers=AUTH).json()
            if changed['status'] != 'running':
                break
            time.sleep(.02)
        assert changed['status'] == 'ready', changed.get('error')
        assert changed['revision'] == 2 and editor.calls == 1
        assert changed['current']['files']['index.html'] == html.replace('Uma seleção de sabores para apresentar a marca.', 'Sabores artesanais para apresentar a marca.', 1)
        assert changed['current']['files']['index.html'].count('data-item=') == 12
        assert changed['current']['files']['styles.css'].endswith('.hero-mark{transform:rotate(7deg)}')
        extra = client.post(f'/studio/projects/{identifier}/assets', headers=AUTH,
                            json={'name': 'nova-foto.jpg', 'purpose': 'image', 'data_base64': base64.b64encode(photo(9)).decode()})
        assert extra.status_code == 200, extra.text
        extra_name = extra.json()['assets'][-1]['name']
        exported = client.get(f'/studio/projects/{identifier}/export', headers=AUTH)
        assert exported.status_code == 200
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            paths = archive.namelist()
            assert {'site/index.html', 'site/styles.css', 'site/app.js', 'site/studio-runtime.js',
                    'site/asset-manifest.json', 'LEIA-ANTES-DE-PUBLICAR.txt', 'ABRIR-SITE.bat', 'server.py'} <= set(paths)
            assert all('site/assets/' + a['name'] in paths for a in page['assets'])
            assert 'site/assets/' + extra_name in paths
            manifest = json.loads(archive.read('site/asset-manifest.json'))
            assert len(manifest) == 9 and sum(a['used_in_page'] for a in manifest) == 8
            assert extra_name in {a['name'] for a in json.loads(archive.read('PROJETO.json'))['assets']}
            assert archive.read('site/index.html').count(b'data-item=') == 12


def test_pizza_missing_contact_is_honest_and_rejects_other_business():
    project = {'name': 'Pizzaria Forno Vivo', 'category': 'restaurante', 'brief': 'Pizzaria artesanal', 'contact': '', 'assets': []}
    files, report = build_pizzeria(project)
    assert report['passed']
    assert 'data-cart-whatsapp' not in files['index.html']
    assert 'Informe um WhatsApp autorizado' in files['index.html']
    assert 'src="assets/' not in files['index.html']
    assert whatsapp_number('Fale pelo e-mail: loja@example.com') == ''
    assert whatsapp_number('Telefone comercial: (11) 98765-4321') == ''
    project['name'] = 'Loja de roupas'
    project['brief'] = 'Venda de camisetas'
    import pytest
    with pytest.raises(ValueError):
        build_pizzeria(project)
