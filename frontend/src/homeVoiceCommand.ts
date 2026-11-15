import {normalizeCapabilityCommand} from './capabilities.ts';

export type HomeVoiceCommand={action:'open';index:number}|{action:'close'};
const targets:Record<string,number>={clima:1,tempo:1,agenda:2,calendario:2,'e-mail':3,email:3,mensagens:3,tecnologia:4,noticias:4,'modelo de ia':5,'modelos de ia':5,'inteligencia artificial':5,politica:6,observacoes:7};

/** A verified transcription may contain only a navigation command. */
export function routeHomeVoiceCommand(text:string):HomeVoiceCommand|null{
 const value=normalizeCapabilityCommand(text).replace(/^(?:por favor)\s+/,'');
 const open=value.match(/^(?:(?:abrir|abra|abre|mostrar|mostre|exibir|exiba|ver|quero ver)\s+)?(?:o |a |os |as )?(cards?|cartoes|paineis|painel|briefing|resumo|clima|tempo|agenda|calendario|e-?mail|mensagens|tecnologia|noticias|modelos? de ia|inteligencia artificial|politica|observacoes)$/);
 if(open)return {action:'open',index:targets[open[1]]??0};
 if(/^(?:fechar|feche|fecha|ocultar|oculte|esconder|esconda)\s+(?:o |a |os |as )?(?:cards?|cartoes|paineis|painel|briefing|resumo|clima|agenda|e-?mail|noticias|observacoes|sistema|memoria|conexoes|analise|configuracoes)$/.test(value)||/^(?:voltar|inicio|tela inicial)$/.test(value))return {action:'close'};
 return null;
}

const modules:Record<string,number>={processamento:0,visao:1,voz:2,linguagem:3,planejamento:4,ferramentas:5,integracoes:6,'banco de dados':7,internet:8,dispositivos:9,seguranca:10,monitoramento:11};
/** Open the existing module; no new service or external integration is implied. */
export function routeModuleVoiceCommand(text:string):number|null{
 const value=normalizeCapabilityCommand(text);
 const match=value.match(/^(?:(?:abrir|abra|abre|mostrar|mostre|ver|acessar)\s+)?(?:o |a |os |as )?(processamento|visao|voz|linguagem|planejamento|ferramentas|integracoes|banco de dados|internet|dispositivos|seguranca|monitoramento)$/);
 return match?modules[match[1]]:null;
}
