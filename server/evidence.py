"""Indexed GIS evidence: visible coverage, never silently promoted to routing edges."""
import json,sqlite3
from pathlib import Path

def build(folder,database):
 folder=Path(folder)
 with sqlite3.connect(str(database)) as db:
  db.execute('CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY,source TEXT,category TEXT,geometry TEXT,properties TEXT)')
  db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS evidence_bounds USING rtree(id,minx,maxx,miny,maxy)')
  db.execute('DELETE FROM evidence');db.execute('DELETE FROM evidence_bounds')
  count=0
  for path in sorted(folder.glob('*.geojson')):
   if path.stem.endswith('-addresses') or path.stem=='pbc-municipalities':continue
   data=json.loads(path.read_text())
   for feature in data['features']:
    g=feature.get('geometry');p=feature.get('properties') or {}
    if not g or g['type'] not in ('LineString','MultiLineString'):continue
    xy=g['coordinates'] if g['type']=='LineString' else [c for line in g['coordinates'] for c in line]
    if not xy:continue
    count+=1;category=p.get('Existing_T') or p.get('STATUS') or p.get('TYPE') or p.get('facility_existing') or 'Road centerline'
    db.execute('INSERT INTO evidence VALUES(?,?,?,?,?)',(count,path.stem,category,json.dumps(g),json.dumps(p)))
    db.execute('INSERT INTO evidence_bounds VALUES(?,?,?,?,?)',(count,min(c[0] for c in xy),max(c[0] for c in xy),min(c[1] for c in xy),max(c[1] for c in xy)))
 print('Indexed GIS evidence:',count)

def nearby(database,lat,lon):
 if not Path(database).exists():return {'type':'FeatureCollection','features':[]}
 with sqlite3.connect(str(database)) as db:
  rows=db.execute("SELECT e.source,e.category,e.geometry FROM evidence e JOIN evidence_bounds b ON e.id=b.id WHERE b.maxx>=? AND b.minx<=? AND b.maxy>=? AND b.miny<=? AND e.category IN ('Sidewalk','Pathway','Shared Use Path','Existing Sidewalk','SIDEWALK') LIMIT 1200",(lon-.008,lon+.008,lat-.006,lat+.006)).fetchall()
 return {'type':'FeatureCollection','features':[{'type':'Feature','properties':{'source':s,'category':c,'routing_verified':False},'geometry':json.loads(g)} for s,c,g in rows],'notice':'County sidewalk evidence; connectivity and bicycle access are not verified. These lines are not directions.'}
if __name__=='__main__':build('data/sources','data/evidence.sqlite')
