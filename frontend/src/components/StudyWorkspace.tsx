import React,{useEffect,useRef,useState} from 'react';
import {BookOpen,BookPlus,ChevronLeft,ChevronRight,FileText,FolderPlus,Image as ImageIcon,Link as LinkIcon,LoaderCircle,Maximize2,Minimize2,PanelLeftClose,PanelLeftOpen,PanelRightClose,PanelRightOpen,Plus,RefreshCw,Search,Send,Upload,X} from 'lucide-react';
import {api,jsonApi} from '../api';
import {MinimizeWindow} from './WindowShelf';
import './StudyWorkspace.css';

type Subject={id:string;name:string;source_count:number;bytes:number;lesson_count:number;created_at:string};
type Source={id:string;filename:string;size:number;page_count:number;indexed_chars:number;created_at:string;kind?:string;source_url?:string};
type WebSource={title:string;url:string;summary:string};
type Citation={source:string;page:number;text?:string};
type ImageResult={title:string;url:string;proxy_url?:string;display_url?:string;source_url:string;license:string;artist:string};
type Lesson={id:string;question:string;answer:string;layout:string;citations:Citation[];created_at:string;image?:ImageResult|null};
type LearningMode='auto'|'simple'|'lesson'|'deep'|'visual'|'tutor'|'exam'|'research';
type Exercise={id:string;topic:string;skill:string;question:string;origin:'simulated';created_at:string};
type Grade={correct:boolean;feedback:string;error_point:string;next_step:string;due_date:string};
type Plan={days_left:number;daily_minutes:number;focus_subjects:string[];weak_topics:string[];reviews_due:{topic:string;due_date:string}[];date_status:string;official_sources:string[];suggested_blocks:string[]};
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

const StudyQuestionForm=React.memo(function StudyQuestionForm({subjectName,hasSources,selectedCount,explaining,onExplain}:{subjectName:string;hasSources:boolean;selectedCount:number;explaining:boolean;onExplain:(value:string,mode:LearningMode)=>Promise<boolean>}){
 const [value,setValue]=useState(''),[mode,setMode]=useState<LearningMode>('auto');
 const submit=async(event:React.FormEvent)=>{event.preventDefault();const prompt=value.trim();if(prompt.length<2||explaining)return;if(await onExplain(prompt,mode))setValue('');};
 return <form className="study-question-box" onSubmit={submit}><label htmlFor="study-question">O que o senhor quer aprender nesta matéria?</label><div className="study-learning-mode"><label htmlFor="study-mode">Forma de ensinar</label><select id="study-mode" value={mode} onChange={event=>setMode(event.target.value as LearningMode)} disabled={explaining}><option value="auto">Automática</option><option value="simple">Simples</option><option value="lesson">Aula completa</option><option value="deep">Ultradetalhada</option><option value="visual">Visual</option><option value="tutor">Professor particular</option><option value="exam">Preparação para prova</option><option value="research">Pesquisa profunda</option></select></div><div className="study-question-input"><textarea id="study-question" value={value} onChange={event=>setValue(event.target.value)} maxLength={5000} rows={3} placeholder={hasSources?`Pergunte sobre ${subjectName.toLowerCase()} ou peça para explicar um trecho dos seus materiais…`:`Faça uma pergunta de ${subjectName.toLowerCase()}…`} disabled={explaining}/><button type="submit" disabled={explaining||value.trim().length<2} aria-label="Pedir explicação"><Send size={17}/><span>{explaining?'Preparando aula':'Explicar'}</span></button></div><small>{hasSources?`${selectedCount} fonte(s) escolhida(s). Ajuste a seleção em Fontes.`:'Sem fontes locais: a resposta usa conhecimento geral.'} As respostas com arquivos citam a fonte e a página utilizados.</small></form>;
});

