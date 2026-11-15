/** Viewport geometry: a filmed camera's zoom is not part of the UI animation. */
export function deckPlacement(slot:number,total:number,active:boolean,overview:boolean,width:number,height:number){
 const cardWidth=Math.min(450,width-36),cardHeight=Math.min(256,Math.max(190,height*.30));
 if(active)return {cardWidth,cardHeight,x:0,y:0,scale:1};
 if(overview){
  // Small screens need legible cards and touch targets; a single row only works on wide video frames.
  const columns=width<700?2:Math.min(4,total),rows=Math.ceil(total/columns);
  const column=slot%columns,row=Math.floor(slot/columns);
  const cellWidth=Math.min(220,(width-32)/columns),cellHeight=Math.min(162,(height-220)/Math.max(1,rows));
  const scale=Math.min(.59,(cellWidth-12)/cardWidth,(cellHeight-12)/cardHeight);
  return {cardWidth,cardHeight,x:(column-(columns-1)/2)*cellWidth,y:(row-(rows-1)/2)*cellHeight,scale};
 }
 const spacing=Math.min(width<700?116:166,(width-32)/Math.max(1,total));
 return {cardWidth,cardHeight,x:(slot-(total-1)/2)*spacing,y:Math.min(205,Math.max(132,height*.215)),scale:Math.min(.46,spacing/cardWidth*.91)};
}
const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
/** Locate the start of a playing TTS chunk; never estimate speech with a timer. */
export function spokenSectionIndex(sections:readonly {title:string;body:string}[],chunk:string):number|null{
 const words=normalize(chunk).split(' ').filter(Boolean);
 for(const size of [12,8,5,3]){
  if(words.length<size)continue;
  const phrase=words.slice(0,size).join(' ');
  const candidates=sections.map((s,i)=>({i,text:normalize(`${s.title} ${s.body}`)})).filter(s=>s.text.includes(phrase));
  if(candidates.length===1)return candidates[0].i;
 }
 return null;
}
