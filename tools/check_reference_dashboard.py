"""Browser check of the filmed layout, with no connected accounts or sample data."""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/visual-audit-r55'

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
            assert not page.locator('.reference-panels-toggle').is_visible()
            assert not page.locator('.home-nav').is_visible()
            assert page.get_by_role('button', name='Ativar controle de voz do Cronos').is_visible()
            assert page.locator('.cronos-quick-actions').count() == 0
            assert page.locator('.cronos-utility-actions').count() == 0
            assert page.locator('canvas.filament-glow').evaluate('(node)=>node.width') == 1080
            page.screenshot(path=str(OUT / 'idle.png'))
            # Show the thinking palette independently of a live voice provider.
            status = page.locator('.reference-voice-status')
            control = page.locator('.reference-voice-control')
            status.evaluate("node=>{node.dataset.state='THINKING';node.querySelector('span').textContent='PENSANDO'}")
            control.evaluate("node=>node.dataset.state='THINKING'")
            assert page.get_by_text('PENSANDO', exact=True).is_visible()
            page.screenshot(path=str(OUT / 'thinking.png'))
            status.evaluate("node=>{node.dataset.state='IDLE';node.querySelector('span').textContent='EM ESPERA'}")
            control.evaluate("node=>node.dataset.state='IDLE'")
            # The hidden DOM trigger exercises the same state change as the spoken command.
            page.locator('.reference-panels-toggle').evaluate('(node)=>node.click()')
            deck = page.get_by_role('region', name='Cards principais do Cronos')
            assert deck.is_visible() and deck.get_attribute('data-mode') == 'focus'
            assert page.locator('.hologram-deck-card').count() == 1
            page.wait_for_timeout(600)
            page.screenshot(path=str(OUT / 'focus.png'))
            page.get_by_role('button', name='Próximo card').click()
            assert page.locator('.hologram-deck-card').count() == 2
            assert page.locator('.hologram-deck-card[data-miniature="true"]').count() == 1
            assert 'NÃO CONECTADO' in page.locator('.deck-weather-visual').inner_text()
            page.screenshot(path=str(OUT / 'history.png'))
            page.get_by_role('button', name='Card anterior').click()
            assert page.get_by_role('heading', name='Resumo do sistema').first.is_visible()
            page.get_by_role('button', name='Ver todos os cards').click()
            assert deck.get_attribute('data-mode') == 'overview'
            assert page.locator('.hologram-deck-card').count() == 8
            assert page.locator('.deck-news-visual img').count() == 3
            assert page.locator('.deck-news-visual img').evaluate_all('(images)=>images.every(image=>image.complete&&image.naturalWidth>0)')
            page.wait_for_timeout(650)
            page.screenshot(path=str(OUT / 'overview.png'))
            page.get_by_role('button', name='Mostrar Observações disponíveis').click()
            page.get_by_role('button', name='Ver memória').click()
            assert page.get_by_role('dialog', name='Painel Memória').is_visible()
            page.get_by_role('button', name='Fechar painel').click()
            page.locator('.home-nav button[aria-label="Sistema"]').evaluate('(node)=>node.click()')
            assert page.get_by_role('dialog', name='Painel Sistema').is_visible()
            page.screenshot(path=str(OUT / 'system.png'))
            page.get_by_role('button', name='Fechar painel').click()
            page.locator('.reference-panels-toggle').evaluate('(node)=>node.click()')
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
