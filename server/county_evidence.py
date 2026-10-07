"""Supplement missing OSM classification using the same county feature and geometry."""
import math
from collections import defaultdict
from server.gis_network import MARKED,SOURCE

def distance_to_line(point,line):
 scale=111320;cos=math.cos(math.radians(point[1]));best=float('inf')
 for a,b in zip(line,line[1:]):
  ax=(a[0]-point[0])*scale*cos;ay=(a[1]-point[1])*scale
  bx=(b[0]-point[0])*scale*cos;by=(b[1]-point[1])*scale
  dx=bx-ax;dy=by-ay;den=dx*dx+dy*dy
  t=max(0,min(1,-(ax*dx+ay*dy)/den)) if den else 0
  best=min(best,math.hypot(ax+t*dx,ay+t*dy))
 return best

def matches(a,b):
 if len(a)<2 or len(b)<2:return False
 # Vertex agreement alone can accept a line that shortcuts a bend or loops.
 def samples(line):
  for p,q in zip(line,line[1:]):
   length=math.hypot((q[0]-p[0])*111320*math.cos(math.radians(p[1])),(q[1]-p[1])*111320)
   count=max(1,math.ceil(length))
   for i in range(count):yield [p[0]+(q[0]-p[0])*i/count,p[1]+(q[1]-p[1])*i/count]
  yield line[-1]
 return all(distance_to_line(p,b)<=1 for p in samples(a)) and all(distance_to_line(p,a)<=1 for p in samples(b))

def supplement(document,features):
 by_way=defaultdict(list);nodes={e['id']:e for e in document['elements'] if e['type']=='node'}
 for f in features:
  p=f.get('properties') or {};kind=(p.get('Existing_T') or '').strip()
  if kind=='Sidewalk' or kind in MARKED:by_way[str(p.get('osm_id'))].append(f)
 result=[];report={'sidewalk_ways':0,'marked_crossing_ways':0,'records':[]}
 for way in document['elements']:
  tags=way.get('tags',{})
  if way.get('type')!='way' or tags.get('highway') not in ('footway','path'):result.append(way);continue
  points=[[nodes[n]['lon'],nodes[n]['lat']] for n in way.get('nodes',[]) if n in nodes]
  if len(points)!=len(way.get('nodes',[])):result.append(way);continue
  candidates=[]
  for f in by_way.get(str(way['id']),[]):
   geom=f.get('geometry') or {};lines=[geom.get('coordinates',[])] if geom.get('type')=='LineString' else geom.get('coordinates',[]) if geom.get('type')=='MultiLineString' else []
   if any(matches(points,line) for line in lines):candidates.append(f)
  kinds={(f['properties'].get('Existing_T') or '').strip() for f in candidates};updated=dict(tags);category=None
  if kinds=={'Sidewalk'} and 'footway' not in tags:
   updated['footway']='sidewalk';category='sidewalk_ways'
  elif kinds and kinds<=MARKED and tags.get('footway')=='crossing' and 'crossing' not in tags and 'crossing:markings' not in tags:
   conflicting=any(nodes[n].get('tags',{}).get('crossing') in ('no','unmarked') or nodes[n].get('tags',{}).get('crossing:markings')=='no' for n in way['nodes'])
   if not conflicting:updated['crossing']='marked';category='marked_crossing_ways'
  if category:
   ids=[f['properties'].get('OBJECTID') for f in candidates];report[category]+=1;report['records'].append({'osm_way_id':way['id'],'county_ids':ids,'classification':category})
   result.append(dict(way,tags=updated,county_evidence={'source':SOURCE,'county_ids':ids,'basis':'Shared osm_id and Bidirectional geometry sampled every metre with at most 1 metre deviation'}))
  else:result.append(way)
 return dict(document,elements=result),report
