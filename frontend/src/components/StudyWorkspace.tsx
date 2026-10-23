import React,{useEffect,useRef,useState} from 'react';
import {BookOpen,BookPlus,ChevronLeft,ChevronRight,FileText,FolderPlus,Image as ImageIcon,Link as LinkIcon,LoaderCircle,Plus,RefreshCw,Search,Send,Upload,X} from 'lucide-react';
import {api,jsonApi} from '../api';
import {MinimizeWindow} from './WindowShelf';
import './StudyWorkspace.css';

type Subject={id:string;name:string;source_count:number;bytes:number;lesson_count:number;created_at:string};
type Source={id:string;filename:string;size:number;page_count:number;indexed_chars:number;created_at:string;kind?:string;source_url?:string};
type Citation={source:string;page:number;text?:string};
type ImageResult={title:string;url:string;source_url:string;license:string;artist:string};
type Lesson={id:string;question:string;answer:string;layout:string;citations:Citation[];created_at:string;image?:ImageResult|null};
type Props={active:boolean;onMinimize:()=>void;onClose:()=>void};

const fmt=(bytes:number)=>bytes<1024*1024?`${Math.ceil(bytes/1024)} KiB`:`${(bytes/(1024*1024)).toFixed(1)} MiB`;
const humanDate=(value:string)=>new Date(value).toLocaleDateString('pt-BR',{day:'2-digit',month:'short'});
function richLine(line:string,key:number){
 const heading=line.match(/^(#{1,3})\s+(.+)/);
 if(heading){const level=heading[1].length;return React.createElement(`h${level+1}`,{key,className:`study-heading level-${level}`},heading[2]);}
 if(/^\s*[-*]\s+/.test(line))return <li key={key}>{inline(line.replace(/^\s*[-*]\s+/,''))}</li>;
 if(/^\s*\d+[.)]\s+/.test(line))return <li key={key}>{inline(line.replace(/^\s*\d+[.)]\s+/,''))}</li>;
 if(!line.trim())return <div key={key} className="study-spacer"/>;
 if(/^>\s?/.test(line))return <blockquote key={key}>{inline(line.replace(/^>\s?/,''))}</blockquote>;
 return <p key={key}>{inline(line)}</p>;
}
function inline(value:string){
 const pieces=value.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
 return pieces.map((part,index)=>part.startsWith('**')&&part.endsWith('**')?<strong key={index}>{part.slice(2,-2)}</strong>:part.startsWith('`')&&part.endsWith('`')?<code key={index}>{part.slice(1,-1)}</code>:part);
}
const Article=React.memo(function Article({text}:{text:string}){
 const lines=text.split(/\r?\n/);const output:React.ReactNode[]=[];let list:React.ReactNode[]=[];
 const flush=()=>{if(list.length){output.push(<ul key={`list-${output.length}`}>{list}</ul>);list=[];}};
 lines.forEach((line,index)=>{if(/^\s*(?:[-*]\s+|\d+[.)]\s+)/.test(line)){list.push(richLine(line,index));return;}flush();output.push(richLine(line,index));});flush();
 return <div className="study-prose">{output}</div>;
});

const StudyQuestionForm=React.memo(function StudyQuestionForm({subjectName,hasSources,explaining,onExplain}:{subjectName:string;hasSources:boolean;explaining:boolean;onExplain:(value:string)=>Promise<boolean>}){
 const [value,setValue]=useState('');
 const submit=async(event:React.FormEvent)=>{event.preventDefault();const prompt=value.trim();if(prompt.length<2||explaining)return;if(await onExplain(prompt))setValue('');};
 return <form className="study-question-box" onSubmit={submit}><label htmlFor="study-question">O que o senhor quer aprender nesta matéria?</label><div className="study-question-input"><textarea id="study-question" value={value} onChange={event=>setValue(event.target.value)} maxLength={5000} rows={2} placeholder={hasSources?`Pergunte sobre ${subjectName.toLowerCase()} ou peça para explicar um trecho dos seus materiais…`:`Faça uma pergunta de ${subjectName.toLowerCase()}…`} disabled={explaining}/><button type="submit" disabled={explaining||value.trim().length<2} aria-label="Pedir explicação"><Send size={17}/><span>{explaining?'Preparando aula':'Explicar'}</span></button></div><small>As respostas com arquivos citam a fonte e a página utilizados.</small></form>;
});

