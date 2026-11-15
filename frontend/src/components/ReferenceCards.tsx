import {HologramDeck} from './HologramDeck';
import {Activity,CalendarDays,CloudSun,FileText,Globe,Layers,Mail,NotebookPen} from 'lucide-react';

type Props={connected:boolean;graphTotal:number;onModule:(index:number)=>void;onMemory:()=>void;onClose:()=>void};

// These cards expose existing modules. Unconnected feeds never masquerade as live data.
export function ReferenceCards({connected,graphTotal,onModule,onMemory,onClose}:Props){
 const cards=[
  {id:'briefing',icon:Activity,kicker:'ALERTA · BRIEFING',title:'Resumo do sistema',body:connected?'Consulte os sinais, eventos e alertas monitorados pelo Cronos.':'Conecte o serviço local para consultar os sinais do sistema.',action:'Abrir monitoramento',open:()=>onModule(11)},
  {id:'weather',icon:CloudSun,kicker:'PARÂMETROS · CLIMA',title:'Seu clima',body:'Localização e fonte meteorológica ainda não conectadas.',action:'Abrir ferramentas',open:()=>onModule(5)},
  {id:'agenda',icon:CalendarDays,kicker:'AGENDA · HOJE',title:'Sua agenda',body:'Calendário ainda não conectado. Seus planos estão disponíveis no planejamento.',action:'Abrir planejamento',open:()=>onModule(4)},
  {id:'emails',icon:Mail,kicker:'COMUNICAÇÕES · E-MAIL',title:'Sua caixa de entrada',body:'Nenhuma conta de e-mail conectada a este painel.',action:'Ver integrações',open:()=>onModule(6)},
  {id:'notes',icon:NotebookPen,kicker:'OBSERVAÇÕES · MEMÓRIA',title:'Observações disponíveis',body:connected?`${graphTotal} registro${graphTotal===1?'':'s'} na memória do Cronos.`:'Conecte o serviço local para consultar a memória.',action:'Ver memória',open:onMemory},
  {id:'technology',icon:Globe,kicker:'NOTÍCIAS · TECNOLOGIA',title:'Tecnologia',body:'Abra a pesquisa para consultar notícias e suas fontes.',action:'Abrir pesquisa',open:()=>onModule(8)},
  {id:'ai',icon:Layers,kicker:'IA · PESQUISA',title:'Modelos de IA',body:'Consulte os provedores e modelos disponíveis nas suas integrações.',action:'Ver modelos',open:()=>onModule(6)},
  {id:'politics',icon:FileText,kicker:'NOTÍCIAS · POLÍTICA',title:'Política',body:'Pesquise notícias atuais no módulo de internet.',action:'Abrir pesquisa',open:()=>onModule(8)},
 ];
 const ordered=[...cards.filter(card=>card.id!=='notes'),cards.find(card=>card.id==='notes')!];
 return <HologramDeck cards={ordered.map(card=>{const Icon=card.icon;return {...card,icon:<Icon size={20}/>};})} label="Cards principais do Cronos" onClose={onClose}/>;
}
