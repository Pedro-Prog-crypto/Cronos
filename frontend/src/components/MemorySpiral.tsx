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
      const arm=index%5,turn=Math.floor(index/5),angle=arm*Math.PI*2/5+Math.log1p(turn)*.7+turn*.035;
      const radius=18+Math.sqrt(turn)*32,jitter=((hash(node.path)%13)-6)*.18;
      return [node.path,{x:460+Math.cos(angle)*(radius+jitter),y:430+Math.sin(angle)*(radius+jitter),node,size:Math.min(2,.8+Math.sqrt(degrees.get(node.path)||0)*.1)}];
    }));
  },[graph.nodes,graph.edges,degrees]);
  // Decorative trails follow real notes; semantic links remain separate.
  const trails=useMemo(()=>{
    const arms:Array<Array<{x:number;y:number;index:number}>>=Array.from({length:5},()=>[]);
    for(const [path,p] of [...positions].slice(0,1200)){const index=indices.current.get(path)!;arms[index%5].push({...p,index});}
    return arms.map(arm=>{
      arm.sort((a,b)=>a.index-b.index);
      if(arm.length<2)return '';
      let d=`M ${arm[0].x} ${arm[0].y}`;
      for(let i=1;i<arm.length;i++){
        const a=arm[i-1],b=arm[i],ai=Math.atan2(a.y-430,a.x-460),bi=Math.atan2(b.y-430,b.x-460),distance=Math.hypot(b.x-a.x,b.y-a.y)/3;
        d+=` C ${a.x-Math.sin(ai)*distance} ${a.y+Math.cos(ai)*distance}, ${b.x+Math.sin(bi)*distance} ${b.y-Math.cos(bi)*distance}, ${b.x} ${b.y}`;
      }
      return d;
    }).filter(Boolean);
  },[positions]);
  // Dust decorates existing notes; it never represents extra saved memories.
  // Three SVG paths rather than thousands of individually animated DOM elements.
  const dust=useMemo(()=>{
    const paths=['','',''];let count=0;const perNote=Math.max(2,Math.min(28,Math.floor(3000/Math.max(1,positions.size))));
    for(const [path,p] of positions){
      const seed=hash(path);
      for(let j=0;j<perNote&&count<3000;j++,count++){
        const a=((seed+j*137.508)%360)*Math.PI/180,r=5+Math.sqrt((seed+j*73)%997)/1.3;
        const x=p.x+Math.cos(a)*r,y=p.y+Math.sin(a)*r*.75,size=.45+(j%3)*.2;
        paths[j%3]+=`M${x.toFixed(1)} ${y.toFixed(1)}a${size} ${size} 0 1 0 ${size*2} 0a${size} ${size} 0 1 0 -${size*2} 0`;
      }
      if(count>=3000)break;
    }
    return paths;
  },[positions]);
  if(!graph.nodes.length)return null;
  const visible=[...positions.values()].filter(p=>Math.abs((p.x-460)*zoom)<455&&Math.abs((p.y-430)*zoom)<425).slice(0,1200);
  const shown=new Set(visible.map(p=>p.node.path));
  return <svg className={`memory-spiral ${small?'memory-small':''}`} viewBox="0 0 920 860" aria-label={`Memória Obsidian: ${graph.total} notas reais`} onWheel={event=>{if(!small)setZoom(value=>Math.max(.6,Math.min(4,value*(event.deltaY>0?.9:1.1))));}}>
    <g transform={`translate(460 430) scale(${zoom}) translate(-460 -430)`}>
      <g aria-hidden="true" pointerEvents="none" className="memory-stardust">{dust.map((d,i)=><path key={i} d={d} fill={i===1?'#7bdbff':'#f2fcff'} opacity={.35+i*.2}/>)}</g>
      <g className="memory-light-trails" fill="none" pointerEvents="none">
        {trails.map((d,i)=><g key={i}><path d={d} stroke="#009dff" strokeWidth="9" opacity=".07"/><path d={d} stroke="#16d9ff" strokeWidth="2.4" opacity=".25"/><path d={d} stroke="#b1f6ff" strokeWidth=".65" opacity=".8"/></g>)}
      </g>
      <g stroke="#16d9ff" strokeWidth=".45" opacity=".35">{graph.edges.filter(e=>shown.has(e.source)&&shown.has(e.target)).slice(0,1800).map(edge=>{const a=positions.get(edge.source)!,b=positions.get(edge.target)!;return <path key={edge.source+'|'+edge.target} d={`M ${a.x} ${a.y} Q ${(a.x+b.x)/2+40} ${(a.y+b.y)/2-40} ${b.x} ${b.y}`} fill="none"/>;})}</g>
      {visible.map(({x,y,node,size})=><g key={node.path} transform={`translate(${x} ${y})`} role="button" tabIndex={small?-1:0} aria-label={node.title} onClick={()=>onSelect(node.path)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(node.path);}}} className="memory-node">
        <title>{node.title}</title><circle r={size+1.4} fill="#9eefff" opacity=".15"/><circle r={size} fill="#f5ffff"/><circle r="7" fill="transparent"/>
      </g>)}
    </g>

  </svg>;
});
