import {createBrowserViteConfig} from './build/vite.js';
export default {...createBrowserViteConfig({command:'build'}),base:'/eye/',build:{outDir:'../../cronos/eye-ui',emptyOutDir:true,chunkSizeWarningLimit:2000}};
