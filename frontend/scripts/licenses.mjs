import {mkdir, copyFile, cp} from 'node:fs/promises';
const destination=new URL('../../cronos/ui/licenses/',import.meta.url);
await mkdir(destination,{recursive:true});
for(const [packageName,file] of [['react','LICENSE'],['react-dom','LICENSE'],['lucide-react','LICENSE'],['@fontsource/plus-jakarta-sans','LICENSE'],['@fontsource/space-grotesk','LICENSE'],['@fontsource/jetbrains-mono','LICENSE']]){
 const source=new URL('../node_modules/'+packageName+'/'+file,import.meta.url);
 await copyFile(source,new URL(packageName.replaceAll('/','-')+'.txt',destination));
}

await cp(new URL('../node_modules/cesium/Build/Cesium/',import.meta.url),new URL('../../cronos/ui/cesium/',import.meta.url),{recursive:true});
await copyFile(new URL('../src/vendor/gods-eye/LICENSE',import.meta.url),new URL('gods-eye-view.txt',destination));
await copyFile(new URL('../node_modules/cesium/LICENSE.md',import.meta.url),new URL('cesium.txt',destination));

for(const name of ['ThirdParty.json','ThirdParty.extra.json'])await copyFile(new URL('../node_modules/cesium/'+name,import.meta.url),new URL('cesium-'+name,destination));
