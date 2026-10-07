'use strict';
const $=id=>document.getElementById(id);
const sidewalkMode=document.body.dataset.planner==='sidewalk';
let map,routeLines=[],pins=[],routes=[],routeRevision=0,mapReady=false;
const places={start:null,end:null};
let crossingDecisions={};
let sidewalkEvidenceLayer,evidenceRevision=0;
const searchRevisions={start:0,end:0};
const inputTimers={};
const searchSessions={start:crypto.randomUUID(),end:crypto.randomUUID()};
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
async function api(path,payload,signal){const response=await fetch(path,{method:payload?'POST':'GET',headers:payload?{'Content-Type':'application/json'}:{},body:payload?JSON.stringify(payload):undefined,signal});const data=await response.json();if(!response.ok)throw new Error(data.error||'Could not complete the request.');return data;}
function updateButton(){ $('find').disabled=!(mapReady&&places.start&&places.end); }
function resetRoute(keepCrossings=false){evidenceRevision++;if(sidewalkEvidenceLayer)sidewalkEvidenceLayer.setMap(null);if(!keepCrossings)crossingDecisions={};routeRevision++;routes=[];routeLines.forEach(line=>line.setMap(null));routeLines=[];$('route-options').replaceChildren();$('route-details').hidden=true;document.getElementById('coverage-card')?.remove();updateButton();}
function updatePins(){pins.forEach(pin=>pin.setMap(null));pins=[];if(!map)return;for(const [key,label] of [['start','A'],['end','B']])if(places[key])pins.push(new google.maps.Marker({map,position:places[key].location,label:{text:label,color:'#fff',fontWeight:'700'},icon:{path:google.maps.SymbolPath.CIRCLE,scale:13,fillColor:key==='start'?'#204f3b':'#769d43',fillOpacity:1,strokeColor:'#fff',strokeWeight:3}}));}
function closeResults(key){$(key+'-results').hidden=true;$(key).setAttribute('aria-expanded','false');}
async function choose(key,prediction){
 const revision=++searchRevisions[key];clearTimeout(inputTimers[key]);closeResults(key);
 status('Checking the selected address…');
 try{
  const place=await api('/api/google/place?'+new URLSearchParams({id:prediction.id,session:searchSessions[key]}));
  if(revision!==searchRevisions[key])return;
  const location={lat:place.location?.latitude,lng:place.location?.longitude};
  if(!Number.isFinite(location.lat)||!Number.isFinite(location.lng))throw new Error('Google did not return a map location for this place. Choose another suggestion.');
  searchSessions[key]=crypto.randomUUID();places[key]={...place,location};
  $(key).value=place.formattedAddress||prediction.label;resetRoute();updatePins();
  if(map){map.panTo(location);map.setZoom(14);}
  status(places.start&&places.end?'Ready when you are. Find your route.':'Location selected. Add the other end of your ride.');
 }catch(error){if(revision===searchRevisions[key])status(error.message,true);}
}
for(const key of ['start','end']){
 $(key).addEventListener('input',()=>{places[key]=null;resetRoute();updatePins();clearTimeout(inputTimers[key]);const revision=++searchRevisions[key];const query=$(key).value.trim();closeResults(key);if(!query)return;inputTimers[key]=setTimeout(async()=>{const list=$(key+'-results');list.replaceChildren();const note=document.createElement('span');note.className='search-note';note.textContent='Searching Google Maps…';list.append(note);list.hidden=false;$(key).setAttribute('aria-expanded','true');try{const result=await api('/api/google/autocomplete?'+new URLSearchParams({q:query,session:searchSessions[key]}));if(revision!==searchRevisions[key])return;list.replaceChildren();for(const place of result.suggestions||[]){const button=document.createElement('button');button.type='button';button.setAttribute('role','option');const title=document.createElement('strong'),address=document.createElement('small');title.textContent=place.label;address.textContent='Select this location';button.append(title,address);button.onclick=()=>choose(key,place);list.append(button);}const credit=document.createElement('span');credit.className='search-note';credit.textContent=result.suggestions?.length?'Google Maps':'No places found. Try a complete address and city.';list.append(credit);}catch(error){if(revision!==searchRevisions[key])return;list.replaceChildren();const note=document.createElement('span');note.className='search-note';note.textContent=error.message;list.append(note);}},250);});
 $(key).addEventListener('keydown',event=>{const list=$(key+'-results');if(event.key==='Escape'){searchRevisions[key]++;closeResults(key);}if(event.key==='ArrowDown'&&!list.hidden){event.preventDefault();list.querySelector('button')?.focus();}if(event.key==='Enter'){event.preventDefault();if(!list.hidden)list.querySelector('button')?.click();else if(places.start&&places.end)$('trip-form').requestSubmit();}});
 $(key+'-results').addEventListener('keydown',event=>{if(event.key==='Escape'){closeResults(key);$(key).focus();}if(event.key==='ArrowDown'){event.preventDefault();event.target.nextElementSibling?.focus();}if(event.key==='ArrowUp'){event.preventDefault();if(event.target.previousElementSibling)event.target.previousElementSibling.focus();else $(key).focus();}});
}
document.addEventListener('click',event=>{for(const key of ['start','end'])if(!$(key).parentElement.contains(event.target))closeResults(key);});
$('swap').onclick=()=>{for(const key of ['start','end']){searchRevisions[key]++;clearTimeout(inputTimers[key]);closeResults(key);} [places.start,places.end]=[places.end,places.start];[$('start').value,$('end').value]=[$('end').value,$('start').value];resetRoute();updatePins();status('Locations swapped. Find your new route.');};
function decodePolyline(encoded){let index=0,lat=0,lng=0;const path=[];while(index<encoded.length){const values=[];for(let i=0;i<2;i++){let shift=0,result=0,b;do{b=encoded.charCodeAt(index++)-63;result|=(b&31)<<shift;shift+=5;}while(b>=32);values.push(result&1?~(result>>1):result>>1);}lat+=values[0];lng+=values[1];path.push({lat:lat/1e5,lng:lng/1e5});}return path;}
function minutes(route){return Math.round(parseFloat(route.duration||'0')/60);}
function miles(distance){return (distance/1609.344).toFixed(1)+' mi';}
function fitRoute(path,includeAddresses=true){if(!path?.length)return;if(!includeAddresses){map.setCenter(path[Math.floor(path.length/2)]);map.setZoom(19);return;}const bounds=new google.maps.LatLngBounds();path.forEach(point=>bounds.extend(point));if(sidewalkMode&&includeAddresses)for(const place of Object.values(places))if(place)bounds.extend(place.location);map.fitBounds(bounds,{top:85,right:45,bottom:110,left:45});}
function selectRoute(index){routeLines.forEach(line=>line.setMap(null));routeLines=[];document.querySelectorAll('.route-option').forEach((button,i)=>{button.classList.toggle('selected',i===index);button.setAttribute('aria-pressed',String(i===index));});const route=routes[index],path=route.path||decodePolyline(route.polyline.encodedPolyline);for(const [color,weight] of [['#ffffff',10],['#204f3b',6]])routeLines.push(new google.maps.Polyline({map,path,strokeColor:color,strokeOpacity:1,strokeWeight:weight,zIndex:3}));for(const segment of route.streetSegments||[])routeLines.push(new google.maps.Polyline({map,path:segment,strokeColor:'#dc303b',strokeWeight:7,zIndex:4}));fitRoute(path);$('fit').onclick=()=>fitRoute(path);$('route-details').hidden=false;$('directions').replaceChildren();let count=0;for(const leg of route.legs||[])for(const step of leg.steps||[]){const li=document.createElement('li'),number=document.createElement('span'),copy=document.createElement('div'),distance=document.createElement('small');if(step.kind==='street')li.className='road';number.className='step-number';number.textContent=++count;copy.textContent=step.navigationInstruction?.instructions||'Continue along the route';distance.textContent=step.distanceMeters?(step.distanceMeters<160?Math.round(step.distanceMeters*3.28084)+' ft':miles(step.distanceMeters)):'Arrive';copy.append(distance);li.append(number,copy);$('directions').append(li);}$('warnings').textContent=[...(route.warnings||[]),...(sidewalkMode?[]:['Google cycling routes may use streets and do not guarantee a sidewalk-only ride.'])].join(' ');$('open-google').href='https://www.google.com/maps/dir/?'+new URLSearchParams({api:'1',origin:places.start.formattedAddress,destination:places.end.formattedAddress,origin_place_id:places.start.id,destination_place_id:places.end.id,travelmode:'bicycling'});status(sidewalkMode?'Mapped path shown. Check the unverified approaches before using this route.':'Route found by Google Maps. Select a route to compare your options.');}
$('trip-form').onsubmit=async event=>{event.preventDefault();if(!places.start||!places.end||!mapReady)return;resetRoute();const revision=routeRevision;$('find').disabled=true;status(sidewalkMode?'Finding connected sidewalks and trails…':'Finding your cycling route with Google Maps…');try{if(sidewalkMode){await findSidewalkRoute(revision);return;}const result=await api('/api/google/route',{origin:places.start.id,destination:places.end.id});if(revision!==routeRevision)return;routes=(result.routes||[]).filter(route=>route.polyline?.encodedPolyline).sort((a,b)=>a.distanceMeters-b.distanceMeters);if(!routes.length){status('Google did not return a cycling route for these locations. Try another destination.',true);return;}routes.forEach((route,index)=>{const button=document.createElement('button');button.type='button';button.className='route-option';const copy=document.createElement('span'),time=document.createElement('strong'),label=document.createElement('small'),distance=document.createElement('span');time.textContent=minutes(route)+' min';label.textContent=index===0?'Shortest returned cycling route':'Alternative '+index;distance.textContent=miles(route.distanceMeters);copy.append(time,label);button.append(copy,distance);button.onclick=()=>selectRoute(index);$('route-options').append(button);});selectRoute(0);}catch(error){if(revision===routeRevision)status(error.message,true);}finally{if(revision===routeRevision)updateButton();}};
function setMapStyle(style){if(map)map.setMapTypeId(style==='satellite'?'satellite':'roadmap');$('street').classList.toggle('selected',style==='street');$('satellite').classList.toggle('selected',style==='satellite');}
$('street').onclick=()=>setMapStyle('street');$('satellite').onclick=()=>setMapStyle('satellite');
function mapError(text){$('map-error').textContent=text;$('map-error').hidden=false;status(text,true);mapReady=false;updateButton();}
window.gm_authFailure=()=>mapError('Google rejected the map key. Check Google Maps access for this demo key.');
window.initSidepath=()=>{map=new google.maps.Map($('map'),{center:{lat:26.365,lng:-80.115},zoom:13,disableDefaultUI:true,zoomControl:true,zoomControlOptions:{position:google.maps.ControlPosition.RIGHT_CENTER},streetViewControl:true,fullscreenControl:true,gestureHandling:'greedy',isFractionalZoomEnabled:true,styles:[{featureType:'poi',elementType:'labels',stylers:[{visibility:'off'}]},{featureType:'landscape',elementType:'geometry',stylers:[{color:'#f1f3e9'}]},{featureType:'water',elementType:'geometry',stylers:[{color:'#b9d9df'}]},{featureType:'road',elementType:'geometry',stylers:[{color:'#ffffff'}]}]});attachMapGestures($('map'),map);new google.maps.BicyclingLayer().setMap(map);mapReady=true;updateButton();status('Search for an address or a place to get started.');};
(async()=>{try{const config=await api('/api/google/config');if(!config.browserKey)throw new Error('A Google Maps browser key is needed to load this map.');const script=document.createElement('script');script.src='https://maps.googleapis.com/maps/api/js?'+new URLSearchParams({key:config.browserKey,callback:'initSidepath',loading:'async',v:'weekly'});script.async=true;script.onerror=()=>mapError('Google Maps could not load. Check your internet connection.');document.head.append(script);}catch(error){mapError(error.message);}})();

