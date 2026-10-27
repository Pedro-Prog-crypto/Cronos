import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const output=mkdtempSync(join(tmpdir(),'cronos-image-dedupe-'));
execFileSync(join(process.cwd(),'node_modules','.bin','tsc'),['src/studyImageDedupe.ts','--target','ES2022','--module','ES2022','--outDir',output,'--skipLibCheck','--ignoreConfig'],{stdio:'inherit'});
const {normalizedImageUrl,normalizedImageTitle,isNearDuplicateHash,partitionWallImages}=await import(pathToFileURL(join(output,'studyImageDedupe.js')));
const checks=[
  normalizedImageUrl('https://upload.wikimedia.org/a/960px-Socrates.jpg?width=960')===normalizedImageUrl('https://upload.wikimedia.org/a/Socrates.jpg'),
  normalizedImageTitle('Sócrates — Retrato.JPG')===normalizedImageTitle('Socrates retrato.png'),
  isNearDuplicateHash('00000000',['00000001']),
  !isNearDuplicateHash('00000000',['11111111']),
  isNearDuplicateHash('00000000',['00000001'],1),
  !isNearDuplicateHash('00000000',['00000111'],1),
  partitionWallImages(Array.from({length:36},(_,index)=>index),0,4).length===4,
  partitionWallImages(Array.from({length:36},(_,index)=>index),0,4).every(row=>row.length===9),
  new Set(partitionWallImages(Array.from({length:36},(_,index)=>index),0,4).flat()).size===36,
  partitionWallImages(['a','b','c','d','e','f','g','h'],0,4).flat().length===8,
  partitionWallImages(['a','b','c','d','e','f','g','h'],1,4).flat()[0]==='b',
];
if(checks.some(check=>!check))throw new Error('Study image deduplication regression: '+checks.map((ok,index)=>`${index+1}:${ok}`).join(', '));
let matrixChecks=0;
for(let count=1;count<=38;count++)for(let offset=0;offset<50;offset++){
 const input=Array.from({length:count},(_,index)=>index),rows=partitionWallImages(input,offset,4),flat=rows.flat();
 const unique=new Set(flat),smallest=Math.floor(count/4),largest=Math.ceil(count/4);
 const balanced=rows.every(row=>row.length>=smallest&&row.length<=largest);
 const expectedFirst=input[offset%count];
 if(flat.length!==count||unique.size!==count||!balanced||flat[0]!==expectedFirst){
  throw new Error(`Image wall partition failed for ${count} images at rotation ${offset}.`);
 }
 matrixChecks++;
}
console.log(`${checks.length+matrixChecks} study-image checks passed (${matrixChecks} partition scenarios).`);