const StudyLinkForm=React.memo(function StudyLinkForm({disabled,adding,onAdd}:{disabled:boolean;adding:boolean;onAdd:(url:string)=>Promise<boolean>}){
 const [value,setValue]=useState('');
 const submit=async(event:React.FormEvent)=>{event.preventDefault();const url=value.trim();if(!url||disabled||adding)return;if(await onAdd(url))setValue('');};
 return <form className="study-link-form" onSubmit={submit}><label htmlFor="study-source-link">Adicionar site ou vídeo</label><div><input id="study-source-link" type="url" value={value} onChange={event=>setValue(event.target.value)} placeholder="Cole um link público…" maxLength={2000} disabled={disabled||adding}/><button type="submit" disabled={disabled||adding||!value.trim()} aria-label="Importar link" title="Importar link">{adding?<LoaderCircle className="study-spin" size={16}/>:<Plus size={16}/>}</button></div><small>Sites, PDFs por link e transcrições públicas do YouTube. Conteúdo privado ou sem transcrição não pode ser lido.</small></form>;
});

export default function StudyWorkspace({active,onMinimize,onClose}:Props){
 const [subjects,setSubjects]=useState<Subject[]>([]),[subjectId,setSubjectId]=useState(''),[sources,setSources]=useState<Source[]>([]),[lessons,setLessons]=useState<Lesson[]>([]),[selectedLesson,setSelectedLesson]=useState<Lesson|null>(null);
 const [storage,setStorage]=useState({used_bytes:0,limit_bytes:5*1024**3,per_file_bytes:100*1024**2});
 const [sourceQuery,setSourceQuery]=useState(''),[selectedSourceIds,setSelectedSourceIds]=useState<string[]>([]);
 const [webQuery,setWebQuery]=useState(''),[webResults,setWebResults]=useState<WebSource[]>([]),[webBusy,setWebBusy]=useState(false);
 const [leftCollapsed,setLeftCollapsed]=useState(false),[rightCollapsed,setRightCollapsed]=useState(false),[readerExpanded,setReaderExpanded]=useState(false);
 const [newSubject,setNewSubject]=useState(''),[creating,setCreating]=useState(false),[uploading,setUploading]=useState(false),[addingLink,setAddingLink]=useState(false),[explaining,setExplaining]=useState(false),[imageLoading,setImageLoading]=useState(false),[imageMessage,setImageMessage]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[preview,setPreview]=useState<{name:string;url:string}|null>(null);
 const [plan,setPlan]=useState<Plan|null>(null),[minutes,setMinutes]=useState(45),[focusInput,setFocusInput]=useState(''),[savingPlan,setSavingPlan]=useState(false);
 const [exercise,setExercise]=useState<Exercise|null>(null),[exerciseTopic,setExerciseTopic]=useState(''),[exerciseAnswer,setExerciseAnswer]=useState(''),[grade,setGrade]=useState<Grade|null>(null),[exerciseBusy,setExerciseBusy]=useState(false);
 const input=useRef<HTMLInputElement>(null),pdfInput=useRef<HTMLInputElement>(null),reader=useRef<HTMLDivElement>(null),imageUrls=useRef<string[]>([]),lastImageLesson=useRef('');
 const currentSubject=subjects.find(item=>item.id===subjectId)||null;
 const filteredSources=sources.filter(source=>source.filename.toLocaleLowerCase('pt-BR').includes(sourceQuery.trim().toLocaleLowerCase('pt-BR')));

 const refresh=async(selectId?:string)=>{
  try{const data=await jsonApi('/studies/overview');setSubjects(data.subjects||[]);setStorage(data.storage||storage);const preferred=selectId||subjectId;const chosen=preferred&&(data.subjects||[]).some((item:Subject)=>item.id===preferred)?preferred:!preferred&&data.subjects?.length?data.subjects[0].id:'';if(chosen)setSubjectId(chosen);return chosen;}
  catch(e){setError(e instanceof Error?e.message:'Não foi possível carregar sua biblioteca de estudos.');}
 };
 const loadSubject=async(id:string)=>{
  if(!id){setSources([]);setSelectedSourceIds([]);setLessons([]);setSelectedLesson(null);return;}
  setSubjectId(id);setSelectedLesson(null);
  try{const [data,pending]=await Promise.all([(await api(`/studies/subjects/${id}/sources`)).json(),(await api(`/studies/subjects/${id}/exercise/pending`)).json()]);setSources(data.sources||[]);setSelectedSourceIds((data.sources||[]).map((source:Source)=>source.id));setSourceQuery('');setLessons(data.lessons||[]);setSelectedLesson(data.lessons?.[0]||null);setExercise(pending.id?pending:null);setGrade(null);setExerciseAnswer('');}
  catch(e){setError(e instanceof Error?e.message:'Não consegui abrir esta matéria.');}
 };
 useEffect(()=>{void refresh().then(id=>{if(id)void loadSubject(id);});},[]);
 useEffect(()=>{void api('/learning/plan').then(response=>response.json()).then((value:Plan)=>{setPlan(value);setMinutes(value.daily_minutes);setFocusInput(value.focus_subjects.join(', '));}).catch(()=>{});},[]);
 useEffect(()=>{if(active&&selectedLesson&&reader.current)reader.current.scrollTop=0;},[active,selectedLesson?.id]);
 useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview.url);},[preview?.url]);
 useEffect(()=>()=>{for(const url of imageUrls.current)URL.revokeObjectURL(url);imageUrls.current=[];},[]);

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
 const searchWeb=async(event:React.FormEvent)=>{
  event.preventDefault();if(webQuery.trim().length<2||webBusy)return;
  setWebBusy(true);setError('');setWebResults([]);
  try{const result=await(await api(`/studies/source-search?query=${encodeURIComponent(webQuery.trim())}`)).json();setWebResults(result.results||[]);if(!result.results?.length)setNotice('Não encontrei fontes públicas para essa busca.');}
  catch(e){setError(e instanceof Error?e.message:'Não consegui pesquisar fontes agora.');}
  finally{setWebBusy(false);}
 };
 const findImage=async(text:string)=>{
  const query=text.replace(/^(?:me explique|explique|estude|fale sobre|resuma|ensine|me ensine)\s+/i,'').slice(0,120).trim();
  if(query.length<2)return null;
  setImageLoading(true);setImageMessage('');
  try{
   const result=await(await api(`/studies/images?query=${encodeURIComponent(query)}`)).json();
   for(const candidate of (result.images||[]).slice(0,5) as ImageResult[]){
    if(!candidate.proxy_url)continue;
    try{
     const blob=await(await api(candidate.proxy_url)).blob();
     if(!blob.type.startsWith('image/')||!blob.size)continue;
     const display_url=URL.createObjectURL(blob);
     imageUrls.current.push(display_url);
     return {...candidate,display_url};
    }catch{/* Tenta outra fonte sem mostrar um ícone de imagem quebrada. */}
   }
   setImageMessage(result.message||'As imagens encontradas não carregaram. Tente outra pergunta ou confira a conexão.');
   return null;
  }
  catch{setImageMessage('A busca de imagens está indisponível agora. A explicação continua disponível.');return null;}finally{setImageLoading(false);}
 };
 useEffect(()=>{
  const lesson=selectedLesson;
  if(!active||!lesson||lesson.image?.display_url||lastImageLesson.current===lesson.id)return;
  lastImageLesson.current=lesson.id;
  void findImage(lesson.question).then(image=>{
   if(!image)return;
   const enriched={...lesson,image};
   setSelectedLesson(current=>current?.id===lesson.id?enriched:current);
   setLessons(current=>current.map(item=>item.id===lesson.id?enriched:item));
  });
 },[active,selectedLesson?.id]);
 const explain=async(prompt:string,mode:LearningMode):Promise<boolean>=>{
  if(!subjectId||prompt.trim().length<2||explaining)return false;setExplaining(true);setError('');setNotice('O Cronos está estudando os trechos mais relevantes desta matéria…');
  const imagePromise=findImage(prompt);
  try{
   const lesson=await jsonApi(`/studies/subjects/${subjectId}/lessons`,{question:prompt,source_ids:selectedSourceIds,...(mode==='auto'?{}:{mode})});
   lastImageLesson.current=lesson.id;
   setSelectedLesson(lesson);setLessons(old=>[lesson,...old.filter(item=>item.id!==lesson.id)]);setNotice('Explicação pronta e salva no histórico desta matéria.');
   void imagePromise.then(image=>{if(image){const enriched={...lesson,image};setSelectedLesson(current=>current?.id===lesson.id?enriched:current);setLessons(old=>old.map(item=>item.id===lesson.id?enriched:item));}});
   void refresh(subjectId);return true;
  }catch(e){setError(e instanceof Error?e.message:'A explicação não terminou; seu material continua salvo.');setNotice('');return false;}
  finally{setExplaining(false);}
 };
 const savePlan=async()=>{
  setSavingPlan(true);setError('');try{const focus=focusInput.split(',').map(item=>item.trim()).filter(Boolean).slice(0,12);setPlan(await jsonApi('/learning/plan',{daily_minutes:minutes,focus_subjects:focus}));setNotice('Plano de estudo salvo. Ajuste o tempo disponível quando precisar.');}
  catch(e){setError(e instanceof Error?e.message:'Não consegui salvar o plano.');}finally{setSavingPlan(false);}
 };
 const makeExercise=async()=>{
  if(!subjectId||exerciseBusy)return;setExerciseBusy(true);setError('');setGrade(null);
  try{const value=await jsonApi(`/studies/subjects/${subjectId}/exercise`,{topic:exerciseTopic.trim()||currentSubject?.name||'assunto desta matéria'});setExercise(value);setExerciseAnswer('');setNotice('Exercício simulado criado. Responda para registrar seu progresso.');}
  catch(e){setError(e instanceof Error?e.message:'Não consegui criar a questão.');}finally{setExerciseBusy(false);}
 };
 const correctExercise=async()=>{
  if(!exercise||!exerciseAnswer.trim()||exerciseBusy)return;setExerciseBusy(true);setError('');
  try{const value=await jsonApi(`/studies/exercises/${exercise.id}/answer`,{answer:exerciseAnswer.trim()});setGrade(value);setPlan(await jsonApi('/learning/plan'));}
  catch(e){setError(e instanceof Error?e.message:'Não consegui corrigir a resposta.');}finally{setExerciseBusy(false);}
 };
 const openPdf=async(source:Source)=>{
  setError('');try{const blob=await(await api(`/studies/sources/${source.id}/file`)).blob();const url=URL.createObjectURL(blob);setPreview(old=>{if(old)URL.revokeObjectURL(old.url);return{name:source.filename,url};});}
  catch(e){setError(e instanceof Error?e.message:'Não foi possível abrir o PDF.');}
 };
 const showLesson=(lesson:Lesson)=>{setSelectedLesson(lesson);setNotice('');};
 const activeLayout=selectedLesson?.layout||'guided';
 const pageClass=`study-layout-${activeLayout}`;
 const selectedImage=selectedLesson?.image?.display_url?selectedLesson.image:null;
 const closePreview=()=>setPreview(old=>{if(old)URL.revokeObjectURL(old.url);return null;});

 return <section className={`study-window ${active?'is-active':''}`} aria-label="Área de estudos do Cronos">
  <header className="study-topbar"><div className="study-brand"><span className="study-brand-orb"><BookOpen size={18}/></span><div><b>CRONOS</b><small>AMBIENTE DE ESTUDOS</small></div></div><div className="study-top-actions"><span className="study-live"><i/> BIBLIOTECA LOCAL</span><button className="study-icon-button" onClick={()=>{setReaderExpanded(false);setLeftCollapsed(value=>!value);}} aria-label={leftCollapsed||readerExpanded?'Mostrar painel de fontes':'Recolher painel de fontes'} title="Mostrar ou recolher fontes">{leftCollapsed||readerExpanded?<PanelLeftOpen size={18}/>:<PanelLeftClose size={18}/>}</button><button className="study-icon-button" onClick={()=>{setReaderExpanded(false);setRightCollapsed(value=>!value);}} aria-label={rightCollapsed||readerExpanded?'Mostrar ferramentas de estudo':'Recolher ferramentas de estudo'} title="Mostrar ou recolher ferramentas">{rightCollapsed||readerExpanded?<PanelRightOpen size={18}/>:<PanelRightClose size={18}/>}</button><button className="study-icon-button" onClick={()=>setReaderExpanded(value=>!value)} aria-label={readerExpanded?'Restaurar painéis':'Maximizar leitura'} title={readerExpanded?'Restaurar painéis':'Maximizar leitura'}>{readerExpanded?<Minimize2 size={18}/>:<Maximize2 size={18}/>}</button><MinimizeWindow label="Área de estudos" onClick={onMinimize}/><button className="study-icon-button" onClick={onClose} aria-label="Fechar estudos" title="Fechar estudos"><X size={19}/></button></div></header>
  <div className={`study-shell ${leftCollapsed?'left-collapsed':''} ${rightCollapsed?'right-collapsed':''} ${readerExpanded?'reader-expanded':''}`}>
   <aside className="study-sidebar">
    <div className="study-sidebar-title"><div><small>SEU ESPAÇO</small><h2>Matérias</h2></div><div className="study-title-actions"><button className="study-icon-button" onClick={()=>input.current?.focus()} title="Criar matéria" aria-label="Criar matéria"><Plus size={17}/></button><button className="study-icon-button" onClick={()=>setLeftCollapsed(true)} title="Recolher fontes e matérias" aria-label="Recolher fontes e matérias"><PanelLeftClose size={17}/></button></div></div>
    <div className="study-subject-list">{subjects.map(subject=><button key={subject.id} className={`study-subject ${subject.id===subjectId?'selected':''}`} onClick={()=>void loadSubject(subject.id)}><span className="study-subject-symbol"><BookOpen size={16}/></span><span className="study-subject-copy"><b>{subject.name}</b><small>{subject.source_count} fontes · {subject.lesson_count} explicações</small></span><ChevronRight size={14}/></button>)}</div>
    <form className="study-create" onSubmit={create}><label htmlFor="study-new-subject">Criar outra matéria</label><div><input ref={input} id="study-new-subject" value={newSubject} maxLength={100} onChange={e=>setNewSubject(e.target.value)} placeholder="Ex.: Biologia"/><button disabled={creating||!newSubject.trim()} title="Criar matéria" aria-label="Criar matéria"><FolderPlus size={16}/></button></div></form>
    {currentSubject&&<section className="study-side-section study-left-sources" aria-label="Fontes da matéria"><div className="study-section-title"><div><span className="study-section-icon"><FileText size={16}/></span><div><small>{currentSubject.name.toUpperCase()}</small><h3>Fontes</h3></div></div><button className="study-icon-button" disabled={uploading} onClick={()=>pdfInput.current?.click()} aria-label="Adicionar PDF" title="Adicionar PDF"><Plus size={17}/></button></div>
     <label className="study-source-search"><Search size={15}/><input value={sourceQuery} onChange={event=>setSourceQuery(event.target.value)} placeholder="Buscar nas fontes salvas" aria-label="Buscar nas fontes salvas"/></label>
     {sources.length>0&&<div className="study-source-select"><span>{selectedSourceIds.length} de {sources.length} fontes na próxima explicação</span><button onClick={()=>setSelectedSourceIds(selectedSourceIds.length===sources.length?[]:sources.map(source=>source.id))}>{selectedSourceIds.length===sources.length?'Limpar seleção':'Selecionar todas'}</button></div>}
     {sources.length?<div className="study-source-list">{filteredSources.map(source=><div key={source.id} className="study-source-row"><input type="checkbox" checked={selectedSourceIds.includes(source.id)} onChange={event=>setSelectedSourceIds(current=>event.target.checked?[...current,source.id]:current.filter(id=>id!==source.id))} aria-label={`Usar ${source.filename} na explicação`}/><button className="study-source" onClick={()=>source.kind==='link'&&source.source_url?window.open(source.source_url,'_blank','noopener,noreferrer'):void openPdf(source)}><span className="study-pdf-icon">{source.kind==='link'?<LinkIcon size={17}/>:<FileText size={17}/>}</span><span><b>{source.filename}</b><small>{source.kind==='link'?`${source.page_count} trechos · abrir origem ↗`:`${source.page_count} páginas · ${fmt(source.size)}`}</small></span><ChevronRight size={14}/></button></div>)}{!filteredSources.length&&<p className="study-source-empty">Nenhuma fonte salva combina com a busca.</p>}</div>:<div className="study-no-sources"><FileText size={22}/><p>Adicione PDFs, sites ou vídeos com transcrição pública.</p></div>}
     <StudyLinkForm key={subjectId} disabled={!subjectId} adding={addingLink} onAdd={addLink}/>
     <form className="study-web-search" onSubmit={searchWeb}><label htmlFor="study-web-query">Pesquisar novas fontes na web</label><div><input id="study-web-query" value={webQuery} onChange={event=>setWebQuery(event.target.value)} maxLength={200} placeholder="Ex.: Iluminismo e Revolução Francesa"/><button disabled={webBusy||webQuery.trim().length<2} title="Pesquisar fontes" aria-label="Pesquisar fontes">{webBusy?<LoaderCircle className="study-spin" size={16}/>:<Search size={16}/>}</button></div></form>
     {webResults.length>0&&<div className="study-web-results">{webResults.map(result=><div key={result.url}><b>{result.title}</b><small>{result.summary}</small><button disabled={addingLink} onClick={()=>void addLink(result.url)}>Adicionar esta fonte</button></div>)}</div>}
    </section>}
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
       {selectedImage&&<figure className="study-inline-image"><img src={selectedImage.display_url} alt={selectedImage.title}/><figcaption><b>{selectedImage.title}</b><span>{selectedImage.artist&&<>Autor: {selectedImage.artist}. </>}{selectedImage.license&&`Licença: ${selectedImage.license}. `}<a href={selectedImage.source_url} target="_blank" rel="noreferrer">Ver fonte ↗</a></span></figcaption></figure>}
      </div>
      {!!selectedLesson.citations?.length&&<div className="study-citation-row"><span>EXPLICADO COM BASE NOS SEUS PDFs</span>{selectedLesson.citations.map((citation,index)=><button key={`${citation.source}-${citation.page}-${index}`} onClick={()=>{const source=sources.find(file=>file.filename===citation.source);if(source)void openPdf(source);}}><FileText size={14}/>{citation.source} · pág. {citation.page}</button>)}</div>}
      <div className="study-lesson-footer"><span>Essa explicação foi salva no histórico de {currentSubject.name}.</span><button onClick={()=>reader.current?.scrollTo({top:0,behavior:'smooth'})}>Voltar ao início <ChevronLeft size={15}/></button></div>
     </article>:<div className="study-first-lesson"><div className="study-first-orb"><Search size={20}/></div><h2>Aprenda a partir do que importa.</h2><p>Adicione os PDFs desta matéria ou faça uma pergunta. O Cronos vai buscar os trechos mais úteis dos arquivos e explicar com exemplos, tópicos e uma pergunta para revisar o que você entendeu.</p>{!sources.length&&<button onClick={()=>pdfInput.current?.click()}><Upload size={16}/> Guardar o primeiro PDF</button>}</div>}
    </>}
   </main>

   <aside className="study-rightbar"><div className="study-side-heading"><div><small>FERRAMENTAS</small><h2>Estúdio de estudos</h2></div><button className="study-icon-button" onClick={()=>setRightCollapsed(true)} aria-label="Recolher ferramentas de estudo" title="Recolher ferramentas"><PanelRightClose size={17}/></button></div>
    {currentSubject&&<StudyQuestionForm key={subjectId} subjectName={currentSubject.name} hasSources={sources.length>0} selectedCount={selectedSourceIds.length} explaining={explaining} onExplain={explain}/>}
    <section className="study-side-section study-visual-section"><div className="study-section-title"><div><span className="study-section-icon violet"><ImageIcon size={16}/></span><div><small>REFERÊNCIA VISUAL</small><h3>Imagem de apoio</h3></div></div></div>
     {selectedImage?<a className="study-image-card" href={selectedImage.source_url} target="_blank" rel="noreferrer"><img src={selectedImage.display_url} alt={selectedImage.title}/><span>{selectedImage.title}</span><small>{selectedImage.license||'Wikimedia Commons'} · Ver origem ↗</small></a>:<div className="study-image-placeholder"><div className="study-image-orbit"><ImageIcon size={20}/></div><p>{imageLoading?'Carregando imagem verificada…':imageMessage||'A referência visual aparece quando houver uma imagem pública relacionada ao assunto.'}</p></div>}
    </section>
    {currentSubject&&<section className="study-learning-panel" aria-label="Questão e correção"><div className="study-learning-heading"><div><small>PRÁTICA ATIVA</small><h2>Exercício e correção</h2></div><span>Questão criada pelo Cronos · simulada</span></div><div className="study-exercise-actions"><input aria-label="Assunto do exercício" value={exerciseTopic} onChange={e=>setExerciseTopic(e.target.value)} placeholder={`Assunto de ${currentSubject.name}`}/><button disabled={exerciseBusy} onClick={()=>void makeExercise()}>{exerciseBusy?'Aguarde…':'Criar exercício'}</button></div>{exercise&&<div className="study-exercise-body"><small>{exercise.skill} · SIMULADA</small><p>{exercise.question}</p><label htmlFor="study-exercise-answer">Sua resposta</label><textarea id="study-exercise-answer" value={exerciseAnswer} onChange={e=>setExerciseAnswer(e.target.value)} rows={3} placeholder="Explique como pensou para eu encontrar a dificuldade exata."/><button disabled={exerciseBusy||!exerciseAnswer.trim()||Boolean(grade)} onClick={()=>void correctExercise()}>Corrigir resposta</button></div>}{grade&&<div className="study-exercise-feedback" role="status"><b>{grade.correct?'Raciocínio correto':'Vamos corrigir este ponto'}</b><p>{grade.feedback}</p>{grade.error_point&&<p>Ponto a rever: {grade.error_point}</p>}<p>Próximo passo: {grade.next_step}</p><small>Revisão sugerida: {new Date(`${grade.due_date}T12:00:00`).toLocaleDateString('pt-BR')}</small></div>}</section>}
    {plan&&<section className="study-learning-panel" aria-label="Meu plano PAS 2"><div className="study-learning-heading"><div><small>MEU PLANO · PAS 2</small><h2>{plan.days_left} dias até 13/12/2026</h2></div><span>Data informada pelo senhor; confira o edital</span></div><div className="study-plan-controls"><label>Minutos por dia <input type="number" min={10} max={480} value={minutes} onChange={e=>setMinutes(Number(e.target.value))}/></label><label>Matérias prioritárias <input value={focusInput} onChange={e=>setFocusInput(e.target.value)} placeholder="Ex.: Matemática, História"/></label><button disabled={savingPlan||minutes<10||minutes>480} onClick={()=>void savePlan()}>{savingPlan?'Salvando…':'Salvar plano'}</button></div><div className="study-plan-tasks">{plan.suggested_blocks.map((task,index)=><span key={index}>{task}</span>)}</div>{plan.weak_topics.length>0&&<p>Reforçar pelos exercícios: {plan.weak_topics.join(', ')}.</p>}{plan.reviews_due.length>0&&<p>{plan.reviews_due.length} revisão(ões) pendente(s) baseada(s) nas respostas dadas.</p>}<small>Confira <a href={plan.official_sources[0]} target="_blank" rel="noreferrer">Cebraspe</a> e <a href={plan.official_sources[1]} target="_blank" rel="noreferrer">matrizes da UnB</a> antes de tratar conteúdos e datas como oficiais.</small></section>}
    <section className="study-side-section study-review"><div className="study-section-title"><div><span className="study-section-icon green"><BookOpen size={16}/></span><div><small>APRENDER ATIVAMENTE</small><h3>Revisão guiada</h3></div></div></div><p>As explicações terminam com uma pergunta aberta para ajudar o senhor a perceber se o conceito ficou claro.</p>{selectedLesson?.citations?.length?<div className="study-source-grounding"><span><i/>{selectedLesson.citations.length} trechos relacionados</span><small>A resposta pode separar o conteúdo da apostila de explicações complementares.</small></div>:<div className="study-review-tip">Dica: guarde os materiais da aula nesta matéria para que o Cronos fundamente a explicação neles.</div>}</section>
   </aside>
  </div>
  {preview&&<div className="study-pdf-overlay" role="dialog" aria-modal="true" aria-label={`PDF ${preview.name}`}><div className="study-pdf-toolbar"><FileText size={17}/><b>{preview.name}</b><a href={preview.url} download={preview.name}>Baixar</a><button onClick={closePreview} aria-label="Fechar prévia do PDF"><X size={18}/></button></div><iframe src={preview.url} title={preview.name}/></div>}
 </section>;
}
