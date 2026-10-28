export type VisualSlide = { id: string; title: string; text: string; query: string };

const clean = (value: string) => value
  .replace(/\*\*/g, '')
  .replace(/^\s*(?:[-*]|\d+[.)])\s+/gm, '')
  .replace(/`/g, '')
  .trim();

const generic = /^(?:vis[aã]o geral|contexto|introdu[cç][aã]o|resumo|ideia central|conclus[aã]o|o que voc[eê] precisa saber)$/i;

const namedPhilosophers: Array<[string, string]> = [
  ['socrates','Socrates'],['platao','Plato'],['plato','Plato'],['aristoteles','Aristotle'],['aristotle','Aristotle'],
  ['kant','Immanuel Kant'],['nietzsche','Friedrich Nietzsche'],['descartes','Rene Descartes'],['confucio','Confucius'],
  ['confucius','Confucius'],['maquiavel','Niccolo Machiavelli'],['machiavelli','Niccolo Machiavelli'],['epicuro','Epicurus'],
  ['epicurus','Epicurus'],['dostoievski','Fyodor Dostoevsky'],['dostoevsky','Fyodor Dostoevsky'],['marx','Karl Marx'],
  ['karl marx','Karl Marx'],['simone de beauvoir','Simone de Beauvoir'],['sartre','Jean-Paul Sartre'],['spinoza','Baruch Spinoza'],
  ['santo agostinho','Augustine of Hippo'],['tomás de aquino','Thomas Aquinas'],['thomas aquinas','Thomas Aquinas'],
  ['heraclito','Heraclitus'],['heraclitus','Heraclitus'],['pitagoras','Pythagoras'],['pythagoras','Pythagoras'],
  ['democrito','Democritus'],['democritus','Democritus'],['seneca','Seneca'],['sêneca','Seneca'],
  ['marco aurelio','Marcus Aurelius'],['marcus aurelius','Marcus Aurelius'],['hobbes','Thomas Hobbes'],['thomas hobbes','Thomas Hobbes'],
  ['locke','John Locke'],['john locke','John Locke'],['hume','David Hume'],['david hume','David Hume'],
  ['rousseau','Jean-Jacques Rousseau'],['hegel','Georg Wilhelm Friedrich Hegel'],['kierkegaard','Søren Kierkegaard'],
  ['camus','Albert Camus'],['hannah arendt','Hannah Arendt'],['wittgenstein','Ludwig Wittgenstein'],
  ['foucault','Michel Foucault'],['derrida','Jacques Derrida'],['rawls','John Rawls'],['ayn rand','Ayn Rand'],
  ['laozi','Laozi'],['lao tse','Laozi'],['sun tzu','Sun Tzu'],['rumi','Rumi'],['avicenna','Avicenna'],
  ['ibn sina','Avicenna'],['al-ghazali','Al-Ghazali'],['mencius','Mencius'],
];

const normalized = (value: string) => value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
function imageQuery(topic: string, text: string, title: string) {
  // Prefer the person in the spoken sentence before the overall topic.
  for (const part of [text, title, topic]) {
    const context=normalized(part);
    const match=namedPhilosophers.map(([name,canonical])=>({canonical,index:context.search(new RegExp(`\\b${normalized(name)}\\b`))}))
      .filter(item=>item.index>=0).sort((a,b)=>a.index-b.index)[0];
    if(match)return match.canonical;
  }
  return topic.replace(/\s+/g,' ').trim().slice(0,150);

}

export function visualSlides(reply: string, topic: string): VisualSlide[] {
  const text = reply.trim();
  if (!text) return [{ id: 'overview', title: topic, text: 'Preparando a explicação…', query: topic }];
  const headings = [...text.matchAll(/^#{1,3}\s+(.+)$/gm)];
  let sections: Array<{ title: string; text: string }> = [];
  if (headings.length) {
    sections = headings.slice(0, 12).map((heading, index) => {
      const start = heading.index! + heading[0].length;
      const end = headings[index + 1]?.index ?? text.length;
      return { title: clean(heading[1]), text: clean(text.slice(start, end)) };
    }).filter(section => section.text.length > 30);
  }
  if (!sections.length) sections = [{ title: topic, text }];

  const scenes: Array<{ title: string; text: string }> = [];
  for (const section of sections) {
    const sentences = section.text.split(/(?<=[.!?])\s+(?=[\p{Lu}0-9])/u).map(clean).filter(Boolean);
    const groups: string[][] = [];
    for (let index = 0; index < sentences.length; index++) groups.push(sentences.slice(index, index + 1));
    if (!groups.length) groups.push([section.text]);
    for (let index = 0; index < groups.length; index++) {
      const content = groups[index].join(' ');
      const excerpt = content.split(/[.!?]/, 1)[0].replace(/[,;:].*$/, '').trim();
      const shortExcerpt = excerpt.length > 58 ? `${excerpt.slice(0, 55).trimEnd()}…` : excerpt;
      const title = groups.length === 1 || generic.test(section.title)
        ? section.title
        : index === 0 ? section.title : shortExcerpt || `${section.title} · parte ${index + 1}`;
      scenes.push({ title, text: content });
      if (scenes.length >= 12) break;
    }
    if (scenes.length >= 12) break;
  }
  return scenes.slice(0, 12).map((slide, index) => {
    const title = !slide.title || generic.test(slide.title) ? `${topic} · parte ${index + 1}` : slide.title;
    const query = imageQuery(topic, slide.text, title);
    return { id: `scene-${index}`, title, text: slide.text, query: query || topic };
  });
}

export function spokenSlideIndex(slides: VisualSlide[], spoken: string, fallback = 0): number {
  const words = spoken.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .match(/[\p{L}\p{N}]{4,}/gu) || [];
  if (!words.length) return fallback;
  const stop = new Set(['para', 'como', 'mais', 'essa', 'esse', 'pela', 'pelo', 'sobre', 'entre', 'quando', 'porque', 'tambem', 'senhor', 'agora', 'entao', 'depois']);
  const tokens = [...new Set(words.filter(word => !stop.has(word)))];
  let bestIndex = fallback;
  let bestScore = 0;
  slides.forEach((slide, index) => {
    const content = `${slide.title} ${slide.text}`.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    const score = tokens.reduce((sum, token) => sum + (content.includes(token) ? Math.min(3, Math.floor(content.split(token).length / 2)) : 0), 0);
    if (score > bestScore) { bestScore = score; bestIndex = index; }
  });
  return bestIndex;
}
