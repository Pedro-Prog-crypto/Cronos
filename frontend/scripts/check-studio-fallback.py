"""Browser check against STUDIO_TEST_FALLBACK=1, with no external provider calls."""
import asyncio
import os

import httpx
from playwright.async_api import async_playwright, expect

BASE = os.getenv('STUDIO_TEST_URL', 'http://127.0.0.1:8879')
AUTH = {'Authorization': 'Bearer studio-test-only'}


async def main():
    async with httpx.AsyncClient(base_url=BASE, headers=AUTH) as client:
        await client.patch('/panels/preferences', json={'device_auto_connect': False, 'proactive_suggestions': False})
        project = (await client.post('/studio/projects', json={'name': 'Reserva automática', 'category': 'hotel', 'brief': 'Hotel com contato e solicitação de horário.'})).json()
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
            page = await browser.new_page(viewport={'width': 1672, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(BASE + '/#cronos-session=studio-test-only')
            await page.get_by_role('button', name='ESTÚDIO DE SITES', exact=True).click()
            await page.get_by_role('button', name='Meus projetos', exact=False).first.click()
            await page.locator('.ss-saved-card').filter(has_text=project['name']).first.click()
            prompt = page.get_by_label('Pedido de alteração do site', exact=True)
            await prompt.fill('Crie este site editorial para o meu hotel.')
            await page.get_by_role('button', name='CRIAR COM IA', exact=True).click()
            await expect(page.get_by_role('alertdialog')).to_contain_text('demais integrações configuradas')
            await page.get_by_role('button', name='CONFIRMAR SOLICITAÇÃO').click()
            await expect(page.locator('.ss-run')).to_contain_text('IA ativa: mistral', timeout=15000)
            assert await page.locator('.ss-job-error').count() == 0
            await expect(page.locator('.ss-run')).to_contain_text('Versão salva', timeout=15000)
            done = (await client.get('/studio/projects/' + project['id'])).json()
            assert done['status'] == 'ready' and done['revision'] == 1 and done['active_provider'] == 'mistral'
            assert not done.get('error') and len(done['history']) == 2
            assert done['last_request'] == 'Crie este site editorial para o meu hotel.'
            calls = (await client.get('/fixture/calls')).json()['adapters']
            assert calls == {'gemini': 1, 'mistral': 2}, calls
            await page.screenshot(path='/tmp/cronos-studio-fallback-recovered.png')
            await prompt.fill('Aguardar cancelamento manual; não continue para outra IA.')
            await page.get_by_role('button', name='GERAR NOVA VERSÃO', exact=True).click()
            await page.get_by_role('button', name='CONFIRMAR SOLICITAÇÃO').click()
            await expect(page.locator('.ss-run')).to_contain_text('IA ativa: mistral', timeout=15000)
            await page.get_by_role('button', name='Cancelar esta criação', exact=True).click()
            cancelled = (await client.get('/studio/projects/' + project['id'])).json()
            assert cancelled['status'] == 'cancelled' and cancelled['revision'] == 1
            await asyncio.sleep(.2)
            calls = (await client.get('/fixture/calls')).json()['adapters']
            assert calls == {'gemini': 1, 'mistral': 3}, calls
            assert not errors, errors
            await browser.close()
    print('PASS: in-app authorization describes reserves; Gemini 429 recovers through Mistral; no intermediate red error; request and revision preserved; manual cancellation does not launch another reserve. Mock adapters only, no live APIs.')


asyncio.run(main())
