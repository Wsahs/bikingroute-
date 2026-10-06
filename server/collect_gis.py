"""Collect public GIS evidence without treating it as verified routing topology."""
import argparse,datetime,hashlib,json,time,urllib.parse,urllib.request
from pathlib import Path
SOURCES={
 'miami-dade-sidewalks':'https://gisweb.miamidade.gov/arcgis/rest/services/EAMS/EAMS_Map/MapServer/2',
 'pbc-roads':'https://pbcmaps.pbcgov.org/arcgis/rest/services/OpenData/Transportation_Open_Data/MapServer/3',
 'pbc-pedestrians':'https://services5.arcgis.com/79IoFXBn9ZeqmVlC/ArcGIS/rest/services/Pedestrian_Facilities/FeatureServer/0',
 'pbc-bikes':'https://services5.arcgis.com/79IoFXBn9ZeqmVlC/ArcGIS/rest/services/Bicycle_Facility/FeatureServer/0',
 'pbc-sidewalks':'https://pbcmaps.pbcgov.org/arcgis/rest/services/Ags/2/MapServer/15',
 'fort-lauderdale-sidewalks':'https://gis.fortlauderdale.gov/server/rest/services/DBLocalGov/SidewalkNetwork/MapServer/0'}
def fetch(url,params):
 for attempt in range(3):
  try:
   payload=urllib.parse.urlencode(params).encode();request=urllib.request.Request(url,data=payload,headers={'User-Agent':'Sidepath-development/0.1 public GIS research','Content-Type':'application/x-www-form-urlencoded'})
   with urllib.request.urlopen(request,timeout=60) as response:doc=json.load(response)
   if 'error' in doc:raise ValueError(str(doc['error']))
   return doc
  except Exception:
   if attempt==2:raise
   time.sleep(1+attempt)
def write(path,doc):
 temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(doc,separators=(',',':')));temp.replace(path)
def collect(key,folder,bounds_override=None):
 url=SOURCES[key];folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 metadata=fetch(url,{'f':'json'});write(folder/(key+'-metadata.json'),metadata)
 bounds=[-80.20,26.32,-80.055,26.43] if key.startswith('pbc-') else ([-80.25,25.72,-80.17,25.82] if key.startswith('miami-') else [-80.20,26.07,-80.09,26.20])
 bounds=bounds_override or bounds
 query={'where':'1=1','returnIdsOnly':'true','f':'json','geometry':','.join(map(str,bounds)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects'}
 ids=fetch(url+'/query',query)
 if 'objectIds' not in ids:raise ValueError('Missing object ID inventory')
 wanted=sorted(ids['objectIds'] or []);oid=ids.get('objectIdFieldName') or next(f['name'] for f in metadata['fields'] if f['type']=='esriFieldTypeOID')
 print(key,'advertises',len(wanted),'records',flush=True)
 features=[]
 for i in range(0,len(wanted),500):
  page=fetch(url+'/query',{'objectIds':','.join(map(str,wanted[i:i+500])),'outFields':'*','returnGeometry':'true','outSR':4326,'f':'geojson'})
  if page.get('exceededTransferLimit') or page.get('type')!='FeatureCollection':raise ValueError('Incomplete feature batch')
  batch=page['features'];actual={f['properties'][oid] for f in batch}
  if len(batch)!=len(wanted[i:i+500]) or actual!=set(wanted[i:i+500]):raise ValueError('Feature batch does not match requested IDs')
  features.extend(batch)
  print(key,len(features),'/',len(wanted),flush=True)
 out=folder/(key+'.geojson');write(out,{'type':'FeatureCollection','features':features})
 counts={}
 for name in ['Existing_T','Proposed_T','facility_existing','facility_suitability','STATUS','TYPE','L_MUNI','R_MUNI']:
  values={}
  for f in features:
   if name in f['properties']:
    value=str(f['properties'][name]);values[value]=values.get(value,0)+1
  if values:counts[name]=values
 result={'source':url,'requested_bbox_wsen':bounds,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'feature_count':len(features),'all_advertised_ids_downloaded':True,'coverage_complete':False,'routing_verified':False,'source_editing_info':metadata.get('editingInfo'),'source_attribution':metadata.get('copyrightText'),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'file':out.name,'category_counts':counts,'limitations':['Full layer download is not proof of complete real-world coverage.','Existing/proposed status must be checked before routing.','Independent GIS lines do not establish connected sidewalk topology or bicycle permission.','Reuse terms and currency must be reviewed before production distribution.']}
 write(folder/(key+'-manifest.json'),result);return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--source',choices=SOURCES,required=True);parser.add_argument('--output',default='data/sources');args=parser.parse_args();collect(args.source,args.output)
