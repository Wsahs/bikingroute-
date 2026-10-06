"""Inventory every imported Boca way; source coverage is not field verification."""
import collections,datetime,json,sqlite3
from pathlib import Path
from server.routing import eligible
REVIEWED={'1152993383','1152993381','1151660139','1151660155'}
def audit(folder=Path('data')):
 raw=json.loads((folder/'boca-source.osm.json').read_text());graph=json.loads((folder/'boca-network.json').read_text())
 ways=[w for w in raw['elements'] if w['type']=='way' and 'highway' in w.get('tags',{})]
 grouped=collections.defaultdict(list)
 for edge in graph['edges']:
  if edge['source'].startswith('OpenStreetMap way '):grouped[edge['source'].split()[-1]].append(edge)
 counts=collections.Counter();rows=[]
 for w in ways:
  wid=str(w['id']);tags=w['tags'];edges=grouped[wid];usable=[e for e in edges if eligible(e)];kind=edges[0]['kind'] if edges else 'no_geometry'
  if kind=='street':status='road_review';reason='Roadway; sidewalk geometry and low-traffic suitability must be assessed separately.'
  elif usable:status='routable_mapped';reason='Mapped geometry and current access/crossing rules pass; not an on-site survey.'
  elif kind=='crossing':status='crossing_review';reason='Crossing access, designation or barrier still unresolved.'
  else:status='access_review';reason='Bicycle permission, access, barrier or geometry needs review.'
  counts[status]+=1
  driveway=any(e.get('crossing_type')=='driveway' for e in edges)
  if driveway:counts['driveway_continuations']+=1
  rows.append((wid,tags.get('name',''),tags['highway'],kind,status,reason,len(edges),len(usable),int(driveway),'aerial-reviewed crossing' if wid in REVIEWED else 'not individually visually reviewed',json.dumps(tags)))
 with sqlite3.connect(folder/'boca-review.sqlite') as db:
  db.execute('CREATE TABLE IF NOT EXISTS ways(osm_id TEXT PRIMARY KEY,name TEXT,highway TEXT,kind TEXT,status TEXT,reason TEXT,segments INTEGER,routable_segments INTEGER,driveway INTEGER,visual_review TEXT,tags TEXT)');db.execute('DELETE FROM ways');db.executemany('INSERT INTO ways VALUES(?,?,?,?,?,?,?,?,?,?,?)',rows)
  assert db.execute('SELECT count(*) FROM ways').fetchone()[0]==len(ways)
  db.execute('CREATE INDEX IF NOT EXISTS ways_status ON ways(status)')
 report={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'imported_highway_ways':len(ways),'inventory_records':len(rows),'counts':dict(counts),'individually_reviewed_crossings':sorted(REVIEWED),'imagery_source':'https://gis.pbcgov.org/image/rest/services/Aerialphotgraphy_2026_WebMercator/ImageServer','survey_complete':False,'bounds':graph['metadata']['bounds'],'notes':['Every imported highway way has a review record. This does not establish every real-world street or sidewalk is mapped.','Driveway continuations require shared-node topology, sidewalks at both ends, service-road-only crossing and reviewed jurisdiction.','Unmarked crossings of ordinary roads remain excluded from the strict route.','Private-access and explicit bicycle restrictions are retained.']}
 (folder/'boca-review-summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':audit()
