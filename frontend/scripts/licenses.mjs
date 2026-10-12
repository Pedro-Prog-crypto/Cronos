import {mkdir, copyFile} from 'node:fs/promises';
const destination=new URL('../../cronos/ui/licenses/',import.meta.url);
await mkdir(destination,{recursive:true});
for(const [packageName,file] of [['react','LICENSE'],['react-dom','LICENSE'],['lucide-react','LICENSE'],['@fontsource/plus-jakarta-sans','LICENSE'],['@fontsource/space-grotesk','LICENSE'],['@fontsource/jetbrains-mono','LICENSE']]){
 const source=new URL('../node_modules/'+packageName+'/'+file,import.meta.url);
 await copyFile(source,new URL(packageName.replaceAll('/','-')+'.txt',destination));
}
