import {useState} from 'react';
import {Search,X} from 'lucide-react';
import {modules} from '../panels/modules';
import type {CapabilityId} from '../capabilities';
import './home-dashboard.css';

type Props={connected:boolean;preferences:any;onPreferences:(value:any)=>void;panelOpenRequest:number;panelCloseRequest?:number;panelTarget?:number;menuOpen:boolean;onMenuClose:()=>void;section:CapabilityId|null;onSection:(value:CapabilityId|null)=>void;graphTotal:number;provider?:string;providerConfigured?:boolean;onModule:(index:number)=>void;onStudy:()=>void;onStudio:()=>void;onEye:()=>void;onChat:()=>void;onScreen:()=>void;onImage:()=>void;onDocument:()=>void;onMicrophone:()=>void;microphoneOn:boolean;presentationActive?:boolean};
const descriptions=['Processamento e tarefas inteligentes','Analise imagens e objetos','Voz e personalização','Comandos, textos e contextos','Planos e tarefas','Utilitários disponíveis','Serviços e plataformas conectados','Dados e memória estruturada','Pesquisa e recursos online','Dispositivos conectados','Proteção e permissões','Estado e desempenho do sistema'];
const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');
export function HomeDashboard({menuOpen,onMenuClose,onModule,onStudy,onStudio,onChat,onDocument}:Props){
 const [search,setSearch]=useState('');
 if(!menuOpen)return null;
 const open=(action:()=>void)=>{onMenuClose();action();};
 return <div className="cronos-home-hud functions-only"><section className="home-gear-menu" role="dialog" aria-modal="true" aria-label="Painel de Funções"><header><div><small>CRONOS / PAINEL DE FUNÇÕES</small><h2>Painel de Funções</h2><p>Acesse e gerencie os módulos disponíveis do Cronos.</p></div><button onClick={onMenuClose} aria-label="Fechar funções"><X size={22}/></button></header><label className="home-function-search"><Search size={19}/><input value={search} onChange={event=>setSearch(event.target.value)} placeholder="Buscar função ou módulo..." aria-label="Buscar função ou módulo"/></label><div className="home-gear-grid">{modules.map((item,index)=>({item,index})).filter(({item})=>normalize(item.name).includes(normalize(search))).map(({item,index})=>{const Icon=item.icon;return <button key={item.id} onClick={()=>open(()=>onModule(index))}><Icon size={31}/><span><strong>{item.name}</strong><small>{descriptions[index]}</small></span><b aria-hidden="true">→</b></button>;})}</div><div className="home-gear-tools"><h3>Ações rápidas</h3><button onClick={()=>open(onChat)}>Falar com o Cronos</button><button onClick={()=>open(onStudy)}>Estudos</button><button onClick={()=>open(onStudio)}>Projetos</button><button onClick={()=>open(onDocument)}>Enviar arquivo</button><button onClick={()=>open(()=>onModule(10))}>Configurações</button></div></section></div>;
}
