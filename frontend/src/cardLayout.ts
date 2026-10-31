export type CardLayout='orbit'|'left'|'right';
export function cardPositionCommand(text:string):CardLayout|null{
 const value=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim().replace(/^(?:cronos|kronos|chronos)[,\s:]*/,'').replace(/^por favor[,\s]*/,'');
 if(/\b(?:imagem|foto|arquivo|zip|painel|holograma)\b/.test(value)&&!/\b(?:cards?|cartoes|textos?|resposta)\b/.test(value))return null;
 if(!/^(?:(?:eu )?quero que (?:voce |vc )?)?(?:colo[cq]\w*|deix\w*|mov\w*|pux\w*|lev\w*|organiz\w*|distribu\w*)\b/.test(value))return null;
 if(/\bdireit[ao]\b/.test(value))return 'right';
 if(/\besquerd[ao]\b/.test(value))return 'left';
 if(/\b(?:redor|circulo|volta|circular)\b/.test(value))return 'orbit';
 return null;
}
/** Initial orbit only. User movement overrides it rather than snapping back to a slot. */
export function cardHome(index:number,total:number,width:number,height:number,cardWidth:number,cardHeight:number,layout:CardLayout){
 const half=Math.ceil(total/2),side=index<half?-1:1,row=index<half?index:index-half,rows=index<half?half:total-half;
 let x:number,y:number;
 if(layout==='orbit'){
  const theta=rows===1?0:(row/(rows-1)-.5)*1.9;
  x=width*.5+side*Math.cos(theta)*width*.29-cardWidth/2;
  y=height*.44+Math.sin(theta)*height*.36-cardHeight/2;
 }else{
  const cols=total>3?2:1,rowsPer=Math.ceil(total/cols),column=index%cols,line=Math.floor(index/cols);
  const area=width*.47,start=layout==='left'?width*.015:width*.515;
  x=start+column*area/cols+(area/cols-cardWidth)/2;
  y=height*.08+line*height*.76/rowsPer;
 }
 return {x:Math.max(8,Math.min(width-cardWidth-8,x)),y:Math.max(8,Math.min(height-cardHeight-65,y))};
}
