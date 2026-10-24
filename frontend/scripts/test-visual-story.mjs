import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const output=mkdtempSync(join(tmpdir(),'cronos-visual-story-'));
execFileSync(join(process.cwd(),'node_modules','.bin','tsc'),['src/visualSlides.ts','--target','ES2022','--module','ES2022','--outDir',output,'--skipLibCheck','--ignoreConfig'],{stdio:'inherit'});
const {visualSlides,spokenSlideIndex}=await import(pathToFileURL(join(output,'visualSlides.js')));
let checks=0,scenarios=0;
const assert=(condition,message)=>{checks++;if(!condition)throw new Error(message);};
const letters=(number)=>{let value='';do{value=String.fromCharCode(65+number%26)+value;number=Math.floor(number/26)-1;}while(number>=0);return value;};
for(let topic=0;topic<200;topic++){
  for(let layout=0;layout<6;layout++){
    const count=2+layout%5;
    const subject=`Assunto ${topic} TEMA_EXCLUSIVO_${letters(topic)}`;
    const markers=Array.from({length:count},(_,chapter)=>`MARCADOR${letters(topic)}CAPITULO${letters(chapter)}`);
    const reply=markers.map((marker,chapter)=>`## Capitulo ${chapter+1}\n\n${marker} apresenta a explicacao detalhada desta etapa, com contexto, evidencia e um exemplo concreto para ajudar a entender o assunto ${letters(topic)}.`).join('\n\n');
    const slides=visualSlides(reply,subject);
    assert(slides.length===count,`scenario ${topic}/${layout}: expected ${count} scenes, got ${slides.length}`);
    assert(new Set(slides.map(scene=>scene.id)).size===count,`scenario ${topic}/${layout}: scene ids are not unique`);
    assert(slides.every(scene=>scene.title.trim().length>0),`scenario ${topic}/${layout}: missing title`);
    assert(slides.every(scene=>scene.text.length>35),`scenario ${topic}/${layout}: missing explanation content`);
    assert(slides.every(scene=>scene.query.includes(subject)),`scenario ${topic}/${layout}: search query lost its topic`);
    assert(slides.every((scene,index)=>scene.text.includes(markers[index])),`scenario ${topic}/${layout}: scene content crossed chapter boundaries`);
    assert(slides.every(scene=>scene.query.length<=150),`scenario ${topic}/${layout}: search query exceeded limit`);
    assert(spokenSlideIndex(slides,`Agora vamos ao ${markers[0]}, que descreve esta etapa`,0)===0,`scenario ${topic}/${layout}: opening narration matched the wrong scene`);
    const middle=Math.floor((count-1)/2);
    assert(spokenSlideIndex(slides,`Agora vamos ao ${markers[middle]}, que descreve esta etapa`,0)===middle,`scenario ${topic}/${layout}: middle narration matched the wrong scene`);
    assert(spokenSlideIndex(slides,`Por fim, analisamos ${markers[count-1]}, que encerra esta etapa`,0)===count-1,`scenario ${topic}/${layout}: final narration matched the wrong scene`);
    scenarios++;
  }
}
if(scenarios<1200||checks<10000)throw new Error(`Insufficient validation: ${scenarios} scenarios, ${checks} checks`);
console.log(`${scenarios} synthetic narrative scenarios passed; ${checks} assertions passed. These validate chapter parsing, topic-specific media queries, boundary isolation, and narration-to-chapter matching; they are not live image-provider/browser end-to-end tests.`);
