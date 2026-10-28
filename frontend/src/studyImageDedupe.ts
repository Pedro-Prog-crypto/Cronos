export type StudyImageIdentity={url:string;title:string};

function normalizedTitle(value:string){
 return value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,'')
  .replace(/\.(?:jpe?g|png|webp|gif|avif)$/i,'').replace(/[^\p{L}\p{N}]+/gu,' ').trim();
}

export function normalizedImageUrl(value:string){
 let url=value.trim();
 try{
  const parsed=new URL(url);parsed.hash='';
  // Query parameters such as Bing's id and DuckDuckGo's u identify the image.
  for(const key of [...parsed.searchParams.keys()])if(/^(?:utm_.*|width|height|w|h|quality|q|fit|crop)$/i.test(key))parsed.searchParams.delete(key);
  parsed.searchParams.sort();
  if(parsed.hostname.endsWith('wikimedia.org')&&parsed.pathname.includes('/thumb/')){
   parsed.pathname=parsed.pathname.replace('/thumb/','/').replace(/\/\d+px-[^/]+$/i,'');
  }
  // Wikimedia and Wikipedia resize the same file by inserting a width prefix.
  parsed.pathname=parsed.pathname.replace(/\/\d+px-([^/]+)$/i,'/$1');
  url=`${parsed.hostname.toLocaleLowerCase()}${parsed.pathname}${parsed.search}`;
 }catch{url=url.toLocaleLowerCase().split(/[?#]/,1)[0];}
 return url;
}

export {normalizedTitle as normalizedImageTitle};

export function hammingDistance(left:string,right:string){
 if(left.length!==right.length)return Number.POSITIVE_INFINITY;
 let distance=0;for(let i=0;i<left.length;i++)if(left[i]!==right[i])distance++;
 return distance;
}

export function isNearDuplicateHash(candidate:string,accepted:string[],maxDistance=1){
 return accepted.some(hash=>hammingDistance(candidate,hash)<=maxDistance);
}

export function partitionWallImages<T>(images:T[],offset=0,rowCount=4):T[][]{
 if(!images.length||rowCount<1)return [];
 const start=((Math.max(0,Math.floor(offset))%images.length)+images.length)%images.length;
 const rotated=images.slice(start).concat(images.slice(0,start));
 const rows=Array.from({length:Math.min(rowCount,rotated.length)},()=>[] as T[]);
 rotated.forEach((image,index)=>rows[index%rows.length].push(image));
 return rows;
}
