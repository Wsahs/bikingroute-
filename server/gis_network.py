"""Import existing county pedestrian centerlines without inventing inter-source joins."""
from server.import_osm import meters
SOURCE='https://services5.arcgis.com/79IoFXBn9ZeqmVlC/ArcGIS/rest/services/Pedestrian_Facilities/FeatureServer/0'
MARKED={'Crosswalk - Standard','Crosswalk - Ladder','Crosswalk - Solid','Crosswalk - Special Emphasis'}
def merge_pedestrians(graph,features,policy,source_date='Unknown'):
 nodes={n['id']:n for n in graph['nodes'] if not n['id'].startswith('pbc:')};edges=[e for e in graph['edges'] if not e['id'].startswith('pbc:')];accepted=0
 for index,f in enumerate(features):
  p=f.get('properties') or {};kind=(p.get('Existing_T') or '').strip();g=f.get('geometry')
  if kind not in MARKED|{'Sidewalk','Shared Use Path'} or not g or g['type'] not in ('LineString','MultiLineString'):continue
  lines=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
  for line_index,line in enumerate(lines):
   points=[dict(lon=c[0],lat=c[1]) for c in line];basis=policy(points)
   if not basis:continue
   accepted+=1
   for i,(a,b) in enumerate(zip(points,points[1:])):
    distance=meters(a,b)
    if distance<=0:continue
    # Preserve source coordinate equality. No rounding, nearest-neighbor snapping,
    # arbitrary road crossings, or inferred links to OSM geometries.
    aa='pbc:'+str(a['lon'])+','+str(a['lat']);bb='pbc:'+str(b['lon'])+','+str(b['lat'])
    nodes[aa]=dict(a,id=aa);nodes[bb]=dict(b,id=bb)
    for src,dst in [(aa,bb),(bb,aa)]:
     edges.append(dict(id=f'pbc:{index}:{line_index}:{i}:{src}',**{'from':src,'to':dst},length_m=distance,kind='crossing' if kind in MARKED else 'sidewalk' if kind=='Sidewalk' else 'path',bicycle_allowed=True,assessed=True,quiet_verified=False,designated=kind in MARKED,name=(p.get('name') or '').strip() or 'County-mapped '+kind.lower(),geometry=[[nodes[src]['lon'],nodes[src]['lat']],[nodes[dst]['lon'],nodes[dst]['lat']]],source=SOURCE,source_date=source_date,permission_basis=basis))
 return dict(graph,nodes=list(nodes.values()),edges=edges,metadata=dict(graph.get('metadata',{}),county_existing_features_imported=accepted,county_topology='Equal source coordinates only; no joins inferred between county and OSM layers.'))
