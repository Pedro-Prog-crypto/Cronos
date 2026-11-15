"""Exercise the state-specific motion in the compiled hologram."""
import json
import io
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from PIL import Image
from playwright.sync_api import sync_playwright
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/visual-audit-r57'
INPUT=r"""(() => {
 const NativeWorker=window.Worker;
 window.__orbInput={};
 window.Worker=class extends NativeWorker {
  constructor(...args){super(...args);this.scene=String(args[0]).includes('scene.worker');}
  postMessage(message,transfer){if(this.scene&&message.type==='input')message={...message,input:{...message.input,...window.__orbInput}};return super.postMessage(message,transfer||[]);}
 };
})();"""

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path=='/connection':
            self.send_response(401);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{}');return
        super().do_GET()

def pixels(canvas):
    return np.asarray(Image.open(io.BytesIO(canvas.screenshot()))).astype(float)

def motion(page):
    canvas=page.locator('canvas.filament-glow')
    first=pixels(canvas);page.wait_for_timeout(550);second=pixels(canvas)
    h,w=second.shape[:2];y,x=np.mgrid[:h,:w];radius=np.hypot(x-w/2,y-h/2)/w
    ring=(radius>.22)&(radius<.43)
    difference=float(np.abs(first-second)[ring].mean())
    light=int(((second[:,:,1]>80)&(second[:,:,2]>130)&ring).sum())
    assert difference>.15 and light>100,(difference,light)
    return {'motion_mean_absolute_difference':round(difference,3),'cyan_ring_pixels':light}

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
    Thread(target=server.serve_forever,daemon=True).start()
    errors=[];checks=[];performance={}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--enable-unsafe-swiftshader'])
            context=browser.new_context(viewport={'width':1440,'height':900})
            context.add_init_script(INPUT)
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/ui/',wait_until='networkidle')
            page.wait_for_timeout(1500)
            assert page.locator('canvas.filament-glow').get_attribute('data-render-thread')=='worker'
            for state,level in [('IDLE',0),('LISTENING',.4),('SPEAKING',.55)]:
                page.evaluate('value=>window.__orbInput=value',{'state':state,'audio':level})
                page.wait_for_timeout(600)
                checks.append({'state':state,**motion(page)})
                page.screenshot(path=str(OUT/f'motion-{state.lower()}.png'))
            orb_worker=next(worker for worker in page.workers if 'scene.worker' in worker.url)
            performance=orb_worker.evaluate('self.__cronosOrbDiagnostics')
            assert not errors,errors
            context.close()
            browser.close()
    finally:
        server.shutdown();server.server_close()
    (OUT/'motion-results.json').write_text(json.dumps({'checks':checks,'worker_performance':performance,'javascript_errors':errors,'limitations':'Controlled states and audio levels; no physical microphone or remote voice provider.'},indent=2))
    print(json.dumps({'checks':checks,'worker_performance':performance}))

if __name__=='__main__':main()
