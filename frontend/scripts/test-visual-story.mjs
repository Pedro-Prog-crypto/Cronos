import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const output=mkdtempSync(join(tmpdir(),'cronos-visual-story-'));
execFileSync(join(process.cwd(),'node_modules','.bin','tsc'),['src/visualSlides.ts','--target','ES2022','--module','ES2022','--outDir',output,'--skipLibCheck','--ignoreConfig'],{stdio:'inherit'});
const {visualSlides,spokenSlideIndex}=await import(pathToFileURL(join(output,'visualSlides.js')));
let checks=0;
const letters=(number)=>{let value='';do{value=String.fromCharCode(65+number%26)+value;number=Math.floor(number/26)-1;}while(number>=0);return value;};
for(let topic=0;topic<100;topic++){
  for(let layout=0;layout<5;layout++){
    const count=2+layout;
    const subject=`Assunto ${topic} TOPICO_UNICO_${topic}`;
    const reply=Array.from({length:count},(_,chapter)=>`## Capitulo ${chapter+1}\n\nMARCADOR${letters(topic)}CAPITULO${letters(chapter)} apresenta a explicacao detalhada desta etapa, com contexto, evidencia e um exemplo concreto para ajudar a entender.`).join('\n\n');
    const slides=visualSlides(reply,subject);
    if(slides.length!==count)throw new Error(`topic ${topic}: expected ${count} scenes, got ${slides.length}`);checks++;
    for(let chapter=0;chapter<count;chapter++){
      const scene=slides[chapter];
      if(!scene.title||scene.text.length<35||!scene.query.includes(subject))throw new Error(`topic ${topic}, scene ${chapter}: incomplete scene fields`);checks++;
      const index=spokenSlideIndex(slides,`Agora vamos ao MARCADOR${letters(topic)}CAPITULO${letters(chapter)}, que descreve esta etapa`,0);
      if(index!==chapter)throw new Error(`topic ${topic}: narration matched scene ${index}, expected ${chapter}`);checks++;
    }
  }
}
if(checks<500)throw new Error(`Expected at least 500 checks, got ${checks}`);
console.log(`${checks} checks passed: scene extraction, titles/content/queries, and narration-to-scene matching.`);
