import {build} from 'vite';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
await build({configFile:false,root,logLevel:'warn',build:{outDir:'../cronos/studio',emptyOutDir:false,lib:{entry:root+'/src/studioProduct3D.js',name:'CronosProduct3D',formats:['iife'],fileName:()=> 'product-3d.js'},minify:true,sourcemap:false}});

const output=new URL('../../cronos/studio/product-3d.js',import.meta.url);
const license=await readFile(new URL('../node_modules/three/LICENSE',import.meta.url),'utf8');
await writeFile(output,'/*! Three.js\n'+license+' */\n'+(await readFile(output,'utf8')).replace(/[ \t]+$/gm,''));
