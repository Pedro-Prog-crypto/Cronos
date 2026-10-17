// Trusted optional components. Layout stays in the generated HTML/CSS; no network,
// persistence, checkout or continuous animation is introduced by these controls.
(()=>{
 const money=cents=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(cents/100);
 const normalize=value=>String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const cents=item=>Math.round(Number(item.dataset.price)*100);
 const collections=[],basket=new Map();let cart=null;
 const button=(text,label,action)=>{const b=document.createElement('button');b.type='button';b.textContent=text;b.setAttribute('aria-label',label);b.addEventListener('click',action);return b;};
 function renderCart(){
  if(!cart)return;
  const list=cart.querySelector('[data-cart-items]'),total=cart.querySelector('[data-cart-total]'),count=cart.querySelector('[data-cart-count]');
  if(!list||!total||!count)return;
  let quantity=0,sum=0;const rows=[];
  for(const [id,entry] of basket){
   quantity+=entry.quantity;sum+=entry.quantity*entry.price;
   const row=document.createElement('li');row.className='studio-cart-row';row.dataset.cartItem=id;
   const title=document.createElement('span');title.textContent=entry.title+' · '+entry.quantity+' × '+money(entry.price);
   row.append(title,
    button('−','Diminuir '+entry.title,()=>{entry.quantity--;if(!entry.quantity)basket.delete(id);renderCart();}),
    button('+','Aumentar '+entry.title,()=>{entry.quantity=Math.min(99,entry.quantity+1);renderCart();}),
    button('Remover','Remover '+entry.title,()=>{basket.delete(id);renderCart();}));
   rows.push(row);
  }
  if(!rows.length){const row=document.createElement('li');row.textContent='Seu carrinho está vazio.';rows.push(row);}
  list.replaceChildren(...rows);total.textContent=money(sum);total.dataset.cartCents=String(sum);count.textContent=String(quantity);
 }
 function install(){
  cart=document.querySelector('[data-studio-cart]');
  for(const root of [...document.querySelectorAll('[data-studio-collection]')].slice(0,8)){
   const items=[...root.querySelectorAll('[data-item]')].filter(item=>item.closest('[data-studio-collection]')===root).slice(0,200);
   const search=root.querySelector('[data-collection-search]'),filter=root.querySelector('[data-collection-filter]'),sort=root.querySelector('[data-collection-sort]');
   const empty=root.querySelector('[data-collection-empty]'),count=root.querySelector('[data-collection-count]');
   const refresh=()=>{
    const term=normalize(search?.value||'').trim(),category=filter?.value||'',order=sort?.value||'default';
    const ordered=items.map((item,index)=>({item,index}));
    if(order!=='default')ordered.sort((a,b)=>(order==='name'?a.item.dataset.title.localeCompare(b.item.dataset.title,'pt-BR'): (cents(a.item)-cents(b.item))*(order==='price-desc'?-1:1))||a.index-b.index);
    // Append only to the original item container; controls keep their positions.
    if(sort&&items.length&&items.every(item=>item.parentElement===items[0].parentElement)){
     const container=items[0].parentElement;for(const {item} of ordered)container.append(item);
    }
    let found=0;
    for(const item of items){item.hidden=Boolean((category&&item.dataset.category!==category)||(term&&!normalize(item.dataset.title+' '+item.textContent).includes(term)));if(!item.hidden)found++;}
    if(empty)empty.hidden=found!==0;if(count)count.textContent=found+' resultado(s)';
   };
   search?.addEventListener('input',refresh);filter?.addEventListener('change',refresh);sort?.addEventListener('change',refresh);
   root.querySelector('[data-collection-reset]')?.addEventListener('click',()=>{if(search)search.value='';if(filter)filter.value='';if(sort)sort.value='default';refresh();});
   for(const item of items){
    const add=item.querySelector('[data-cart-add]');if(!add||!cart)continue;
    add.addEventListener('click',()=>{
     const id=item.dataset.item,price=cents(item);if(!id||!Number.isSafeInteger(price)||price<0||price>999999999)return;
     const entry=basket.get(id)||{title:item.dataset.title||'Item',price,quantity:0};entry.quantity=Math.min(99,entry.quantity+1);basket.set(id,entry);renderCart();
    });
   }
   root.dataset.collectionReady='true';refresh();collections.push({root,items,search,filter,sort,refresh});
  }
  renderCart();
 }
 const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
 async function tests(){
  const checks=[];const add=(name,ok,detail)=>checks.push({name,status:ok?'passed':'failed',detail});
  const y=scrollY,x=scrollX,focus=document.activeElement;
  try{
   for(const {items,search,filter,sort,refresh} of collections){
    const old={search:search?.value,filter:filter?.value,sort:sort?.value};
    try{
     if(filter)filter.value='';if(search)search.value='';if(sort)sort.value='default';refresh();
     if(search){search.value='__cronos_sem_resultado_7e93__';search.dispatchEvent(new Event('input',{bubbles:true}));await tick();add('Busca: estado sem resultados',items.length>0&&items.every(item=>item.hidden&&getComputedStyle(item).display==='none'),'Consulta inexistente deve ocultar os itens. Nenhuma pesquisa externa é enviada.');search.value=items[0]?.dataset.title||'';search.dispatchEvent(new Event('input',{bubbles:true}));await tick();add('Busca: item encontrado',Boolean(items[0]&&!items[0].hidden&&getComputedStyle(items[0]).display!=='none'),'Busca pelo nome do primeiro item, incluindo acentos.');search.value='';refresh();}
     if(filter){const category=items[0]?.dataset.category;filter.value=category||'';filter.dispatchEvent(new Event('change',{bubbles:true}));await tick();add('Filtro: categoria selecionada',Boolean(category)&&items.every(item=>item.hidden===(item.dataset.category!==category)&&(item.hidden?getComputedStyle(item).display==='none':getComputedStyle(item).display!=='none')),'Itens de outras categorias precisam ser ocultados.');filter.value='';refresh();}
     if(sort){for(const order of ['price-asc','price-desc']){sort.value=order;sort.dispatchEvent(new Event('change',{bubbles:true}));await tick();const sequence=items[0]?.parentElement?[...items[0].parentElement.children].filter(item=>item.hasAttribute('data-item')).map(cents):[];add('Ordenação: '+order,sequence.length>0&&sequence.every((v,i)=>Number.isFinite(v)&&(!i||(order==='price-asc'?v>=sequence[i-1]:v<=sequence[i-1]))),'A ordem foi observada nos elementos reais, sem confiar na resposta da IA.');}}
    }finally{if(search)search.value=old.search;if(filter)filter.value=old.filter;if(sort)sort.value=old.sort;refresh();}
   }
   if(cart){
    const saved=new Map([...basket].map(([id,entry])=>[id,{...entry}]));
    try{
     basket.clear();renderCart();const item=collections.flatMap(c=>c.items).find(item=>item.querySelector('[data-cart-add]'));
     const addButton=item?.querySelector('[data-cart-add]');addButton?.click();await tick();addButton?.click();await tick();
     const total=cart.querySelector('[data-cart-total]'),count=cart.querySelector('[data-cart-count]');
     add('Carrinho: adicionar e calcular',Boolean(item)&&count?.textContent==='2'&&Number(total?.dataset.cartCents)===2*cents(item),'Duas unidades devem produzir o total exato em centavos; nenhum pagamento é efetuado.');
     cart.querySelector('[data-cart-item] button')?.click();await tick();
     add('Carrinho: diminuir quantidade',count?.textContent==='1'&&Number(total?.dataset.cartCents)===cents(item),'A redução deve recalcular quantidade e total.');
     cart.querySelector('[data-cart-item] button:last-child')?.click();await tick();
     add('Carrinho: remover e esvaziar',count?.textContent==='0'&&total?.dataset.cartCents==='0'&&!cart.querySelector('[data-cart-item]'),'Estado vazio após remover; o carrinho anterior é restaurado ao terminar o teste.');
    }finally{basket.clear();for(const [id,entry] of saved)basket.set(id,entry);renderCart();}
   }
  }finally{if(focus?.isConnected&&typeof focus.focus==='function')focus.focus({preventScroll:true});scrollTo(x,y);}
  return checks;
 }
 window.__studioFeatureTests=tests;
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
