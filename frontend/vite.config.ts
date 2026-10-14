import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import {defineConfig} from 'vite';

export default defineConfig({
  base: '/ui/',
  plugins: [react(), tailwindcss()],
  worker:{format:'es'},
  build: {assetsInlineLimit:0,outDir: '../cronos/ui', emptyOutDir: true, rolldownOptions:{input:{main:'index.html',world:'world.html'}}},
  server: {host: '127.0.0.1', port: 3000, proxy: {
    '/chat': 'http://127.0.0.1:8003', '/status': 'http://127.0.0.1:8003',
    '/voice': 'http://127.0.0.1:8003', '/monitor': 'http://127.0.0.1:8003',
    '/modules': 'http://127.0.0.1:8003', '/tests': 'http://127.0.0.1:8003',
    '/static': 'http://127.0.0.1:8003', '/conversations': 'http://127.0.0.1:8003',
    '/memory': 'http://127.0.0.1:8003', '/world': 'http://127.0.0.1:8003',
    '/tools': 'http://127.0.0.1:8003'
  }}
});
