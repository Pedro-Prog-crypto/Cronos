/** UI entry points for existing CRONOS services. Server-side tool permissions stay in cronos/tools.py. */
export type CapabilityId = 'system'|'memory'|'connections'|'analysis'|'settings'|'studio'|'study'|'internet'|'files'|'chat'|'screen'|'microphone';
export type Capability = {id:CapabilityId;label:string;category:'navigation'|'workspace'|'input';description:string;permission:'safe'|'confirm';requiresConnection:boolean;moduleIndex?:number;patterns:RegExp[]};
export const capabilities:readonly Capability[] = [
 {id:'system',label:'Sistema',category:'navigation',description:'Indicadores e estado do computador',permission:'safe',requiresConnection:true,moduleIndex:11,patterns:[/^(?:abrir|mostrar|ver|ir para) (?:o )?(?:sistema|painel do sistema)$/]},
 {id:'memory',label:'Memória',category:'navigation',description:'Notas e memória persistente',permission:'safe',requiresConnection:true,moduleIndex:7,patterns:[/^(?:abrir|mostrar|ver|ir para) (?:a )?memoria$/]},
 {id:'connections',label:'Conexões',category:'navigation',description:'Provedores e integrações configurados',permission:'safe',requiresConnection:true,moduleIndex:6,patterns:[/^(?:abrir|mostrar|ver|ir para) (?:as )?conexoes$/]},
 {id:'analysis',label:'Análise',category:'navigation',description:'Ferramentas de análise existentes',permission:'safe',requiresConnection:true,moduleIndex:0,patterns:[/^(?:abrir|mostrar|ver|ir para) (?:a )?analise$/]},
 {id:'settings',label:'Configurações',category:'navigation',description:'Preferências do assistente',permission:'safe',requiresConnection:true,moduleIndex:5,patterns:[/^(?:abrir|mostrar|ver|ir para) (?:as )?configuracoes$/]},
 {id:'studio',label:'Estúdio de Sites',category:'workspace',description:'Projetos de sites',permission:'safe',requiresConnection:true,patterns:[/^(?:abrir|mostrar) (?:o )?estudio de sites$/]},
 {id:'study',label:'Área de estudos',category:'workspace',description:'Materiais e explicações',permission:'safe',requiresConnection:true,patterns:[/^(?:abrir|mostrar) (?:a )?area de estudos$/]},
 {id:'internet',label:'Internet',category:'workspace',description:'Busca e conectividade',permission:'safe',requiresConnection:true,moduleIndex:8,patterns:[/^(?:abrir|mostrar) (?:a )?internet$/]},
 {id:'files',label:'Arquivos',category:'workspace',description:'Análise de arquivos',permission:'safe',requiresConnection:true,patterns:[/^(?:abrir|mostrar|analisar) (?:um )?arquivo$/]},
 {id:'chat',label:'Conversa',category:'input',description:'Mensagem por texto',permission:'safe',requiresConnection:false,patterns:[/^(?:abrir|mostrar) (?:a )?conversa$/]},
 {id:'screen',label:'Tela',category:'input',description:'Compartilhar tela após seleção do navegador',permission:'confirm',requiresConnection:true,patterns:[]},
 {id:'microphone',label:'Microfone',category:'input',description:'Captura de voz autorizada pelo navegador',permission:'confirm',requiresConnection:true,patterns:[]},
];
export function normalizeCapabilityCommand(text:string){return text.trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/^(?:cronos|kronos|chronos)[,\s:]+/i,'').replace(/[.!?]+$/,'').toLowerCase().replace(/\s+/g,' ');}
export function routeCapabilityCommand(text:string):Capability|undefined{const value=normalizeCapabilityCommand(text);return capabilities.find(item=>item.patterns.some(pattern=>pattern.test(value)));}
export function capability(id:CapabilityId){return capabilities.find(item=>item.id===id)!;}
export type CapabilityHandlers=Partial<Record<CapabilityId,()=>void>>;
export class ActionRouter {
 private readonly handlers:CapabilityHandlers;
 constructor(handlers:CapabilityHandlers){this.handlers=handlers;}
 execute(id:CapabilityId):boolean{const handler=this.handlers[id];if(!handler)return false;handler();return true;}
 route(text:string):boolean{const match=routeCapabilityCommand(text);return match?this.execute(match.id):false;}
}
