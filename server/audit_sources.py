"""Validate downloaded evidence and produce a source inventory; does not approve routes."""
import collections,datetime,hashlib,html,json,math
from pathlib import Path

def coordinates(value):
 if isinstance(value,list) and len(value)>=2 and isinstance(value[0],(int,float)):
  yield value
 elif isinstance(value,list):
  for child in value:yield from coordinates(child)

def audit(folder):
 folder=Path(folder);records=[]
 for manifest in sorted(folder.glob('*-manifest.json')):
  entry=json.loads(manifest.read_text());data=folder/entry['file'];raw=data.read_bytes()
  assert hashlib.sha256(raw).hexdigest()==entry['sha256'],str(data)+' checksum mismatch'
  features=json.loads(raw)['features'];assert len(features)==entry['feature_count']
  metadata=json.loads((folder/(manifest.name.replace('-manifest','-metadata'))).read_text())
  oid=next(f['name'] for f in metadata['fields'] if f['type']=='esriFieldTypeOID')
  ids=[f['properties'][oid] for f in features];assert len(set(ids))==len(ids),'Duplicate IDs'
  nulls=0;types=collections.Counter();counts={}
  for f in features:
   geo=f.get('geometry')
   if not geo:nulls+=1;continue
   types[geo['type']]+=1
   for p in coordinates(geo['coordinates']):assert math.isfinite(p[0]) and math.isfinite(p[1]) and -180<=p[0]<=180 and -90<=p[1]<=90,'Invalid longitude/latitude'
  for field in ['Existing_T','Proposed_T','facility_existing','facility_suitability','STATUS','TYPE']:
   count=collections.Counter(str(f['properties'].get(field)) for f in features if field in f['properties'])
   if count:counts[field]=dict(count)
  entry.update(category_counts=counts,geometry_types=dict(types),missing_geometry=nulls,validation='IDs unique; expected count, checksum and longitude/latitude verified')
  manifest.write_text(json.dumps(entry,indent=2));records.append(entry)
 previous=json.loads((folder.parent/'boca-source.osm.json').read_text());kinds=collections.Counter(e.get('tags',{}).get('highway') for e in previous['elements'] if e['type']=='way' and 'highway' in e.get('tags',{}))
 result={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'datasets':records,'existing_osm_pilot':{'source_timestamp':previous.get('osm3s',{}).get('timestamp_osm_base'),'highway_way_count':sum(kinds.values()),'highway_counts':dict(kinds),'bounds_south_west_north_east':[26.32,-80.20,26.43,-80.055]},'uncollected':[{'region':'Miami-Dade','source':'https://gisweb.miamidade.gov/arcgis/rest/services/EAMS/EAMS_Map/MapServer/2','reason':'HTTPS certificate chain could not be validated; no features downloaded.'}],'routing_status':'Research evidence only; not yet merged, deduplicated or approved for turn-by-turn routing.'}
 (folder/'inventory.json').write_text(json.dumps(result,indent=2))
 rows=''.join('<tr><td><a href="'+html.escape(r['source'],quote=True)+'">'+html.escape(r['file'].replace('.geojson',''))+'</a></td><td>'+format(r['feature_count'],',')+'</td><td>'+html.escape(str(r['requested_bbox_wsen']))+'</td><td><a href="'+r['file']+'">GeoJSON</a></td></tr>' for r in records)
 report='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sidepath data collection</title><style>body{font:16px/1.5 system-ui;margin:32px auto;max-width:960px;padding:0 20px}table{border-collapse:collapse;width:100%}td,th{padding:12px;text-align:left;border-bottom:1px solid #ccc}code{overflow-wrap:anywhere}.table{overflow-x:auto}</style><h1>Sidepath data collection</h1><p>Downloaded public GIS evidence for the Boca Raton area and a Fort Lauderdale pilot. Bounding boxes are west, south, east, north. These are partial regional inventories, not a survey of every street.</p><div class="table"><table><thead><tr><th>Source</th><th>Records</th><th>Requested area</th><th>Data</th></tr></thead><tbody>'''+rows+'''</tbody></table></div><p>Also retained: '''+format(sum(kinds.values()),',')+''' OpenStreetMap highway ways from the earlier Boca-area pilot.</p><p><strong>Not route-ready:</strong> overlapping sources need reconciliation. Proposed facilities, missing geometry, bicycle permissions, crossings, bridges and disconnected endpoints require review. Road centerlines are not sidewalk geometry. Unmapped does not mean nonexistent.</p><p>Miami-Dade download is blocked by certificate validation; no records are claimed for it. Broward coverage is limited to the Fort Lauderdale pilot.</p><p>Each dataset includes source metadata, retrieval date and a checksum. Source record counts can overlap; they are not unique streets or miles.</p><p><a href="inventory.json">Detailed inventory and category counts</a></p></html>'''
 (folder/'index.html').write_text(report)
 print(json.dumps({'datasets':len(records),'records':sum(r['feature_count'] for r in records),'osm_highway_ways':sum(kinds.values()),'validation':'passed'},indent=2))
if __name__=='__main__':audit('outputs/Sidepath/data/sources')
