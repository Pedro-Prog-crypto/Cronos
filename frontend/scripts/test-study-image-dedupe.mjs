import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const output=mkdtempSync(join(tmpdir(),'cronos-image-dedupe-'));
execFileSync(join(process.cwd(),'node_modules','.bin','tsc'),['src/studyImageDedupe.ts','--target','ES2022','--module','ES2022','--outDir',output,'--skipLibCheck','--ignoreConfig'],{stdio:'inherit'});
const {normalizedImageUrl,normalizedImageTitle,isNearDuplicateHash,selectWallImages,wallGridLayout}=await import(pathToFileURL(join(output,'studyImageDedupe.js')));
const checks=[
  normalizedImageUrl('https://upload.wikimedia.org/a/960px-Socrates.jpg?width=960')===normalizedImageUrl('https://upload.wikimedia.org/a/Socrates.jpg'),
  normalizedImageTitle('Sócrates — Retrato.JPG')===normalizedImageTitle('Socrates retrato.png'),
  isNearDuplicateHash('00000000',['00000001']),
  !isNearDuplicateHash('00000000',['11111111']),
  selectWallImages(['a','b','c','d','e','f','g','h','i'],0,8).length===8,
  new Set(selectWallImages(['a','b','c','d','e','f','g','h','i'],0,8)).size===8,
  selectWallImages(['a','b','c','d','e','f','g','h','i'],1,8)[0]==='g',
  JSON.stringify(wallGridLayout(2))===JSON.stringify({columns:2,rows:1,lastSpan:1}),
  JSON.stringify(wallGridLayout(7))===JSON.stringify({columns:4,rows:2,lastSpan:2}),
];
if(checks.some(check=>!check))throw new Error('Study image deduplication regression: '+checks.map((ok,index)=>`${index+1}:${ok}`).join(', '));
console.log(`${checks.length} study-image deduplication checks passed.`);
