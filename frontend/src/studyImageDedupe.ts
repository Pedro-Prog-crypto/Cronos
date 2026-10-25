export type StudyImageIdentity={url:string;title:string};

function normalizedTitle(value:string){
 return value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'')
  .replace(/\.(?:jpe?g|png|webp|gif|avif)$/i,'').replace(/[^\p{L}\p{N}]+/gu,' ').trim();
}

export function normalizedImageUrl(value:string){
 let url=value.trim();
 try{
  const parsed=new URL(url);parsed.hash='';parsed.search='';
  // Wikimedia and Wikipedia resize the same file by inserting a width prefix.
  parsed.pathname=parsed.pathname.replace(/\/\d+px-([^/]+)$/i,'/$1');
  url=`${parsed.hostname.toLocaleLowerCase()}${parsed.pathname.toLocaleLowerCase()}`;
 }catch{url=url.toLocaleLowerCase().split(/[?#]/,1)[0];}
 return url;
}

export {normalizedTitle as normalizedImageTitle};

export function hammingDistance(left:string,right:string){
 if(left.length!==right.length)return Number.POSITIVE_INFINITY;
 let distance=0;for(let i=0;i<left.length;i++)if(left[i]!==right[i])distance++;
 return distance;
}

export function isNearDuplicateHash(candidate:string,accepted:string[],maxDistance=4){
 return accepted.some(hash=>hammingDistance(candidate,hash)<=maxDistance);
}
