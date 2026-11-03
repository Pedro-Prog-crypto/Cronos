"""Browser acceptance for the real pizzeria preview and exported files.

Runs against studio-fixture-server.py. No external model or image API is called.
"""
import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx
from PIL import Image
from playwright.async_api import async_playwright, expect


BASE = os.getenv('STUDIO_TEST_URL', 'http://127.0.0.1:8923')
AUTH = {'Authorization': 'Bearer studio-test-only'}
SCREENSHOTS = Path(__file__).resolve().parents[2] / 'outputs'


def photo(index):
    image = Image.new('RGB', (920, 720), (95 + index * 12, 33 + index * 4, 25 + index * 3))
    output = io.BytesIO()
    image.save(output, 'JPEG')
    return output.getvalue()


async def main():
    async with httpx.AsyncClient(base_url=BASE, headers=AUTH, timeout=30) as client:
        response = await client.post('/studio/projects', json={
            'name': 'Pizzaria Forno Vivo', 'category': 'restaurante',
            'brief': 'Pizzaria artesanal com cardápio, fotos dos produtos e carrinho de demonstração.',
            'contact': 'WhatsApp (11) 98765-4321',
        })
        assert response.status_code == 200, response.text
        project = response.json()
        ids = ['margherita', 'calabresa', 'quatro-queijos', 'portuguesa', 'frango-catupiry', 'pepperoni', 'napolitana', 'vegetariana']
        for index, product in enumerate(ids):
            uploaded = await client.post(f'/studio/projects/{project["id"]}/assets', json={
                'name': product + '.jpg', 'purpose': 'image', 'data_base64': base64.b64encode(photo(index)).decode(),
            })
            assert uploaded.status_code == 200, uploaded.text
            asset = uploaded.json()['assets'][-1]
            linked = await client.post(f'/studio/projects/{project["id"]}/assets/{asset["name"]}/link', json={'product': product})
            assert linked.status_code == 200, linked.text
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
            app = await browser.new_page(viewport={'width': 1440, 'height': 900})
            app_errors = []
            app.on('pageerror', lambda error: app_errors.append(str(error)))
            await app.goto(BASE + '/#cronos-session=studio-test-only')
            if await app.get_by_role('button', name='Depois', exact=True).count():
                await app.get_by_role('button', name='Depois', exact=True).click()
            await app.get_by_role('button', name='Iniciar ditado longo').click()
            await app.get_by_role('button', name='Finalizar ditado longo').click()
            await app.locator('#chat-input').fill('abrir estúdio de sites')
            await app.get_by_role('button', name='Enviar mensagem').click()
            await expect(app.get_by_role('dialog', name='Estúdio de Sites')).to_be_visible()
            await app.get_by_role('button', name='Meus projetos', exact=False).first.click()
            await app.locator('.ss-saved-card').filter(has_text='Pizzaria Forno Vivo').first.click()
            await app.get_by_role('tab', name='Imagens e 3D').click()
            await expect(app.get_by_role('button', name='MONTAR PIZZARIA FUNCIONAL')).to_be_visible()
            await app.get_by_role('button', name='MONTAR PIZZARIA FUNCIONAL').click()
            await expect(app.locator('.ss-badge')).to_contain_text('v1')
            await expect(app.locator('.ss-frame-space iframe')).to_be_visible()
            built = (await client.get('/studio/projects/' + project['id'])).json()
            assert built['revision'] == 1 and built['current']['report']['passed']
            assert not app_errors, app_errors
            preview = (await client.post(f'/studio/projects/{project["id"]}/preview')).json()['url']
            for width, height, name in [(390, 844, 'mobile'), (768, 1024, 'tablet'), (1440, 900, 'desktop')]:
                page = await browser.new_page(viewport={'width': width, 'height': height})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                await page.goto(BASE + preview)
                await expect(page.locator('[data-item]')).to_have_count(12)
                await expect(page.locator('.gallery-tile img')).to_have_count(8)
                await expect(page.locator('.gallery-tile img').first).to_have_js_property('complete', True)
                assert await page.locator('.gallery-tile img').first.evaluate('(img) => img.naturalWidth > 0')
                assert await page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2'), name
                await expect(page.locator('[data-cart-whatsapp]')).to_have_attribute('aria-disabled', 'true')
                await page.locator('[data-item="margherita"] [data-cart-add]').click()
                await page.locator('[data-item="margherita"] [data-cart-size]').select_option('grande')
                await page.locator('[data-item="margherita"] [data-cart-add]').click()
                await expect(page.locator('[data-cart-count]')).to_have_text('2')
                await expect(page.locator('[data-cart-total]')).to_have_text('R$\u00a097,80')
                await page.locator('[data-cart-notes]').fill('sem cebola')
                link = await page.locator('[data-cart-whatsapp]').get_attribute('href')
                await expect(page.locator('[data-cart-whatsapp]')).to_have_attribute('aria-disabled', 'false')
                assert link.startswith('https://wa.me/5511987654321?text=') and 'sem%20cebola' in link
                assert not errors, (name, errors)
                if name != 'tablet':
                    SCREENSHOTS.mkdir(exist_ok=True)
                    await page.screenshot(path=str(SCREENSHOTS / f'studio-pizzaria-{name}.png'), full_page=True)
                await page.close()
            exported = await client.get(f'/studio/projects/{project["id"]}/export')
            assert exported.status_code == 200
            with tempfile.TemporaryDirectory(prefix='cronos-pizza-export-') as directory:
                with zipfile.ZipFile(io.BytesIO(exported.content)) as package:
                    package.extractall(directory)
                process = subprocess.Popen([sys.executable, 'server.py', '--port', '8934'], cwd=directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    for _ in range(70):
                        try:
                            async with httpx.AsyncClient() as checker:
                                if (await checker.get('http://127.0.0.1:8934/')).status_code == 200:
                                    break
                        except httpx.HTTPError:
                            pass
                        await asyncio.sleep(.1)
                    export_page = await browser.new_page(viewport={'width': 390, 'height': 844})
                    export_errors = []
                    export_page.on('pageerror', lambda error: export_errors.append(str(error)))
                    await export_page.goto('http://127.0.0.1:8934/')
                    await expect(export_page.locator('.gallery-tile img')).to_have_count(8)
                    await export_page.locator('[data-item="calabresa"] [data-cart-size]').select_option('grande')
                    await export_page.locator('[data-item="calabresa"] [data-cart-add]').click()
                    await expect(export_page.locator('[data-cart-total]')).to_have_text('R$\u00a061,90')
                    assert 'Calabresa' in await export_page.locator('[data-cart-whatsapp]').get_attribute('href')
                    assert not export_errors, export_errors
                    await export_page.close()
                finally:
                    process.terminate()
                    process.wait(timeout=5)
            await browser.close()
        print('PASS: UI build, 8 photographs, 12 products, 3 browser widths, size pricing, cart, WhatsApp, exported server and images.')


asyncio.run(main())