if($('sidewalk-area'))$('sidewalk-area').onchange=()=>{resetRoute();status('Mapping area changed. Find a route to search this area.');};
function mappedRoute(route,result){
 return {distanceMeters:route.distance_m,duration:String(route.duration_seconds)+'s',path:route.segments.flatMap(s=>s.geometry.map(p=>({lat:p[1],lng:p[0]}))),streetSegments:route.segments.filter(s=>(s.kind==='street'||s.crossing_option)).map(s=>s.geometry.map(p=>({lat:p[1],lng:p[0]}))),warnings:result.warnings||[],legs:[{steps:(route.directions||[]).map(step=>({navigationInstruction:{instructions:step.instruction},distanceMeters:step.distance_m,kind:step.kind}))}]};
}
async function findSidewalkRoute(revision){
 const result=await api('/api/sidewalk-trip',{dataset:$('sidewalk-area').value,origin:places.start.location,destination:places.end.location,crossing_choices:crossingDecisions});
 if(revision!==routeRevision)return;
 const card=document.createElement('div');card.id='coverage-card';card.className='coverage-card';
 const heading=document.createElement('strong'),note=document.createElement('p');card.append(heading,note);$('route-options').before(card);
 addSidewalkEvidenceControls(card);
 if(!result.primary&&!result.alternative&&!result.crossing_proposal){heading.textContent='We cannot verify this trip yet';note.textContent=result.message||'Sidewalk coverage is incomplete here. This does not prove there is no sidewalk route.';const back=document.createElement('a');back.href='/';back.textContent='Use the Google cycling planner →';card.append(back);status('No complete mapped connection found. Your selected addresses are kept.');return;}
 heading.textContent='Mapped path — address connections unverified';
 function describeApproaches(approaches){note.textContent='Start: '+Math.round(approaches.origin.distance_m)+' m from the mapped path. Destination: '+Math.round(approaches.destination.distance_m)+' m from the mapped path. These are straight-line distances, not verified riding connections. They are excluded from the time and distance below.';}
 describeApproaches(result.approaches||result.proposal_approaches);
 const legend=document.createElement('p');legend.textContent='Route data: OpenStreetMap and Palm Beach County. Green: mapped route. Red: street riding or unmarked crossings; a preview is not an approved route. Map pins mark your addresses; the route line may stop before them.';card.append(legend);

 function show(route,label){routes=[mappedRoute(route,result)];$('route-options').replaceChildren();const button=document.createElement('button');button.className='route-option';button.type='button';button.textContent=minutes(routes[0])+' min · '+miles(route.distance_m)+' · '+label;button.onclick=()=>selectRoute(0);$('route-options').append(button);selectRoute(0);}
 if(result.primary)show(result.primary,result.primary.segments.some(s=>s.crossing_option)?'Includes approved unmarked crossings':'Mapped sidewalks & trails');
 if(result.crossing_proposal){
  const section=document.createElement('section'),title=document.createElement('strong'),summary=document.createElement('p'),preview=document.createElement('button');
  title.textContent='Review each unmarked crossing';
  summary.textContent=miles(result.crossing_proposal.distance_m)+' mapped route · '+result.crossing_choices.length+' crossing choices remain. '+result.proposal_message;
  preview.type='button';preview.className='street-choice';preview.textContent='Preview crossings on the map';
  preview.onclick=()=>{describeApproaches(result.proposal_approaches);routes=[mappedRoute(result.crossing_proposal,{...result,warnings:[result.proposal_message]})];$('route-options').replaceChildren();const label=document.createElement('p');label.textContent='Preview only — crossings not yet approved';$('route-options').append(label);selectRoute(0);status('Preview only. Red crossing segments need individual approval.');};
  section.append(title,summary,preview);
  for(const [crossingIndex,crossing] of result.crossing_choices.entries()){
   const row=document.createElement('div'),text=document.createElement('p'),yes=document.createElement('button'),no=document.createElement('button');
   text.textContent='Crossing '+(crossingIndex+1)+': '+crossing.name+' · '+Math.round(crossing.distance_m*3.28084)+' ft across. '+crossing.warning;
   for(const button of [yes,no]){button.type='button';button.className='street-choice';}
   yes.textContent='Yes — allow this crossing';no.textContent='No — avoid this crossing';
   const choose=async allowed=>{crossingDecisions[crossing.id]=allowed;resetRoute(true);const next=routeRevision;status('Recalculating with your crossing choice…');$('find').disabled=true;try{await findSidewalkRoute(next);}catch(error){if(next===routeRevision)status(error.message,true);}finally{if(next===routeRevision)updateButton();}};
   const focus=document.createElement('button');focus.type='button';focus.className='street-choice';focus.textContent='Show this crossing';focus.onclick=()=>{preview.onclick();fitRoute(crossing.geometry.map(p=>({lat:p[1],lng:p[0]})),false);status('Previewing crossing '+(crossingIndex+1)+': '+crossing.name+'. This crossing is not approved.');};
   yes.onclick=()=>choose(true);no.onclick=()=>choose(false);row.append(text,focus,yes,no);section.append(row);
  }
  card.append(section);
  if(!result.primary)status('A route may be possible with unmarked crossings. Review each choice first.');
 }

 if(result.alternative){
  const panel=document.createElement('div'),accept=document.createElement('button'),decline=document.createElement('button'),copy=document.createElement('p');
  copy.textContent=(result.primary?'Optional street shortcut':'No continuous sidewalk-only route was found in our data')+': '+miles(result.alternative.street_distance_m)+' of street riding.'+(result.extra_seconds?' Saves about '+Math.round(result.extra_seconds/60)+' minutes.':'');
  accept.className=decline.className='street-choice';accept.textContent='Yes — show this street alternative';decline.textContent='No — keep streets out';
  accept.onclick=()=>{show(result.alternative,'Includes street riding');panel.remove();};decline.onclick=()=>{panel.remove();if(!result.primary)status('Street alternative declined. We cannot verify a sidewalk-only route for this trip yet.');};panel.append(copy,accept,decline);card.append(panel);
 }
}

