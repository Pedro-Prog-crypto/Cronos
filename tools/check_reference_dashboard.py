"""Verify the clean home screen and the functions panel in a disconnected browser."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
    Thread(target=server.serve_forever,daemon=True).start()
    errors=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1440,'height':900})
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/ui/',wait_until='networkidle')
            assert page.get_by_text('EM ESPERA',exact=True).is_visible()
            assert page.locator('.reference-processing,.home-stats,.home-nav,.hologram-deck').count()==0
            page.keyboard.press('Control+Shift+f')
            panel=page.get_by_role('dialog',name='Painel de Funções')
            assert panel.is_visible()
            assert panel.locator('.home-gear-grid button').count()==12
            search=panel.get_by_role('textbox',name='Buscar função ou módulo')
            search.fill('visão')
            assert panel.locator('.home-gear-grid button').count()==1
            panel.get_by_role('button',name='Fechar funções').click()
            assert panel.count()==0
            assert not errors,errors
            browser.close()
    finally:server.shutdown()
    print('Clean home and functions panel checks passed.')
if __name__=='__main__':main()
