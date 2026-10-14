export type ProspectCommand={city:string;category:string};
export function prospectCommand(text:string):ProspectCommand|null{
 const clean=text.trim().replace(/^(?:cronos|kronos)[,\s:]+/i,'').replace(/[.!?]+$/,'');
 const plain=clean.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 if(/^(?:abrir|abra|abre|mostrar|mostre) (?:o )?(?:painel de )?(?:prospeccao|clientes|oportunidades)$/.test(plain))return {city:'',category:'restaurante'};
 if(!/^(?:buscar|busque|procurar|procure|encontrar|encontre|listar|liste|me fale|me mostre|pesquisar|pesquise)\b/.test(plain)|| !/\b(?:sites?|clientes?|prospeccao|oportunidades)\b/.test(plain))return null;
 const city=clean.match(/\b(?:em|na cidade de)\s+(.+)$/i);if(!city)return null;
 const category=/pizzaria/.test(plain)?'pizzaria':/lanchonete/.test(plain)?'lanchonete':/cafeteria/.test(plain)?'cafeteria':/japones/.test(plain)?'japones':'restaurante';
 return {city:city[1].replace(/[,\s]+por favor$/i,'').trim(),category};
}
