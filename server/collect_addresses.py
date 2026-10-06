"""Download public address fields only; check every advertised ID before publishing."""
import argparse,datetime,hashlib,json,urllib.parse,urllib.request,time
from pathlib import Path
from server.addresses import AddressIndex
SOURCES={
 'boca':('https://gis.pbcgov.org/arcgis/rest/services/CWGIS/SITUS_FULL_ADDRESS/FeatureServer/0',[-80.30,26.30,-80.055,26.46],"STATUS = 'PROD'",'OBJECTID,FULL_ADDRESS,STREET_NO,STREET_PRE_DIR,STREET_NAME,STREET_SUFFIX,STREET_POST_DIR,APARTMENT,ZIP_CITY,ZIP_CODE'),
 'hollywood':('https://services.arcgis.com/JMAJrTsHNLrSsWf5/ArcGIS/rest/services/ZoningApp/FeatureServer/0',[-80.26,25.97,-80.10,26.09],'1=1','OBJECTID,FULL_SITE_ADDRESS,SITUS_HOUSE_NUMBER,SITUS_STREET_PRE_DIRECTION,SITUS_STREET_NAME,SITUS_STREET_TYPE,SITUS_STREET_SUFFIX_DIRECTION,SITUS_UNIT_NUMBER,CITY_NAME,ZIP_CODE')}
def fetch(url,params):
 for attempt in range(3):
  try:
   request=urllib.request.Request(url,data=urllib.parse.urlencode(params).encode()) if 'objectIds' in params else url+'?'+urllib.parse.urlencode(params)
   with urllib.request.urlopen(request,timeout=50) as response:d=json.load(response)
   if 'error' in d:raise ValueError(d['error'])
   return d
  except Exception:
   if attempt==2:raise
   time.sleep(attempt+1)
def collect(region,folder):
 url,bounds,where,fields=SOURCES[region];folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 inventory=fetch(url+'/query',dict(where=where,geometry=','.join(map(str,bounds)),geometryType='esriGeometryEnvelope',inSR=4326,returnIdsOnly='true',f='json'))
 ids=sorted(inventory['objectIds']);features=[];print(region,'address inventory',len(ids),flush=True)
 for offset in range(0,len(ids),500):
  wanted=ids[offset:offset+500];batch=fetch(url+'/query',dict(objectIds=','.join(map(str,wanted)),outFields=fields,outSR=4326,f='geojson'))
  if batch.get('exceededTransferLimit') or {f['properties']['OBJECTID'] for f in batch['features']}!=set(wanted):raise ValueError('Incomplete address batch')
  features.extend(batch['features'])
  if offset%5000==0:print(region,len(features),'/',len(ids),flush=True)
 records=[]
 for f in features:
  p=f['properties'];xy=(f.get('geometry') or {}).get('coordinates')
  if not xy:continue
  if region=='boca':
   street=' '.join(str(p[k]).strip() for k in ['STREET_NO','STREET_PRE_DIR','STREET_NAME','STREET_SUFFIX','STREET_POST_DIR'] if p.get(k));unit=p.get('APARTMENT');city=p.get('ZIP_CITY') or 'Boca Raton'
  else:
   street=' '.join(str(p[k]).strip() for k in ['SITUS_HOUSE_NUMBER','SITUS_STREET_PRE_DIRECTION','SITUS_STREET_NAME','SITUS_STREET_TYPE','SITUS_STREET_SUFFIX_DIRECTION'] if p.get(k));unit=p.get('SITUS_UNIT_NUMBER');city=(p.get('CITY_NAME') or 'Hollywood').title()
  if not street:continue
  if unit:street+=' Unit '+str(unit)
  label=f"{street}, {city}, FL {p.get('ZIP_CODE') or ''}".strip()
  records.append(dict(id=str(p['OBJECTID']),label=label,lat=xy[1],lon=xy[0],source=url))
 target=folder/(region+'-addresses.geojson');temp=target.with_suffix('.tmp');temp.write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':')));temp.replace(target)
 AddressIndex(folder.parent/'addresses.sqlite').replace(region,records)
 manifest=dict(source=url,bounds=bounds,retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),advertised_count=len(ids),downloaded_count=len(features),indexed_count=len(records),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),coverage_complete=False)
 (folder/(region+'-addresses-manifest.json')).write_text(json.dumps(manifest,indent=2));print(manifest,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('region',choices=SOURCES);p.add_argument('--folder',default='data/sources');a=p.parse_args();collect(a.region,a.folder)
