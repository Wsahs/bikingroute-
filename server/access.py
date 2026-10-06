"""Offer nearby distinct networks instead of eight vertices on one isolated path."""
from collections import defaultdict
from server.import_osm import meters

def access_points(graph,allowed,lat,lon):
 parent={};names={}
 def find(a):
  parent.setdefault(a,a)
  while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
  return a
 for e in graph['edges']:
  if not allowed(e):continue
  a,b=e['from'],e['to'];parent[find(a)]=find(b)
  for n in (a,b):names.setdefault(n,e.get('name') or 'Mapped path')
 sizes=defaultdict(int)
 for n in parent:sizes[find(n)]+=1
 candidates=[]
 for n in graph['nodes']:
  if n['id'] not in names:continue
  distance=meters({'lat':lat,'lon':lon},n)
  if distance<=500:
   component=find(n['id']);candidates.append(dict(n,name=names[n['id']],distance_m=round(distance,1),component=component,network_nodes=sizes[component]))
 candidates.sort(key=lambda p:p['distance_m']);seen=set();points=[]
 for p in candidates:
  if p['component'] not in seen:points.append(p);seen.add(p['component'])
  if len(points)==12:break
 return points
