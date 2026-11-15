import {HologramDeck,type HologramDeckCard} from './HologramDeck';
import {Activity,CalendarDays,CloudSun,FileText,Globe,Layers,Mail,NotebookPen,Radio,Sun} from 'lucide-react';
import technologyImage from '../assets/images/news_gandhi_doc_1791817493630.jpg';
import aiImage from '../assets/images/news_ai_safety_1791817511005.jpg';
import politicsImage from '../assets/images/news_politics_hall_1791817523809.jpg';

type Props={connected:boolean;graphTotal:number;onModule:(index:number)=>void;onMemory:()=>void;onClose:()=>void;initialCard?:number};

/** The reference geometry uses real module state; disconnected feeds have no invented readings. */
export function ReferenceCards({connected,graphTotal,onModule,onMemory,onClose,initialCard=0}:Props){
 const cards:HologramDeckCard[]=[
  {id:'briefing',icon:<Activity size={20}/>,kicker:'ALERTA · BRIEFING',title:'Resumo do sistema',badge:connected?'LOCAL':'OFFLINE',visual:<div className="deck-signal-visual"><Radio size={26}/><span><strong>{connected?'Sinais disponíveis':'Aguardando serviço local'}</strong><small>MONITORAMENTO DO DISPOSITIVO</small></span><i aria-hidden="true"/></div>,body:connected?'Consulte os sinais e alertas monitorados pelo Cronos.':'Conecte o serviço local para consultar os sinais do sistema.',action:'Abrir monitoramento',open:()=>onModule(11)},
  {id:'weather',icon:<CloudSun size={20}/>,kicker:'PARÂMETROS · CLIMA',title:'Seu clima',badge:'SEM FONTE',visual:<div className="deck-weather-visual"><Sun size={38}/><strong>—°</strong><span>CLIMA<br/>NÃO CONECTADO</span></div>,body:'Localização e fonte meteorológica ainda não conectadas.',action:'Abrir ferramentas',open:()=>onModule(5)},
  {id:'agenda',icon:<CalendarDays size={20}/>,kicker:'AGENDA · HOJE',title:'Sua agenda',badge:'SEM CALENDÁRIO',visual:<div className="deck-empty-visual"><CalendarDays size={36}/><strong>Agenda não conectada</strong><small>Os planos continuam no planejamento.</small></div>,body:'Abra o planejamento para consultar seus planos.',action:'Abrir planejamento',open:()=>onModule(4)},
  {id:'emails',icon:<Mail size={20}/>,kicker:'COMUNICAÇÕES · E-MAIL',title:'Sua caixa de entrada',badge:'SEM CONTA',visual:<div className="deck-mail-visual"><span><Mail size={18}/> INBOX <b>—</b></span><span><Radio size={16}/> Aguardando integração</span></div>,body:'Nenhuma conta de e-mail conectada a este painel.',action:'Ver integrações',open:()=>onModule(6)},
  {id:'technology',icon:<Globe size={20}/>,kicker:'NOTÍCIAS · TECNOLOGIA',title:'Tecnologia',badge:'PESQUISA',visual:<div className="deck-news-visual"><img src={technologyImage} alt="Ilustração histórica; não é uma notícia ao vivo"/><span>IMAGEM ILUSTRATIVA · FONTE NÃO CONECTADA</span></div>,body:'Abra a pesquisa para consultar notícias atuais e suas fontes.',action:'Abrir pesquisa',open:()=>onModule(8)},
  {id:'ai',icon:<Layers size={20}/>,kicker:'IA · PESQUISA',title:'Modelos de IA',badge:'INTEGRAÇÕES',visual:<div className="deck-news-visual"><img src={aiImage} alt="Ilustração de inteligência artificial; não é uma notícia ao vivo"/><span>IMAGEM ILUSTRATIVA · FONTE NÃO CONECTADA</span></div>,body:'Consulte os modelos disponíveis nas suas integrações.',action:'Ver modelos',open:()=>onModule(6)},
  {id:'politics',icon:<FileText size={20}/>,kicker:'NOTÍCIAS · POLÍTICA',title:'Política',badge:'PESQUISA',visual:<div className="deck-news-visual"><img src={politicsImage} alt="Ilustração de edifício público; não é uma notícia ao vivo"/><span>IMAGEM ILUSTRATIVA · FONTE NÃO CONECTADA</span></div>,body:'Pesquise notícias atuais no módulo de internet.',action:'Abrir pesquisa',open:()=>onModule(8)},
  {id:'notes',icon:<NotebookPen size={20}/>,kicker:'OBSERVAÇÕES · MEMÓRIA',title:'Observações disponíveis',badge:connected?'MEMÓRIA LOCAL':'OFFLINE',visual:<div className="deck-empty-visual"><NotebookPen size={34}/><strong>{connected?`${graphTotal} registro${graphTotal===1?'':'s'}`:'Memória desconectada'}</strong><small>NOTAS DO CRONOS</small></div>,body:connected?'Revise as observações registradas.':'Conecte o serviço local para consultar a memória.',action:'Ver memória',open:onMemory},
 ];
 return <HologramDeck cards={cards} label="Cards principais do Cronos" initialActive={initialCard} onClose={onClose}/>;
}
