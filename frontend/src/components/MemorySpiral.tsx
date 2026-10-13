import React,{useMemo,useState,useRef} from 'react';
export type MemoryNode={path:string;title:string};
export type MemoryGraph={nodes:MemoryNode[];edges:{source:string;target:string}[];total:number};
function hash(value:string){let number=2166136261;for(const char of value){number=Math.imul(number^char.charCodeAt(0),16777619);}return number>>>0;}
export const MemorySpiral=React.memo(function MemorySpiral({graph,onSelect,small=false}:{graph:MemoryGraph;onSelect:(path:string)=>void;small?:boolean}){
  const [zoom,setZoom]=useState(1);
  const indices=useRef(new Map<string,number>());
  const degrees=useMemo(()=>{const values=new Map<string,number>();for(const edge of graph.edges){values.set(edge.source,(values.get(edge.source)||0)+1);values.set(edge.target,(values.get(edge.target)||0)+1);}return values;},[graph.edges]);
  const positions=useMemo(()=>{
    const ordered=[...graph.nodes].sort((a,b)=>a.path.localeCompare(b.path,'pt-BR',{numeric:true}));
    if(!ordered.length)indices.current.clear();
    return new Map(ordered.map(node=>{
      if(!indices.current.has(node.path))indices.current.set(node.path,indices.current.size);
      const index=indices.current.get(node.path)!;
      const arm=index%5,turn=Math.floor(index/5),angle=arm*Math.PI*2/5+turn*.22;
      const radius=12+Math.sqrt(turn)*28,jitter=(hash(node.path)%13)-6;
      return [node.path,{x:460+Math.cos(angle)*(radius+jitter),y:430+Math.sin(angle)*(radius+jitter),node,size:Math.min(2.6,1.1+Math.sqrt(degrees.get(node.path)||0)*.12)}];
    }));
  },[graph.nodes,graph.edges,degrees]);
  if(!graph.nodes.length)return null;
  const visible=[...positions.values()].filter(p=>Math.abs((p.x-460)*zoom)<455&&Math.abs((p.y-430)*zoom)<425).slice(0,1200);
  const shown=new Set(visible.map(p=>p.node.path));
  return <svg className={`memory-spiral ${small?'memory-small':''}`} viewBox="0 0 920 860" aria-label={`Memória Obsidian: ${graph.total} notas reais`} onWheel={event=>{if(!small)setZoom(value=>Math.max(.6,Math.min(4,value*(event.deltaY>0?.9:1.1))));}}>
    <g transform={`translate(460 430) scale(${zoom}) translate(-460 -430)`}>
      <g stroke="#16d9ff" strokeWidth=".45" opacity=".35">{graph.edges.filter(e=>shown.has(e.source)&&shown.has(e.target)).map(edge=>{const a=positions.get(edge.source)!,b=positions.get(edge.target)!;return <path key={edge.source+'|'+edge.target} d={`M ${a.x} ${a.y} Q ${(a.x+b.x)/2+40} ${(a.y+b.y)/2-40} ${b.x} ${b.y}`} fill="none"/>;})}</g>
      {visible.map(({x,y,node,size})=><g key={node.path} transform={`translate(${x} ${y})`} role="button" tabIndex={small?-1:0} aria-label={node.title} onClick={()=>onSelect(node.path)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(node.path);}}} className="memory-node">
        <title>{node.title}</title><circle r={size+1.4} fill="#9eefff" opacity=".15"/><circle r={size} fill="#f5ffff"/><circle r="7" fill="transparent"/>
      </g>)}
    </g>

  </svg>;
});
