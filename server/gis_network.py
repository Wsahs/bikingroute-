"""Import existing county pedestrian centerlines without inventing inter-source joins."""
from server.import_osm import meters
from server.routing import eligible
from collections import defaultdict
SOURCE='https://services5.arcgis.com/79IoFXBn9ZeqmVlC/ArcGIS/rest/services/Pedestrian_Facilities/FeatureServer/0'
MARKED={'Crosswalk - Standard','Crosswalk - Ladder','Crosswalk - Solid','Crosswalk - Special Emphasis'}
def merge_pedestrians(graph,features,policy,source_date='Unknown'):
 nodes={n['id']:n for n in graph['nodes'] if not n['id'].startswith('pbc:')};edges=[e for e in graph['edges'] if not e['id'].startswith('pbc:')];accepted=0
 # County osm_id supplies provenance; proximity alone is never enough.
 by_way=defaultdict(set);source_links=[];pathways=0;restricted=set()
 for edge in edges:
  if not eligible(edge):restricted.add(str(edge['id']).split(':')[0])
  if eligible(edge) and edge.get('kind') in ('sidewalk','path','trail'):
   by_way[str(edge['id']).split(':')[0]].update((edge['from'],edge['to']))
 for way in restricted:by_way.pop(way,None)
 for index,f in enumerate(features):
  p=f.get('properties') or {};kind=(p.get('Existing_T') or '').strip();g=f.get('geometry')
  source_nodes=by_way.get(str(p.get('osm_id')),set())
  if kind=='Pathway' and not source_nodes:continue
  if kind not in MARKED|{'Sidewalk','Shared Use Path','Pathway'} or not g or g['type'] not in ('LineString','MultiLineString'):continue
  lines=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
  for line_index,line in enumerate(lines):
   points=[dict(lon=c[0],lat=c[1]) for c in line];basis=policy(points)
   if not basis:continue
   accepted+=1
   if kind=='Pathway':pathways+=1
   if kind in ('Sidewalk','Shared Use Path','Pathway') and source_nodes:
    for point in (points[0],points[-1]):
     near=sorted((meters(point,nodes[n]),n) for n in source_nodes)
     # Do not choose arbitrarily between ambiguous equidistant OSM nodes.
     if near and near[0][0]<=1 and (len(near)==1 or near[1][0]-near[0][0]>.01):
      county='pbc:'+str(point['lon'])+','+str(point['lat'])
      source_links.append((county,near[0][1],near[0][0],p.get('osm_id')))

   for i,(a,b) in enumerate(zip(points,points[1:])):
    distance=meters(a,b)
    if distance<=0:continue
    # Preserve source coordinate equality. No rounding, nearest-neighbor snapping,
    # arbitrary road crossings, or inferred links to OSM geometries.
    aa='pbc:'+str(a['lon'])+','+str(a['lat']);bb='pbc:'+str(b['lon'])+','+str(b['lat'])
    nodes[aa]=dict(a,id=aa);nodes[bb]=dict(b,id=bb)
    for src,dst in [(aa,bb),(bb,aa)]:
     edges.append(dict(id=f'pbc:{index}:{line_index}:{i}:{src}',**{'from':src,'to':dst},length_m=distance,kind='crossing' if kind in MARKED else 'sidewalk' if kind=='Sidewalk' else 'path',bicycle_allowed=True,assessed=True,quiet_verified=False,designated=kind in MARKED,name=(p.get('name') or '').strip() or 'County-mapped '+kind.lower(),geometry=[[nodes[src]['lon'],nodes[src]['lat']],[nodes[dst]['lon'],nodes[dst]['lat']]],source=SOURCE,source_date=source_date,permission_basis=basis))
 linked=set()
 for county,osm,distance,way in source_links:
  if county not in nodes or (county,osm) in linked:continue
  linked.add((county,osm))
  for a,b in ((county,osm),(osm,county)):
   edges.append(dict(id=f'pbc:source-link:{a}:{b}',**{'from':a,'to':b},length_m=max(distance,.001),kind='path',bicycle_allowed=True,assessed=True,quiet_verified=False,name='Mapped path connection',geometry=[[nodes[a]['lon'],nodes[a]['lat']],[nodes[b]['lon'],nodes[b]['lat']]],source=SOURCE,source_date=source_date,connection_basis='Same county osm_id and eligible OSM way; endpoints within 1 metre',osm_way_id=way))
 return dict(graph,nodes=list(nodes.values()),edges=edges,metadata=dict(graph.get('metadata',{}),county_existing_features_imported=accepted,county_source_links=len(linked),county_pathways_with_osm_evidence=pathways,county_topology='Equal county coordinates plus shared osm_id endpoint matches within 1 metre to eligible OSM paths; no proximity-only joins.'))