const StudyLinkForm=React.memo(function StudyLinkForm({disabled,adding,onAdd}:{disabled:boolean;adding:boolean;onAdd:(url:string)=>Promise<boolean>}){
 const [value,setValue]=useState('');
 const submit=async(event:React.FormEvent)=>{event.preventDefault();const url=value.trim();if(!url||disabled||adding)return;if(await onAdd(url))setValue('');};
 return <form className="study-link-form" onSubmit={submit}><label htmlFor="study-source-link">Adicionar site ou vídeo</label><div><input id="study-source-link" type="url" value={value} onChange={event=>setValue(event.target.value)} placeholder="Cole um link público…" maxLength={2000} disabled={disabled||adding}/><button type="submit" disabled={disabled||adding||!value.trim()} aria-label="Importar link" title="Importar link">{adding?<LoaderCircle className="study-spin" size={16}/>:<Plus size={16}/>}</button></div><small>Sites, PDFs por link e transcrições públicas do YouTube. Conteúdo privado ou sem transcrição não pode ser lido.</small></form>;
});

export default function StudyWorkspace({active,onMinimize,onClose}:Props){
 const [subjects,setSubjects]=useState<Subject[]>([]),[subjectId,setSubjectId]=useState(''),[sources,setSources]=useState<Source[]>([]),[lessons,setLessons]=useState<Lesson[]>([]),[selectedLesson,setSelectedLesson]=useState<Lesson|null>(null);
 const [storage,setStorage]=useState({used_bytes:0,limit_bytes:5*1024**3,per_file_bytes:100*1024**2});
 const [newSubject,setNewSubject]=useState(''),[creating,setCreating]=useState(false),[uploading,setUploading]=useState(false),[addingLink,setAddingLink]=useState(false),[explaining,setExplaining]=useState(false),[imageLoading,setImageLoading]=useState(false),[imageMessage,setImageMessage]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[preview,setPreview]=useState<{name:string;url:string}|null>(null);
 const input=useRef<HTMLInputElement>(null),pdfInput=useRef<HTMLInputElement>(null),reader=useRef<HTMLDivElement>(null);
 const currentSubject=subjects.find(item=>item.id===subjectId)||null;

 const refresh=async(selectId?:string)=>{
  try{const data=await jsonApi('/studies/overview');setSubjects(data.subjects||[]);setStorage(data.storage||storage);const preferred=selectId||subjectId;const chosen=preferred&&(data.subjects||[]).some((item:Subject)=>item.id===preferred)?preferred:!preferred&&data.subjects?.length?data.subjects[0].id:'';if(chosen)setSubjectId(chosen);return chosen;}
  catch(e){setError(e instanceof Error?e.message:'Não foi possível carregar sua biblioteca de estudos.');}
 };
 const loadSubject=async(id:string)=>{
  if(!id){setSources([]);setLessons([]);setSelectedLesson(null);return;}
  setSubjectId(id);setSelectedLesson(null);
  try{const data=await(await api(`/studies/subjects/${id}/sources`)).json();setSources(data.sources||[]);setLessons(data.lessons||[]);setSelectedLesson(data.lessons?.[0]||null);}
  catch(e){setError(e instanceof Error?e.message:'Não consegui abrir esta matéria.');}
 };
 useEffect(()=>{void refresh().then(id=>{if(id)void loadSubject(id);});},[]);
 useEffect(()=>{if(active&&selectedLesson&&reader.current)reader.current.scrollTop=0;},[active,selectedLesson?.id]);
 useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview.url);},[preview?.url]);

 const create=async(event:React.FormEvent)=>{
  event.preventDefault();if(!newSubject.trim()||creating)return;setCreating(true);setError('');
  try{const created=await jsonApi('/studies/subjects',{name:newSubject.trim()});setNewSubject('');await refresh(created.id);await loadSubject(created.id);}
  catch(e){setError(e instanceof Error?e.message:'Não foi possível criar a matéria.');}finally{setCreating(false);}
 };
 const upload=async(files:FileList|null)=>{
  if(!files||!subjectId)return;setError('');setNotice('');setUploading(true);
  try{
   for(const file of Array.from(files)){
    if(file.size>storage.per_file_bytes)throw new Error(`${file.name}: o limite é 100 MiB por PDF.`);
    if(file.type!=='application/pdf'&&!file.name.toLowerCase().endsWith('.pdf'))throw new Error(`${file.name}: escolha um PDF.`);
    setNotice(`Guardando e indexando ${file.name}…`);
    await api(`/studies/subjects/${subjectId}/sources?name=${encodeURIComponent(file.name)}`,{method:'POST',headers:{'Content-Type':'application/pdf'},body:file});
   }
   setNotice('PDFs salvos nesta matéria. O Cronos já pode consultar o texto extraído.');await refresh(subjectId);await loadSubject(subjectId);
  }catch(e){setError(e instanceof Error?e.message:'Não foi possível guardar o PDF.');}
  finally{setUploading(false);if(pdfInput.current)pdfInput.current.value='';}
 };
 const addLink=async(url:string):Promise<boolean>=>{
  if(!subjectId||addingLink)return false;setError('');setNotice('');setAddingLink(true);setNotice('Buscando o texto público do link…');
  try{await jsonApi(`/studies/subjects/${subjectId}/links`,{url});setNotice('Fonte adicionada e indexada nesta matéria.');await refresh(subjectId);await loadSubject(subjectId);return true;}
  catch(e){setError(e instanceof Error?e.message:'Não consegui importar este link.');setNotice('');return false;}
  finally{setAddingLink(false);}
 };
 const findImage=async(text:string)=>{
  const query=text.replace(/^(?:me explique|explique|estude|fale sobre|resuma|ensine|me ensine)\s+/i,'').slice(0,120).trim();
  if(query.length<2)return null;
  setImageLoading(true);setImageMessage('');
  try{const result=await(await api(`/studies/images?query=${encodeURIComponent(query)}`)).json();const image=result.images?.[0]||null;if(!image)setImageMessage(result.message||'Não encontrei uma imagem pública compatível agora. A explicação continua disponível.');return image;}
  catch{setImageMessage('A busca de imagens está indisponível agora. A explicação continua disponível.');return null;}finally{setImageLoading(false);}
 };
 const explain=async(prompt:string):Promise<boolean>=>{
  if(!subjectId||prompt.trim().length<2||explaining)return false;setExplaining(true);setError('');setNotice('O Cronos está estudando os trechos mais relevantes desta matéria…');
  try{
   const lesson=await jsonApi(`/studies/subjects/${subjectId}/lessons`,{question:prompt});
   setSelectedLesson(lesson);setLessons(old=>[lesson,...old.filter(item=>item.id!==lesson.id)]);setNotice('Explicação pronta e salva no histórico desta matéria.');
   void findImage(prompt).then(image=>{if(image){const enriched={...lesson,image};setSelectedLesson(current=>current?.id===lesson.id?enriched:current);setLessons(old=>old.map(item=>item.id===lesson.id?enriched:item));}});
   void refresh(subjectId);return true;
  }catch(e){setError(e instanceof Error?e.message:'A explicação não terminou; seu material continua salvo.');setNotice('');return false;}
  finally{setExplaining(false);}
 };
 const openPdf=async(source:Source)=>{
  setError('');try{const blob=await(await api(`/studies/sources/${source.id}/file`)).blob();const url=URL.createObjectURL(blob);setPreview(old=>{if(old)URL.revokeObjectURL(old.url);return{name:source.filename,url};});}
  catch(e){setError(e instanceof Error?e.message:'Não foi possível abrir o PDF.');}
 };
 const showLesson=(lesson:Lesson)=>{setSelectedLesson(lesson);setNotice('');};
 const activeLayout=selectedLesson?.layout||'guided';
 const pageClass=`study-layout-${activeLayout}`;
 const selectedImage=selectedLesson?.image;
 const closePreview=()=>setPreview(old=>{if(old)URL.revokeObjectURL(old.url);return null;});

 return <section className={`study-window ${active?'is-active':''}`} aria-label="Área de estudos do Cronos">
  <header className="study-topbar"><div className="study-brand"><span className="study-brand-orb"><BookOpen size={18}/></span><div><b>CRONOS</b><small>AMBIENTE DE ESTUDOS</small></div></div><div className="study-top-actions"><span className="study-live"><i/> BIBLIOTECA LOCAL</span><MinimizeWindow label="Área de estudos" onClick={onMinimize}/><button className="study-icon-button" onClick={onClose} aria-label="Fechar estudos" title="Fechar estudos"><X size={19}/></button></div></header>
  <div className="study-shell">
   <aside className="study-sidebar">
    <div className="study-sidebar-title"><div><small>SEU ESPAÇO</small><h2>Matérias</h2></div><button className="study-icon-button" onClick={()=>input.current?.focus()} title="Criar matéria" aria-label="Criar matéria"><Plus size={17}/></button></div>
    <div className="study-subject-list">{subjects.map(subject=><button key={subject.id} className={`study-subject ${subject.id===subjectId?'selected':''}`} onClick={()=>void loadSubject(subject.id)}><span className="study-subject-symbol"><BookOpen size={16}/></span><span className="study-subject-copy"><b>{subject.name}</b><small>{subject.source_count} fontes · {subject.lesson_count} explicações</small></span><ChevronRight size={14}/></button>)}</div>
    <form className="study-create" onSubmit={create}><label htmlFor="study-new-subject">Criar outra matéria</label><div><input ref={input} id="study-new-subject" value={newSubject} maxLength={100} onChange={e=>setNewSubject(e.target.value)} placeholder="Ex.: Biologia"/><button disabled={creating||!newSubject.trim()} title="Criar matéria" aria-label="Criar matéria"><FolderPlus size={16}/></button></div></form>
    <div className="study-storage"><div className="study-storage-head"><span>ARQUIVOS DE ESTUDO</span><span>{fmt(storage.used_bytes)} / 5 GiB</span></div><div className="study-storage-bar"><i style={{width:`${Math.min(100,storage.used_bytes/storage.limit_bytes*100)}%`}}/></div><small>Os PDFs ficam no computador, separados por matéria.</small></div>
    <div className="study-history"><div className="study-history-head"><span>ÚLTIMAS EXPLICAÇÕES</span><RefreshCw size={13} onClick={()=>void refresh(subjectId)} aria-label="Atualizar histórico"/></div>{lessons.length?lessons.slice(0,8).map(lesson=><button key={lesson.id} className={`study-history-item ${selectedLesson?.id===lesson.id?'current':''}`} onClick={()=>showLesson(lesson)}><span>{lesson.question}</span><small>{humanDate(lesson.created_at)}</small></button>):<p>As explicações salvas nesta matéria aparecerão aqui.</p>}</div>
   </aside>

   <main className="study-main">
    {!currentSubject?<div className="study-empty"><div className="study-empty-orb"><BookPlus size={30}/></div><p>SEU PRÓXIMO CAPÍTULO COMEÇA AQUI</p><h1>Organize seus estudos<br/>do seu jeito.</h1><span>Crie uma matéria para separar biologia, matemática, história e tudo o que estiver aprendendo. Depois, guarde os PDFs e peça uma explicação completa.</span><button onClick={()=>input.current?.focus()}><Plus size={17}/> Criar primeira matéria</button></div>:<>
     <div className="study-subject-header"><div><div className="study-eyebrow">SALA DE ESTUDO · {String(subjects.findIndex(item=>item.id===subjectId)+1).padStart(2,'0')}</div><h1>{currentSubject.name}</h1><p>Seus materiais e explicações ficam organizados nesta matéria.</p></div><button className="study-upload-primary" disabled={uploading} onClick={()=>pdfInput.current?.click()}><Upload size={17}/>{uploading?'Indexando PDFs…':'Adicionar PDFs'}</button></div>
     <input ref={pdfInput} type="file" accept="application/pdf,.pdf" multiple hidden onChange={e=>void upload(e.target.files)}/>
     {notice&&<div className="study-notice" role="status"><LoaderCircle size={14} className={explaining||uploading?'study-spin':''}/>{notice}</div>}
     {error&&<div className="study-error" role="alert">{error}<button onClick={()=>setError('')} aria-label="Fechar erro"><X size={14}/></button></div>}
     {selectedLesson?<article className={`study-lesson ${pageClass}`} ref={reader}>
      <div className="study-lesson-meta"><span><i/>{activeLayout.toUpperCase()} · EXPLICAÇÃO PERSONALIZADA</span><span>{humanDate(selectedLesson.created_at)}</span></div>
      <div className="study-lesson-heading"><span className="study-lesson-kicker">AULA GUIADA</span><h2>{selectedLesson.question}</h2></div>
      <div className="study-article-grid">
       <div className="study-article-text"><Article text={selectedLesson.answer}/></div>
       {selectedImage&&<figure className="study-inline-image"><img src={selectedImage.url} alt={selectedImage.title}/><figcaption><b>{selectedImage.title}</b><span>{selectedImage.artist&&<>Autor: {selectedImage.artist}. </>}{selectedImage.license&&`Licença: ${selectedImage.license}. `}<a href={selectedImage.source_url} target="_blank" rel="noreferrer">Ver fonte ↗</a></span></figcaption></figure>}
      </div>
      {!!selectedLesson.citations?.length&&<div className="study-citation-row"><span>EXPLICADO COM BASE NOS SEUS PDFs</span>{selectedLesson.citations.map((citation,index)=><button key={`${citation.source}-${citation.page}-${index}`} onClick={()=>{const source=sources.find(file=>file.filename===citation.source);if(source)void openPdf(source);}}><FileText size={14}/>{citation.source} · pág. {citation.page}</button>)}</div>}
      <div className="study-lesson-footer"><span>Essa explicação foi salva no histórico de {currentSubject.name}.</span><button onClick={()=>reader.current?.scrollTo({top:0,behavior:'smooth'})}>Voltar ao início <ChevronLeft size={15}/></button></div>
     </article>:<div className="study-first-lesson"><div className="study-first-orb"><Search size={20}/></div><h2>Aprenda a partir do que importa.</h2><p>Adicione os PDFs desta matéria ou faça uma pergunta. O Cronos vai buscar os trechos mais úteis dos arquivos e explicar com exemplos, tópicos e uma pergunta para revisar o que você entendeu.</p>{!sources.length&&<button onClick={()=>pdfInput.current?.click()}><Upload size={16}/> Guardar o primeiro PDF</button>}</div>}
     <StudyQuestionForm key={subjectId} subjectName={currentSubject.name} hasSources={sources.length>0} explaining={explaining} onExplain={explain}/>
    </>}
   </main>

   <aside className="study-rightbar">
    <section className="study-side-section"><div className="study-section-title"><div><span className="study-section-icon"><FileText size={16}/></span><div><small>SEUS MATERIAIS</small><h3>Biblioteca</h3></div></div><button className="study-icon-button" disabled={!subjectId||uploading} onClick={()=>pdfInput.current?.click()} aria-label="Adicionar PDF"><Plus size={17}/></button></div>
     {sources.length?<div className="study-source-list">{sources.map(source=><button key={source.id} className="study-source" onClick={()=>source.kind==='link'&&source.source_url?window.open(source.source_url,'_blank','noopener,noreferrer'):void openPdf(source)}><span className="study-pdf-icon">{source.kind==='link'?<LinkIcon size={17}/>:<FileText size={17}/>}</span><span><b>{source.filename}</b><small>{source.kind==='link'?`${source.page_count} trechos · ${fmt(source.size)} · abrir origem ↗`:`${source.page_count} páginas · ${fmt(source.size)}`}</small></span><ChevronRight size={14}/></button>)}</div>:<div className="study-no-sources"><FileText size={22}/><p>Adicione apostilas, livros, sites ou vídeos com legenda pública.</p><small>PDFs até 100 MiB; links públicos até 30 MiB de conteúdo.</small></div>}
     <StudyLinkForm key={subjectId} disabled={!subjectId} adding={addingLink} onAdd={addLink}/>
    </section>
    <section className="study-side-section study-visual-section"><div className="study-section-title"><div><span className="study-section-icon violet"><ImageIcon size={16}/></span><div><small>REFERÊNCIA VISUAL</small><h3>Imagem de apoio</h3></div></div></div>
     {selectedImage?<a className="study-image-card" href={selectedImage.source_url} target="_blank" rel="noreferrer"><img src={selectedImage.url} alt={selectedImage.title}/><span>{selectedImage.title}</span><small>{selectedImage.license||'Wikimedia Commons'} · Ver origem ↗</small></a>:<div className="study-image-placeholder"><div className="study-image-orbit"><ImageIcon size={20}/></div><p>{imageLoading?'Buscando referência visual…':imageMessage||'A referência visual aparece quando houver uma imagem pública relacionada ao assunto.'}</p></div>}
    </section>
    <section className="study-side-section study-review"><div className="study-section-title"><div><span className="study-section-icon green"><BookOpen size={16}/></span><div><small>APRENDER ATIVAMENTE</small><h3>Revisão guiada</h3></div></div></div><p>As explicações terminam com uma pergunta aberta para ajudar o senhor a perceber se o conceito ficou claro.</p>{selectedLesson?.citations?.length?<div className="study-source-grounding"><span><i/>{selectedLesson.citations.length} trechos relacionados</span><small>A resposta pode separar o conteúdo da apostila de explicações complementares.</small></div>:<div className="study-review-tip">Dica: guarde os materiais da aula nesta matéria para que o Cronos fundamente a explicação neles.</div>}</section>
   </aside>
  </div>
  {preview&&<div className="study-pdf-overlay" role="dialog" aria-modal="true" aria-label={`PDF ${preview.name}`}><div className="study-pdf-toolbar"><FileText size={17}/><b>{preview.name}</b><a href={preview.url} download={preview.name}>Baixar</a><button onClick={closePreview} aria-label="Fechar prévia do PDF"><X size={18}/></button></div><iframe src={preview.url} title={preview.name}/></div>}
 </section>;
}
