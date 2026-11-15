"""Browser check of the filmed layout, with no connected accounts or sample data."""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/visual-audit-r52'

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'cronos')))
    Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox', '--enable-unsafe-swiftshader'])
            page = browser.new_page(viewport={'width': 1440, 'height': 900})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/ui/', wait_until='networkidle')
            page.wait_for_timeout(1800)
            assert page.get_by_text('EM ESPERA', exact=True).is_visible()
            assert page.locator('.reference-core').count() == 0
            assert page.locator('.hologram-deck').count() == 0
            page.screenshot(path=str(OUT / 'idle.png'))
            page.get_by_role('button', name='ABRIR PAINÉIS').click()
            deck = page.get_by_role('region', name='Cards principais do Cronos')
            assert deck.is_visible() and deck.get_attribute('data-mode') == 'focus'
            assert page.locator('.hologram-deck-card').count() == 1
            page.screenshot(path=str(OUT / 'focus.png'))
            page.get_by_role('button', name='Próximo card').click()
            assert page.locator('.hologram-deck-card').count() == 2
            assert page.locator('.hologram-deck-card[data-miniature="true"]').count() == 1
            page.screenshot(path=str(OUT / 'history.png'))
            page.get_by_role('button', name='Card anterior').click()
            assert page.get_by_role('heading', name='Resumo do sistema').first.is_visible()
            page.get_by_role('button', name='Ver todos os cards').click()
            assert deck.get_attribute('data-mode') == 'overview'
            assert page.locator('.hologram-deck-card').count() == 8
            page.wait_for_timeout(650)
            page.screenshot(path=str(OUT / 'overview.png'))
            page.get_by_role('button', name='Mostrar Observações disponíveis').click()
            page.get_by_role('button', name='Ver memória').click()
            assert page.get_by_role('dialog', name='Painel Memória').is_visible()
            page.get_by_role('button', name='Fechar painel').click()
            for width, height, name in [(1024, 768, 'tablet'), (390, 844, 'mobile')]:
                page.set_viewport_size({'width': width, 'height': height})
                page.wait_for_timeout(550)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.get_by_role('button', name='Ativar controle de voz do Cronos').is_visible()
                page.screenshot(path=str(OUT / f'{name}.png'))
                if name == 'mobile':
                    page.get_by_role('button', name='Ver todos os cards').click()
                    page.wait_for_timeout(650)
                    page.screenshot(path=str(OUT / 'mobile-overview.png'))
            assert not errors, errors
            (OUT / 'results.json').write_text(json.dumps({'javascript_errors': errors, 'verified': ['standby without opaque core or cards', 'focus/history/overview transitions', 'memory routing', 'desktop/tablet/mobile without horizontal overflow'], 'data': 'Disconnected; live feeds were not fabricated.'}, indent=2))
            browser.close()
    finally:
        server.shutdown()
    print('Reference dashboard checks passed.')

if __name__ == '__main__':
    main()
