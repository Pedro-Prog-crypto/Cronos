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
const spokenLesson='Sócrates viveu em Atenas e questionava as certezas dos cidadãos. Seu método ficou conhecido como diálogo socrático. Ele perguntava para revelar contradições no raciocínio. Foi condenado à morte em 399 antes de Cristo. A acusação dizia que corrompia os jovens. Sócrates aceitou a sentença e bebeu cicuta.';
const spokenScenes=visualSlides(spokenLesson,'Sócrates');
assert(spokenScenes.length===6,'each narrated sentence should become a changing visual scene');
assert(spokenScenes.every(scene=>/socrates/i.test(scene.query)),'each visual scene must search for its subject');
for(let index=0;index<spokenScenes.length;index++){
  const marker=spokenScenes[index].text.split(/[.!?]/,1)[0];
  assert(spokenSlideIndex(spokenScenes,marker,0)===index,`spoken paragraph ${index} did not select its matching scene`);
}
const philosophers=visualSlides('Sócrates questionava os atenienses. Platão fundou a Academia. Aristóteles ensinou Alexandre.', 'Qual filósofo foi mais importante?');
assert(philosophers.length===3,'a multi-philosopher answer should produce one image search per narrated person');
assert(/socrates/i.test(philosophers[0].query),'first philosopher portrait query is not specific');
assert(/plato/i.test(philosophers[1].query),'second philosopher portrait query is not specific');
assert(/aristotle/i.test(philosophers[2].query),'third philosopher portrait query is not specific');
if(scenarios<1200||checks<10000)throw new Error(`Insufficient validation: ${scenarios} scenarios, ${checks} checks`);
console.log(`${scenarios} synthetic narrative scenarios passed; ${checks} assertions passed. These validate chapter splitting, topic-specific media queries, boundary isolation, and narration-to-scene matching; they are not live image-provider/browser end-to-end tests.`);
