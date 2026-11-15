export type NewsArticle={title:string;url:string;source:string;published:string;excerpt:string;image?:string};
type NewsTool={name:string;status:string;result?:unknown};
const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();

export function isDailyNewsRequest(message:string){
 const value=normalize(message).replace(/^(?:cronos|kronos|chronos)[, :]+/,'')
  .replace(/^(?:(?:me\s+)?(?:diga|conte|mostre|traga|fale|busque|pesquise|procure)(?:\s+me)?(?:\s+sobre)?|quais\s+(?:sao|foram))\s+/,'');
 return /^(?:as\s+)?(?:principais\s+|ultimas\s+)?noticias\s+(?:do dia|de hoje|atuais|de agora)\b/.test(value)
  && !/\b(?:nao|sem)\s+(?:pesquis|busc|procur)/.test(value)
  && !/\b(?:19|20)\d{2}\b|\bdo dia\s+\d/.test(value)
  && !/\b(?:e|tambem)\s+(?:abra|abrir|execute|executar|salve|salvar|apague|enviar)\b/.test(value);
}

function safeHttp(value:unknown){
 if(typeof value!=='string')return '';
 try{
  const url=new URL(value),host=url.hostname.toLowerCase();
  if(!['https:','http:'].includes(url.protocol)||url.username||url.password||host==='localhost'||host.endsWith('.localhost')||host.endsWith('.local')||host==='[::1]'||/^(?:0|10|127|169\.254|192\.168)\./.test(host)||/^172\.(?:1[6-9]|2\d|3[01])\./.test(host))return '';
  return url.href;
 }catch{return '';}
}

export function newsArticlesFromTools(tools:readonly NewsTool[]):NewsArticle[]{
 const raw=tools.find(tool=>tool.name==='web_news'&&tool.status==='completed')?.result;
 const articles=raw&&typeof raw==='object'&&'articles' in raw?(raw as {articles?:unknown}).articles:null;
 if(!Array.isArray(articles))return [];
 const seen=new Set<string>(),result:NewsArticle[]=[];
 for(const item of articles){
  if(!item||typeof item!=='object')continue;
  const article=item as Record<string,unknown>,url=safeHttp(article.url),title=String(article.title||'').trim();
  if(!url||!title||seen.has(url))continue;
  seen.add(url);
  const image=safeHttp(article.image);
  result.push({title:title.slice(0,300),url,source:String(article.source||new URL(url).hostname).slice(0,100),published:String(article.published||'').slice(0,100),excerpt:String(article.excerpt||'').slice(0,600),image:image.startsWith('https:')?image:undefined});
  if(result.length===6)break;
 }
 return result;
}
