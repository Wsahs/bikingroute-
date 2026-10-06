(function(root){
'use strict';
function formatPlace(feature){
 const p=feature.properties||{},coords=feature.geometry?.coordinates;
 if(!Array.isArray(coords)||!coords.slice(0,2).every(Number.isFinite)||coords.length<2||Math.abs(coords[0])>180||Math.abs(coords[1])>90)return null;
 const street=[p.housenumber,p.street].filter(Boolean).join(' '),city=p.city||p.town||p.village||p.locality;
 const state=p.state==='Florida'?'FL':p.state;
 const region=[state,p.postcode].filter(Boolean).join(' ');
 const label=[street||p.name,city,region].filter(Boolean).join(', ');
 if(!street&&!p.name)return null;
 return {id:String(p.osm_type||'')+String(p.osm_id||label),label,name:p.name||'',lat:coords[1],lon:coords[0],kind:p.housenumber?'Address':p.name?'Place':'Street — add a house number for a specific address'};
}
function attach({input,list,status,region,onEdit,onChoose}){
 let serial=0,timer,controller,items=[],active=-1;const cache=new Map();
 function close(){list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;}
 function choose(item){serial++;clearTimeout(timer);controller?.abort();input.value=item.label;close();status.textContent='Selected: '+item.label;onChoose(item);}
 function paint(results){items=results;active=-1;list.replaceChildren();input.removeAttribute('aria-activedescendant');list.hidden=!results.length;input.setAttribute('aria-expanded',String(!!results.length));results.forEach((item,index)=>{
  const option=document.createElement('button');option.type='button';option.id=input.id+'-option-'+index;option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.className='address-option';
  const title=document.createElement('strong');title.textContent=item.label;const detail=document.createElement('span');detail.textContent=item.name&&item.name!==item.label?item.name+' · '+item.kind:item.kind;option.append(title,detail);option.onclick=()=>choose(item);list.append(option);
 });}
 input.addEventListener('input',()=>{
  const id=++serial;clearTimeout(timer);controller?.abort();onEdit();close();items=[];const query=input.value.trim();
  if(!query){status.textContent='Type an address or place name.';return;}
  status.textContent='Finding matching addresses…';
  const area=region(),key=area+':'+query.toLowerCase();
  if(cache.has(key)){paint(cache.get(key));status.textContent=items.length+' suggestions. Select the correct address.';return;}
  timer=setTimeout(async()=>{
   controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),12000);
   try{
    let results=[];
    const local=await fetch('/api/addresses?'+new URLSearchParams({q:query,dataset:area}),{signal:controller.signal});
    if(local.ok){const data=await local.json();results=data.results||[];}
    if(id!==serial)return;
    if(!results.length){
     const url=new URL('https://photon.komoot.io/api/');url.search=new URLSearchParams({q:query,limit:'6',lang:'en',lat:area==='boca'?'26.375':'26.025',lon:area==='boca'?'-80.12':'-80.16',bbox:'-80.55,25.2,-79.95,27.05'});
     const response=await fetch(url,{signal:controller.signal,referrerPolicy:'no-referrer'});if(!response.ok)throw Error('Search unavailable');const data=await response.json();if(id!==serial)return;
     const seen=new Set();results=(data.features||[]).map(formatPlace).filter(p=>p&&!seen.has(p.label)&&seen.add(p.label));
    }cache.set(key,results);if(cache.size>60)cache.delete(cache.keys().next().value);
    paint(results);status.textContent=results.length?'Select the correct address below.':'No match found. Try the street name and city.';
   }catch(e){if(id===serial){close();status.textContent='Address search is unavailable. Keep your text and try again.';}}
   finally{clearTimeout(timeout);}
  },350);
 });
 input.addEventListener('keydown',event=>{
  if(event.key==='Escape'){close();return;}
  if(event.key==='ArrowDown'||event.key==='ArrowUp'){
   if(!items.length)return;event.preventDefault();list.hidden=false;input.setAttribute('aria-expanded','true');active=(active+(event.key==='ArrowDown'?1:-1)+items.length)%items.length;
   Array.from(list.children).forEach((el,i)=>el.setAttribute('aria-selected',String(i===active)));input.setAttribute('aria-activedescendant',list.children[active].id);
  }
  if(event.key==='Enter'&&!list.hidden&&items.length){event.preventDefault();choose(items[Math.max(0,active)]);}
 });
 input.addEventListener('focus',()=>{if(items.length){list.hidden=false;input.setAttribute('aria-expanded','true');}});
 document.addEventListener('pointerdown',event=>{if(!input.parentElement.contains(event.target))close();});
 return {reset(){serial++;clearTimeout(timer);controller?.abort();input.value='';items=[];close();status.textContent='';}};
}
const api={formatPlace,attach};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.SidepathAddress=api;
})(typeof window==='undefined'?{}:window);
