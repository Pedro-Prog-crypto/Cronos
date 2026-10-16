"""Open an exported fixture site on its own real HTTP server and submit real forms."""
import asyncio,hashlib,io,json,os,sys,tempfile,threading,zipfile
from pathlib import Path,PurePosixPath
import httpx
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from cronos.studio.runtime import Handler
from http.server import ThreadingHTTPServer
BASE=os.getenv('STUDIO_TEST_URL','http://127.0.0.1:8871')
AUTH={'Authorization':'Bearer studio-test-only'}


async def main():
 async with httpx.AsyncClient(base_url=BASE,headers=AUTH) as client:
  entries=(await client.get('/studio/projects')).json()['projects']
  project=next(p for p in entries if p['revision']>=2)
  prefix='/studio/projects/'+project['id']
  # The main integration creates a GLB revision, then restores the original.
  restored=await client.post(prefix+'/restore',json={'revision':2});restored.raise_for_status()
  response=await client.get(prefix+'/export');response.raise_for_status()
  with tempfile.TemporaryDirectory(prefix='cronos-export-test-') as folder:
   root=Path(folder)
   with zipfile.ZipFile(io.BytesIO(response.content)) as package:
    assert hashlib.sha256(package.read('server.py')).digest()==hashlib.sha256((ROOT/'cronos/studio/runtime.py').read_bytes()).digest()
    for info in package.infolist():assert not PurePosixPath(info.filename).is_absolute() and '..' not in PurePosixPath(info.filename).parts
    package.extractall(root)
   (root/'private').mkdir()
   server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.site_root=root/'site';server.database=root/'private/contacts.sqlite3'
   server.csrf='export-csrf-test-only';server.hostnames={'localhost','127.0.0.1'};server.rates={};server.rate_lock=threading.Lock()
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    async with async_playwright() as p:
     browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--use-angle=swiftshader-webgl','--enable-unsafe-swiftshader'],headless=True)
     page=await browser.new_page(viewport={'width':1280,'height':900});errors=[];blocked=[]
     page.on('pageerror',lambda e:errors.append(str(e)))
     page.on('console',lambda m:blocked.append(m.text) if 'Refused to' in m.text or 'violates the following Content Security' in m.text else None)
     await page.goto(f'http://127.0.0.1:{server.server_port}/')
     await expect(page.locator('[data-studio-model] canvas')).to_be_visible(timeout=15000)
     await expect(page.get_by_role('slider',name='Separação dos objetos existentes no GLB')).to_be_enabled()
     await page.get_by_role('slider',name='Separação dos objetos existentes no GLB').fill('40')
     form=page.locator('form[data-studio-form="contact"]')
     await form.locator('[name=name]').fill('Contato de exportação')
     await form.locator('[name=email]').fill('export@example.com')
     await form.locator('[name=message]').fill('Este contato foi gravado no servidor exportado.')
     await form.locator('[name=consent]').check()
     await form.get_by_role('button',name='Enviar mensagem').click()
     await expect(form.locator('[data-form-status]')).to_contain_text('Solicitação registrada')
     import sqlite3
     with sqlite3.connect(server.database) as db:
      assert db.execute('SELECT count(*) FROM submissions').fetchone()[0]==1
      assert 'Contato de exportação' in db.execute('SELECT payload FROM submissions').fetchone()[0]
     await page.set_viewport_size({'width':390,'height':844})
     assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
     await page.screenshot(path='/tmp/cronos-exported-site-mobile.png')
     assert not errors,errors
     assert not blocked,blocked
     await browser.close()
     print('PASS: exported site runs independently, CSP holds, real browser CSRF/session/contact persistence works, local GLB loads and interacts, and mobile has no horizontal overflow. Test builder only.')
   finally:server.shutdown();server.server_close();thread.join(timeout=2)
asyncio.run(main())
