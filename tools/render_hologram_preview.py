"""Record a short browser preview of the compiled idle/listening/speaking orb."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import subprocess

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'releases/Cronos-R54-holograma-preview.mp4'
INJECT = """(() => {
  const NativeWorker=window.Worker;
  window.__orbInput={};
  window.Worker=class extends NativeWorker {
    constructor(...args){super(...args);this.scene=String(args[0]).includes('scene.worker');}
    postMessage(message,transfer){
      if(this.scene&&message.type==='input')message={...message,input:{...message.input,...window.__orbInput}};
      return super.postMessage(message,transfer||[]);
    }
  };
})();"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/connection':
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{}')
            return
        super().do_GET()


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / 'cronos')))
    Thread(target=server.serve_forever, daemon=True).start()
    OUTPUT.parent.mkdir(exist_ok=True)
    try:
        with TemporaryDirectory(prefix='cronos-hologram-preview-') as temp:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox', '--enable-unsafe-swiftshader'])
                context = browser.new_context(viewport={'width': 960, 'height': 600}, device_scale_factor=1)
                context.add_init_script(INJECT)
                page = context.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/ui/', wait_until='networkidle')
                page.wait_for_timeout(1200)
                if page.locator('canvas.filament-glow').get_attribute('data-render-thread') != 'worker':
                    raise RuntimeError('The filmed hologram renderer did not start.')
                number = 0
                for state, level, frames in [('IDLE', 0, 28), ('LISTENING', .35, 28), ('SPEAKING', .55, 28)]:
                    page.evaluate('value=>window.__orbInput=value', {'state': state, 'audio': level})
                    for _ in range(frames):
                        page.wait_for_timeout(75)
                        page.screenshot(path=f'{temp}/{number:04d}.png', animations='disabled')
                        number += 1
                context.close()
                browser.close()
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '12', '-i', f'{temp}/%04d.png', '-c:v', 'libx264', '-crf', '23', '-pix_fmt', 'yuv420p', str(OUTPUT)], check=True)
    finally:
        server.shutdown()
        server.server_close()
    print(f'{OUTPUT} ({OUTPUT.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
