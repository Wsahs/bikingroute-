"""Expand an evidence download, retaining prior records with explicit provenance."""
import concurrent.futures,datetime,hashlib,json
from pathlib import Path
from server.collect_gis import fetch,SOURCES,write

def expand(key,folder,bounds):
 folder=Path(folder);path=folder/(key+'.geojson');manifest_path=folder/(key+'-manifest.json')
 previous=json.loads(manifest_path.read_text());old=json.loads(path.read_text())
 if hashlib.sha256(path.read_bytes()).hexdigest()!=previous['sha256']:raise ValueError('Existing evidence checksum mismatch')
 metadata=json.loads((folder/(key+'-metadata.json')).read_text());oid=next(f['name'] for f in metadata['fields'] if f['type']=='esriFieldTypeOID')
 inventory=fetch(SOURCES[key]+'/query',{'where':'1=1','returnIdsOnly':'true','f':'json','geometry':','.join(map(str,bounds)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects'})
 if 'objectIds' not in inventory:raise ValueError('Missing source inventory')
 wanted=set(inventory['objectIds'] or []);retained={f['properties'][oid]:f for f in old['features'] if f['properties'][oid] in wanted};missing=sorted(wanted-retained.keys())
 print('Retained',len(retained),'new',len(missing),flush=True)
 def batch(ids):
  page=fetch(SOURCES[key]+'/query',{'objectIds':','.join(map(str,ids)),'outFields':'*','returnGeometry':'true','outSR':4326,'f':'geojson'})
  if page.get('exceededTransferLimit') or page.get('type')!='FeatureCollection':raise ValueError('Incomplete GIS batch')
  fs=page['features']
  if len(fs)!=len(ids) or {f['properties'][oid] for f in fs}!=set(ids):raise ValueError('Wrong GIS batch inventory')
  return fs
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for fs in pool.map(batch,[missing[i:i+500] for i in range(0,len(missing),500)]):
   for f in fs:retained[f['properties'][oid]]=f
 if retained.keys()!=wanted:raise ValueError('Incomplete expanded dataset')
 write(path,{'type':'FeatureCollection','features':[retained[i] for i in sorted(wanted)]})
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 result=dict(previous,feature_count=len(wanted),requested_bbox_wsen=bounds,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),inventory_checked_at=now,expansion={'new_records':len(missing),'new_records_retrieved_at':now,'retained_records':len(wanted)-len(missing),'retained_records_retrieved_at':previous['retrieved_at'],'existing_features_refetched':False},coverage_complete=False,routing_verified=False)
 result['limitations']=previous['limitations']+['Expansion checks all current source IDs but retains existing feature versions; it is not a refresh of their attributes or geometry.']
 counts={}
 for feature in retained.values():
  category=feature['properties'].get('TYPE','Unknown');counts[category]=counts.get(category,0)+1
 result['category_counts']={'TYPE':counts}
 write(manifest_path,result);print('Expanded evidence',len(wanted),flush=True)
if __name__=='__main__':expand('pbc-sidewalks','data/sources',[-80.245,26.32,-80.055,26.43])