function addSidewalkEvidenceControls(card){
 const evidenceNote=document.createElement('p');evidenceNote.textContent='Missing address connection? Inspect the county’s mapped sidewalks nearby. These outlines are evidence, not directions.';card.append(evidenceNote);
 for(const [key,label] of [['start','starting point'],['end','destination']]){
  const inspect=document.createElement('button');inspect.type='button';inspect.className='street-choice';inspect.textContent='Show sidewalks near '+label;
  inspect.onclick=async()=>{const revision=++evidenceRevision;inspect.disabled=true;try{const p=places[key].location;const data=await api('/api/sidewalk-evidence?'+new URLSearchParams({lat:p.lat,lon:p.lng}));if(revision!==evidenceRevision)return;if(sidewalkEvidenceLayer)sidewalkEvidenceLayer.setMap(null);sidewalkEvidenceLayer=new google.maps.Data({map});sidewalkEvidenceLayer.addGeoJson(data);sidewalkEvidenceLayer.setStyle({strokeColor:'#bc790d',strokeWeight:3,strokeOpacity:.8,clickable:false,zIndex:1});map.setCenter(p);map.setZoom(18);status(data.features.length?data.notice+(data.truncated?' Only part of the available evidence is displayed.':''):'No sidewalk evidence was returned here. This does not prove sidewalks are absent.');}catch(error){if(revision===evidenceRevision)status(error.message,true);}finally{inspect.disabled=false;}};card.append(inspect);
 }
 const hideEvidence=document.createElement('button');hideEvidence.type='button';hideEvidence.className='street-choice';hideEvidence.textContent='Hide county sidewalk outlines';hideEvidence.onclick=()=>{evidenceRevision++;if(sidewalkEvidenceLayer)sidewalkEvidenceLayer.setMap(null);status('County sidewalk outlines hidden.');};card.append(hideEvidence);

}
