"""Insert temporary access points on mapped segments, never between separate paths."""
import math
from server.import_osm import meters
from server.routing import eligible

def with_path_access(graph, locations):
 nodes=list(graph['nodes']);edges=[];cuts={};created={}
 for edge in graph['edges']:
  geometry=edge.get('geometry',[])
  if not eligible(edge) or len(geometry)!=2:
   edges.append(edge);continue
  a,b=geometry
  key=tuple(sorted((edge['from'],edge['to'])))
  # The same topological segment in reverse must use identical inserted nodes.
  if key not in cuts:
   candidates={}
   for point in locations:
    lat,lon=point['lat'],point['lng'];sx=111320*math.cos(math.radians(lat));sy=111320
    if not min(a[1],b[1])-.0046<=lat<=max(a[1],b[1])+.0046:continue
    if not min(a[0],b[0])-500/max(sx,1)<=lon<=max(a[0],b[0])+500/max(sx,1):continue
    ax=(a[0]-lon)*sx;ay=(a[1]-lat)*sy;dx=(b[0]-a[0])*sx;dy=(b[1]-a[1])*sy
    den=dx*dx+dy*dy
    if not den:continue
    t=max(0,min(1,-(ax*dx+ay*dy)/den))
    if t*edge['length_m']<.01 or (1-t)*edge['length_m']<.01:continue
    coord=[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])]
    if meters({'lat':lat,'lon':lon},{'lat':coord[1],'lon':coord[0]})>500:continue
    identity=tuple(round(x,10) for x in coord)
    if identity in candidates:continue
    nid='access:'+str(len(created));node={'id':nid,'lat':coord[1],'lon':coord[0]}
    created[nid]=node;nodes.append(node);candidates[identity]=node
   cuts[key]=list(candidates.values())
  selected=cuts[key]
  if not selected:edges.append(edge);continue
  dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
  if not den:edges.append(edge);continue
  parts=[(0,edge['from'],a),(1,edge['to'],b)]
  for n in selected:
   t=((n['lon']-a[0])*dx+(n['lat']-a[1])*dy)/den
   if 0<t<1:parts.append((t,n['id'],[n['lon'],n['lat']]))
  parts.sort()
  for i,(p,q) in enumerate(zip(parts,parts[1:])):
   edges.append(dict(edge,id=edge['id']+':access:'+str(i),**{'from':p[1],'to':q[1]},length_m=edge['length_m']*(q[0]-p[0]),geometry=[p[2],q[2]]))
 return dict(graph,nodes=nodes,edges=edges)
