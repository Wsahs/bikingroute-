"""Explicitly optional unmarked side-street crossings; never strict eligibility."""
from collections import defaultdict
from server.import_osm import meters

def catalog(document, policy):
 nodes={n['id']:n for n in document['elements'] if n['type']=='node'}
 ways=[w for w in document['elements'] if w['type']=='way' and 'highway' in w.get('tags',{})]
 connected=defaultdict(list)
 for w in ways:
  for n in w.get('nodes',[]):connected[n].append(w)
 result={}
 for w in ways:
  t=w['tags'];ids=w.get('nodes',[])
  if t.get('footway')!='crossing' or t.get('crossing')!='unmarked' or len(ids)<3 or any(n not in nodes for n in ids):continue
  points=[nodes[n] for n in ids]
  if not policy(points):continue
  length=sum(meters(a,b) for a,b in zip(points,points[1:]))
  if length>35:continue
  if not all(any(x['tags'].get('footway') in ('sidewalk','traffic_island') for x in connected[n] if x['id']!=w['id']) for n in (ids[0],ids[-1])):continue
  roads={x['id']:x for n in ids[1:-1] for x in connected[n] if x['tags']['highway'] not in ('footway','path','cycleway','pedestrian','steps')}
  if not roads or any(x['tags']['highway'] not in ('residential','service') for x in roads.values()):continue
  segments={frozenset(pair) for pair in zip(ids,ids[1:])}
  if any(frozenset(pair) in segments for x in roads.values() for pair in zip(x['nodes'],x['nodes'][1:])):continue
  result[str(w['id'])]={'id':str(w['id']),'name':' / '.join(sorted({x['tags'].get('name','Unnamed side street') for x in roads.values()})), 'distance_m':length,'geometry':[[n['lon'],n['lat']] for n in points], 'source':'OpenStreetMap way '+str(w['id']), 'warning':'Unmarked crossing. Traffic conditions and current accessibility have not been verified.'}
 return result

def apply_options(graph, decisions, preview=False):
 if not isinstance(decisions,dict) or len(decisions)>500 or any(not isinstance(k,str) or type(v) is not bool for k,v in decisions.items()):raise ValueError('Invalid crossing choices')
 edges=[]
 for e in graph['edges']:
  option=e.get('crossing_option');choice=decisions.get(option['id']) if option else None
  if option and (choice is True or (preview and choice is not False)):
   e=dict(e,designated=True,kind='crossing',name='Unmarked crossing: '+option['name'],approval_required=choice is not True)
  edges.append(e)
 return dict(graph,edges=edges)
