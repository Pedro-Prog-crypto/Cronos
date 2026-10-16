import React,{useEffect,useState} from 'react';

export type TemplateReference={remote_images?:boolean;id:string;name:string;category:string;description:string;template_type:string;price_range:[number,number];features:string[];sample_images:string[];sample_texts:Record<string,string>;color_scheme:Record<string,string>;layout:string;notice?:string};
export type PricingTier={id:string;name:string;price_range:[number,number];type:string;features:string[];['3d']:boolean};
export type ReferenceSettings={reference_id:string;tier:string;template:string;model_type:string};
export const defaultReferenceSettings:ReferenceSettings={reference_id:'',tier:'reference',template:'premium',model_type:'auto'};
const brl=(n:number)=>n.toLocaleString('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0});
export const referenceType=(kind:string)=>kind==='3d'?'3D':kind==='2d_enhanced'?'2D Avançado':'2D';

export function ReferenceArt({reference,small=false}:{reference:TemplateReference;small?:boolean}){
 const [failed,setFailed]=useState(false);
 useEffect(()=>setFailed(false),[reference.id]);
 return <div className={'ss-reference-art '+(small?'small':'')} style={{'--ref-bg':reference.color_scheme.background,'--ref-ink':reference.color_scheme.text,'--ref-color':reference.color_scheme.primary} as React.CSSProperties}>
  <div className="ss-ref-label">{referenceType(reference.template_type)} / {reference.name}</div>
  {!failed&&reference.remote_images!==false&&reference.sample_images[0]?<img src={reference.sample_images[0]} loading="lazy" referrerPolicy="no-referrer" alt={'Imagem de exemplo da referência '+reference.name} onError={()=>setFailed(true)}/>:<div className="ss-ref-placeholder"><span>{reference.template_type==='3d'?'◈':'◇'}</span><small>Prévia de composição<br/>{reference.remote_images===false?'Fotografias externas desativadas':'Fotografia externa indisponível'}</small></div>}
  <div className="ss-ref-copy"><b>{reference.sample_texts.hero_title}</b><span>{reference.sample_texts.hero_description}</span></div>
 </div>;
}

export function ReferenceOptions({references,tiers,value,onChange}:{references:TemplateReference[];tiers:PricingTier[];value:ReferenceSettings;onChange:(value:ReferenceSettings)=>void}){
 const reference=references.find(r=>r.id===value.reference_id)||references[0];
 if(!reference)return null;
 const update=(key:keyof ReferenceSettings,next:string)=>onChange({...value,[key]:next});
 const selectedTier=tiers.find(t=>t.id===value.tier);
 const range=selectedTier?.price_range||reference.price_range;
 const is3d=selectedTier?selectedTier['3d']:reference.template_type==='3d';
 return <div className="ss-reference-options">
  <label>Referência do catálogo<select aria-label="Referência do catálogo" value={reference.id} onChange={e=>update('reference_id',e.target.value)}>{references.map(r=><option key={r.id} value={r.id}>{r.name} · {referenceType(r.template_type)}</option>)}</select></label>
  <div className="ss-ref-estimate"><b>{brl(range[0])} — {brl(range[1])}</b><span>{referenceType(is3d?'3d':selectedTier?.type||reference.template_type)} · proposta estimada</span></div>
  <p>{reference.description}</p>
  <label>Faixa de projeto<select aria-label="Faixa de projeto" value={value.tier} onChange={e=>update('tier',e.target.value)}><option value="reference">Faixa da referência escolhida</option>{tiers.map(t=><option key={t.id} value={t.id}>{t.name} · {brl(t.price_range[0])}–{brl(t.price_range[1])}</option>)}</select></label>
  <label>Template enviado<select aria-label="Template enviado" value={value.template} onChange={e=>update('template',e.target.value)}><option value="basic">Basic · 2D</option><option value="standard">Standard · 2D Avançado</option><option value="premium">Premium · categoria / 3D</option></select></label>
  {is3d&&<label>Modelo procedural<select aria-label="Modelo procedural" value={value.model_type} onChange={e=>update('model_type',e.target.value)}><option value="auto">Automático pela categoria</option><option value="earbuds">Fones com estojo</option><option value="airplane">Avião comercial</option><option value="hotel">Edifício com andares</option></select></label>}
  <div className="ss-ref-palette" aria-label="Esquema de cores">{Object.entries(reference.color_scheme).map(([name,color])=><span key={name} style={{backgroundColor:color}} title={name+': '+color}><i>{name}</i></span>)}</div>
  <details><summary>Recursos, textos e imagens enviados</summary><ul>{reference.features.map(f=><li key={f}>{f}</li>)}</ul><p>Recursos descritos na referência; pagamentos, integrações e dados reais precisam de implementação e configuração específicas.</p>{Object.entries(reference.sample_texts).map(([key,text])=><p key={key}><b>{key.replaceAll('_',' ')}:</b> {text}</p>)}<div className="ss-ref-images">{reference.sample_images.map((src,index)=><a key={src} href={src} target="_blank" rel="noopener noreferrer">{reference.remote_images===false?'Fonte da imagem '+(index+1):<img src={src} alt={'Exemplo '+(index+1)+' da referência'} loading="lazy" referrerPolicy="no-referrer"/>}</a>)}</div><p>{reference.notice}</p></details>
 </div>;
}

export function PricingOverview({tiers}:{tiers:PricingTier[]}){
 return <div className="ss-price-overview" aria-label="Faixas de projeto">{tiers.map(t=><article key={t.id}><span>{t.name}</span><b>{brl(t.price_range[0])} — {brl(t.price_range[1])}</b><small>{t['3d']?'3D':'2D'} · estimativa de proposta</small></article>)}</div>;
}
