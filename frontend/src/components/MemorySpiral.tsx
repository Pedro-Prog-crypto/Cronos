import React,{useMemo,useState} from 'react';
export type MemoryNode={path:string;title:string};
export type MemoryGraph={nodes:MemoryNode[];edges:{source:string;target:string}[];total:number};
function hash(value:string){let number=2166136261;for(const char of value){number=Math.imul(number^char.charCodeAt(0),16777619);}return number>>>0;}
export const MemorySpiral=React.memo(function MemorySpiral({graph,onSelect,small=false}:{graph:MemoryGraph;onSelect:(path:string)=>void;small?:boolean}){
  const [zoom,setZoom]=useState(1);
  const degrees=useMemo(()=>{const values=new Map<string,number>();for(const edge of graph.edges){values.set(edge.source,(values.get(edge.source)||0)+1);values.set(edge.target,(values.get(edge.target)||0)+1);}return values;},[graph.edges]);
  const positions=useMemo(()=>{
    const ordered=[...graph.nodes].sort((a,b)=>a.path.localeCompare(b.path,'pt-BR',{numeric:true}));
    const hubs=ordered.filter(node=>(degrees.get(node.path)||0)>3).sort((a,b)=>(degrees.get(b.path)||0)-(degrees.get(a.path)||0)).slice(0,9);
    const hubIndex=new Map(hubs.map((node,index)=>[node.path,index]));
    const groupCount=Math.max(1,hubs.length||Math.min(9,Math.ceil(ordered.length/20)));
    const groups=new Map<string,number>();
    for(const edge of graph.edges){if(hubIndex.has(edge.source))groups.set(edge.target,hubIndex.get(edge.source)!);if(hubIndex.has(edge.target))groups.set(edge.source,hubIndex.get(edge.target)!);}
    const counts=new Map<number,number>();
    return new Map(ordered.map((node,index)=>{
      const group=hubIndex.get(node.path)??groups.get(node.path)??Math.min(groupCount-1,Math.floor(index/Math.max(1,Math.ceil(ordered.length/groupCount))));
      const angle=group/groupCount*Math.PI*2-.35;
      const cx=460+Math.cos(angle)*285,cy=430+Math.sin(angle)*290;
      const local=counts.get(group)||0;counts.set(group,local+1);
      const h=hash(node.path);const phase=local*2.39996;const radius=hubIndex.has(node.path)?0:24+Math.sqrt(local)*15;
      return [node.path,{x:cx+Math.cos(phase)*Math.min(115,radius),y:cy+Math.sin(phase)*Math.min(115,radius),node,size:Math.min(12,4+Math.sqrt(degrees.get(node.path)||0))}];
    }));
  },[graph.nodes,graph.edges,degrees]);
  const visible=[...positions.values()].filter(p=>Math.abs((p.x-460)*zoom)<455&&Math.abs((p.y-430)*zoom)<425).slice(0,1200);
  const shown=new Set(visible.map(p=>p.node.path));
  return <svg className={`memory-spiral ${small?'memory-small':''}`} viewBox="0 0 920 860" aria-label={`Memória Obsidian: ${graph.total} notas reais`} onWheel={event=>{if(!small)setZoom(value=>Math.max(.6,Math.min(4,value*(event.deltaY>0?.9:1.1))));}}>
    <defs>
      <radialGradient id="memory-aura"><stop stopColor="#bafaff"/><stop offset=".2" stopColor="#00d9ff" stopOpacity=".8"/><stop offset="1" stopColor="#008bff" stopOpacity="0"/></radialGradient>
      <filter id="memory-bloom" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.2"/></filter>
      <symbol id="memory-light" viewBox="-12 -12 24 24"><circle r="12" fill="url(#memory-aura)"/><circle r="1.8" fill="#e9ffff"/></symbol>
    </defs>
    <g className="memory-flow" opacity=".75">
      {Array.from({length:28},(_,index)=>{const a=index/28*Math.PI*2;const x=460+Math.cos(a)*420,y=430+Math.sin(a)*390;return <path key={index} d={`M 920 430 C 660 430 560 430 460 430 C ${460+Math.cos(a+.8)*180} ${430+Math.sin(a+.8)*180} ${460+Math.cos(a+.3)*330} ${430+Math.sin(a+.3)*330} ${x} ${y}`} fill="none" stroke={index%4?'#00b9ed':'#93f9ff'} strokeWidth={index%4?.9:1.7}/>;})}
      {Array.from({length:12},(_,index)=>{const a=index/12*Math.PI*2;const x=460+Math.cos(a)*420,y=430+Math.sin(a)*390;return <circle key={'photon'+index} r="1.7" fill="#baffff"><animateMotion dur={`${8+index%4}s`} repeatCount="indefinite" path={`M 920 430 C 660 430 560 430 460 430 C ${460+Math.cos(a+.8)*180} ${430+Math.sin(a+.8)*180} ${460+Math.cos(a+.3)*330} ${430+Math.sin(a+.3)*330} ${x} ${y}`}/></circle>;})}
    </g>
    <g transform={`translate(460 430) scale(${zoom}) translate(-460 -430)`}>
      <g stroke="#16d9ff" strokeWidth=".8" opacity=".7">{graph.edges.filter(e=>shown.has(e.source)&&shown.has(e.target)).map(edge=>{const a=positions.get(edge.source)!,b=positions.get(edge.target)!;return <path key={edge.source+'|'+edge.target} d={`M ${a.x} ${a.y} Q ${(a.x+b.x)/2+40} ${(a.y+b.y)/2-40} ${b.x} ${b.y}`} fill="none"/>;})}</g>
      {visible.map(({x,y,node,size})=><g key={node.path} transform={`translate(${x} ${y})`} role="button" tabIndex={small?-1:0} aria-label={node.title} onClick={()=>onSelect(node.path)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(node.path);}}} className="memory-node">
        <title>{node.title}</title><use href="#memory-light" x="-14" y="-14" width="28" height="28"/><circle r={size} fill="#031b30" stroke="#76f4ff" strokeWidth="1"/><path d="M -2 -2 H 2 M -2 0 H 2 M -2 2 H 2" stroke="#9dffff" strokeWidth=".65"/><circle r="10" fill="transparent"/>
      </g>)}
    </g>
    <circle cx="460" cy="430" r="38" fill="url(#memory-aura)" className="memory-center-light"/>
  </svg>;
});
