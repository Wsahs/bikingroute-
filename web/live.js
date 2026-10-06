'use strict';
const q=id=>document.getElementById(id),map=L.map('map',{preferCanvas:true,scrollWheelZoom:false}).setView([26.375,-80.12],13);
const streetTiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'}).addTo(map);
const CountyAerial=L.TileLayer.extend({getTileUrl:SidepathImagery.tileURL}),aerialTiles=new CountyAerial('',{maxZoom:20,attribution:'2026 aerial imagery: Palm Beach County'});
q('map-style').onchange=()=>{const aerial=q('map-style').value==='aerial';map.removeLayer(aerial?streetTiles:aerialTiles);(aerial?aerialTiles:streetTiles).addTo(map);};
let networkLayer,routeLayer,evidenceLayer,focusLayer,start,end,markers={},revision=0,networkRevision=0;
function syncEvidence(){for(const layer of [networkLayer,evidenceLayer])if(layer){if(q("show-evidence").checked)layer.addTo(map);else map.removeLayer(layer);}}
q("show-evidence").onchange=syncEvidence;
q("fit-route").onclick=()=>{if(routeLayer&&routeLayer.getBounds().isValid())map.fitBounds(routeLayer.getBounds(),{padding:[35,35],animate:false});};
function googleLink(){const ready=addresses.start&&addresses.end;q("google-link").hidden=q("google-note").hidden=!ready;if(ready)q("google-link").href="https://www.google.com/maps/dir/?"+new URLSearchParams({api:"1",origin:addresses.start.lat+","+addresses.start.lon,destination:addresses.end.lat+","+addresses.end.lon,travelmode:"bicycling"});}
const addresses={start:null,end:null},searches={};
const region=()=>q('region').value;
function message(text){q('message').textContent=text;}
async function api(path,body){const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;}
function clearRoute(){revision++;googleLink();q("route-summary").hidden=true;q("fit-route").hidden=true;if(focusLayer){map.removeLayer(focusLayer);focusLayer=null;}start=end=null;if(evidenceLayer){map.removeLayer(evidenceLayer);evidenceLayer=null;}if(routeLayer){map.removeLayer(routeLayer);routeLayer=null;}q('access').replaceChildren();q('choices').replaceChildren();q('directions').replaceChildren();q('route').disabled=!(addresses.start&&addresses.end);}
for(const key of ['start','end']){
 searches[key]=SidepathAddress.attach({input:q(key+'-address'),list:q(key+'-suggestions'),status:q(key+'-search-status'),region,
  onEdit(){addresses[key]=null;if(markers[key]){map.removeLayer(markers[key]);delete markers[key];}clearRoute();message('Select the correct suggestion for each address.');},
  onChoose(place){addresses[key]=place;clearRoute();if(markers[key])map.removeLayer(markers[key]);markers[key]=L.circleMarker([place.lat,place.lon],{radius:7,color:key==='start'?'#255e45':'#173e7a'}).addTo(map);map.setView([place.lat,place.lon],15,{animate:false});message(addresses.start&&addresses.end?'Both addresses selected. Let’s find the mapped route.':'Address selected. Enter the other location.');}
 });
}
async function load(resetLocations=true){
 if(resetLocations){for(const key of ['start','end']){addresses[key]=null;searches[key].reset();if(markers[key])map.removeLayer(markers[key]);}markers={};}
 clearRoute();const current=++networkRevision;message('Loading assessed network…');if(networkLayer)map.removeLayer(networkLayer);map.setView(region()==='boca'?[26.375,-80.12]:[26.025,-80.16],13);
 try{const data=await api('/api/network?display=1&dataset='+region()+'&mode='+q('mode').value);if(current!==networkRevision)return;networkLayer=L.geoJSON(data,{style:{color:'#428056',weight:2,opacity:.7},onEachFeature:(f,layer)=>layer.bindTooltip(f.properties.name||'Mapped path')});syncEvidence();message('Enter your starting location and destination above. '+data.segment_count+' mapped connections available.');}catch(e){if(current===networkRevision)message(e.message);}
}
async function calculate(){
 if(!start||!end)return;
 const current=++revision;q('route-summary').hidden=true;q('fit-route').hidden=true;if(focusLayer){map.removeLayer(focusLayer);focusLayer=null;}q('route').disabled=true;q('choices').replaceChildren();q('directions').replaceChildren();if(routeLayer){map.removeLayer(routeLayer);routeLayer=null;}message('Searching connected mapped paths…');
 try{const result=await api('/api/route',{dataset:region(),start:start.id,end:end.id,mode:q('mode').value});if(current!==revision)return;if(result.primary)showRoute(result.primary);else message('Our mapped connections are incomplete for this trip. This does not mean there is no sidewalk route. Enable “Show sidewalk mapping evidence” to inspect unverified county connections.');if(!result.primary&&result.alternative){const b=document.createElement('button');b.textContent='Use disclosed street fallback ('+(result.alternative.street_distance_m/1609.344).toFixed(2)+' street miles)';b.onclick=()=>showRoute(result.alternative);q('choices').append(b);}}catch(e){if(current===revision)message(e.message);}finally{if(current===revision)q('route').disabled=!(addresses.start&&addresses.end);}
}
q('route').onclick=async()=>{
 if(!addresses.start||!addresses.end)return;
 if(start&&end){await calculate();return;}
 const current=++revision;q('route').disabled=true;q('access').replaceChildren();q('choices').replaceChildren();message('Checking mapped paths near your addresses…');
 try{
  const results=await Promise.all(['start','end'].map(key=>{const p=addresses[key];return api('/api/access?dataset='+region()+'&mode='+q('mode').value+'&lat='+p.lat+'&lon='+p.lon);}));
  if(current!==revision)return;
  const evidence=results.flatMap(r=>r.sidewalk_evidence?.features||[]);
  if(evidence.length)evidenceLayer=L.geoJSON({type:'FeatureCollection',features:evidence},{style:{color:'#b57925',weight:3,opacity:.75,dashArray:'5 5'}});syncEvidence();
  if(results.some(r=>!r.points.length)){message((evidence.length?'County records show sidewalks nearby; turn on mapping evidence to inspect them. We still need to connect them correctly. ':'')+'We found your addresses, but cannot verify a nearby path connection for '+results.map((r,i)=>r.points.length?null:i===0?'the starting location':'the destination').filter(Boolean).join(' and ')+'. Your addresses are kept. This is incomplete coverage, not proof that no sidewalk exists.');return;}
  const common=new Set(results[0].points.map(p=>p.component).filter(c=>results[1].points.some(p=>p.component===c)));
  if(!common.size){message('Sidewalks and paths are mapped near both addresses, but our data does not yet connect them into one continuous route. This is a mapping gap, not proof that sidewalks do not exist. Enable “Show sidewalk mapping evidence” to inspect county records; we cannot give complete directions for this trip yet.');return;}
  for(const result of results)result.points=result.points.filter(p=>common.has(p.component));
  message('Nearby paths found. Address-to-path connections are not verified yet. Confirm where you can join and leave the mapped network; the calculated route will cover those points only.');
  const panel=document.createElement('div');panel.className='access-picker';const selects=[];
  for(let i=0;i<2;i++){
   const label=document.createElement('label');label.textContent=i===0?'Path access near starting location':'Path access near destination';label.htmlFor='confirm-access-'+i;
   const select=document.createElement('select');select.id=label.htmlFor;const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Choose a path access point';select.append(placeholder);
   for(const point of results[i].points){const option=document.createElement('option');option.value=point.id;option.textContent=point.name+' · '+Math.round(point.distance_m)+' m straight-line · approach unverified';select.append(option);}selects.push(select);panel.append(label,select);
  }
  const confirm=document.createElement('button');confirm.textContent='Use these path access points';confirm.disabled=true;
  selects.forEach(s=>s.onchange=()=>{confirm.disabled=selects.some(s=>!s.value);});
  confirm.onclick=()=>{if(current!==revision)return;start=results[0].points.find(p=>p.id===selects[0].value);end=results[1].points.find(p=>p.id===selects[1].value);calculate();};panel.append(confirm);q('choices').append(panel);
 }catch(e){if(current===revision)message(e.message);}finally{if(current===revision)q('route').disabled=!(addresses.start&&addresses.end);}
};
function formatDistance(m){return m<160?Math.round(m*3.28084/10)*10+' ft':(m/1609.344).toFixed(m<1609?2:1)+' mi';}
function showRoute(route){
 if(routeLayer)map.removeLayer(routeLayer);if(focusLayer)map.removeLayer(focusLayer);
 const all=route.segments.flatMap(s=>s.geometry.map(p=>[p[1],p[0]]));
 routeLayer=L.featureGroup().addTo(map);
 L.polyline(all,{color:'#fff',weight:12,opacity:1,lineCap:'round',interactive:false}).addTo(routeLayer);
 L.polyline(all,{color:'#0754b8',weight:9,opacity:1,lineCap:'round',interactive:false}).addTo(routeLayer);
 for(const s of route.segments)L.polyline(s.geometry.map(p=>[p[1],p[0]]),{color:s.kind==='street'?'#dc303b':'#1595ff',weight:6,opacity:1,lineCap:'round'}).addTo(routeLayer);
 for(const [p,label] of [[all[0],'A'],[all[all.length-1],'B']])if(p)L.marker(p,{icon:L.divIcon({className:'route-pin',html:label,iconSize:[30,30],iconAnchor:[15,15]})}).addTo(routeLayer);
 if(all.length){map.fitBounds(routeLayer.getBounds(),{padding:[35,35],animate:false});L.tooltip({permanent:true,direction:'top',className:'route-time',offset:[0,-10]}).setLatLng(all[Math.floor(all.length/2)]).setContent(Math.round(route.duration_seconds/60)+' min · '+(route.distance_m/1609.344).toFixed(1)+' mi').addTo(routeLayer);}
 q('fit-route').hidden=!all.length;const summary=q('route-summary');summary.hidden=false;summary.replaceChildren();
 for(const [value,label] of [[Math.round(route.duration_seconds/60)+' min','Estimated ride'],[(route.distance_m/1609.344).toFixed(2)+' mi','Mapped route'],[formatDistance(route.street_distance_m),'Street riding']]){const box=document.createElement('div'),strong=document.createElement('strong'),small=document.createElement('span');strong.textContent=value;small.textContent=label;box.append(strong,small);summary.append(box);}
 message((all.length?'':'Both selected access points are the same. No mapped riding leg is needed. ')+'Between selected path access points only. The '+Math.round(start.distance_m)+' m starting approach and '+Math.round(end.distance_m)+' m destination approach are unverified straight-line distances and are not included.');
 q('directions').replaceChildren();
 const arrows={depart:'↑',straight:'↑',left:'↰',right:'↱',uturn:'↶',cross:'⇥',arrive:'⚑'};
 for(const step of route.directions||[]){const li=document.createElement('li'),button=document.createElement('button'),icon=document.createElement('span'),copy=document.createElement('span'),title=document.createElement('strong'),detail=document.createElement('small'),dist=document.createElement('span');
  icon.className='turn-icon';icon.textContent=arrows[step.maneuver]||'↑';icon.setAttribute('aria-hidden','true');title.textContent=step.instruction;detail.textContent=[step.driveways?step.driveways+' driveway crossing'+(step.driveways===1?'':'s'):'',step.context?step.context.basis+' · Palm Beach County':'',step.kind==='street'?'Street riding':''].filter(Boolean).join(' · ');copy.className='direction-copy';copy.append(title,detail);dist.className='step-distance';dist.textContent=step.distance_m?formatDistance(step.distance_m):'';button.append(icon,copy,dist);button.setAttribute('aria-label',step.instruction+(step.distance_m?' for '+formatDistance(step.distance_m):''));
  button.onclick=()=>{if(focusLayer)map.removeLayer(focusLayer);const coords=route.segments.slice(step.segment_start,step.segment_end+1).flatMap(s=>s.geometry.map(p=>[p[1],p[0]]));focusLayer=L.polyline(coords,{color:step.kind==='street'?'#a61926':'#003f96',weight:9}).addTo(map);map.fitBounds(focusLayer.getBounds(),{padding:[45,45],maxZoom:18,animate:false});q('map').scrollIntoView({behavior:'auto',block:'center'});};
  if(step.kind==='street')li.className='road';li.append(button);q('directions').append(li);
 }
}
q('region').onchange=()=>load(true);q('mode').onchange=()=>load(false);load();
