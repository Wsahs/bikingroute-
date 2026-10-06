"""Local, source-attributed address autocomplete. Never invent a house number."""
import json,re,sqlite3
from pathlib import Path
SUFFIXES={'rd','road','st','street','ave','avenue','blvd','boulevard','way','dr','drive','ln','lane','ct','court','cir','circle','pl','place','ter','terrace'}
ALIASES={'north':'n','south':'s','east':'e','west':'w','northwest':'nw','northeast':'ne','southwest':'sw','southeast':'se','road':'rd','street':'st','avenue':'ave','boulevard':'blvd','drive':'dr','lane':'ln','court':'ct','circle':'cir','place':'pl','terrace':'ter'}
def tokens(value):return [ALIASES.get(t,t) for t in re.findall(r'[a-z0-9]+',value.lower())]
class AddressIndex:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.connect() as db:
   db.execute('CREATE TABLE IF NOT EXISTS addresses(region TEXT,id TEXT,label TEXT,lat REAL,lon REAL,source TEXT,normalized TEXT,PRIMARY KEY(region,id))')
   db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS address_fts USING fts5(normalized, content='addresses', content_rowid='rowid',prefix='1 2 3 4')")
 def connect(self):return sqlite3.connect(str(self.path),timeout=30)
 def replace(self,region,records):
  with self.connect() as db:
   db.execute('DELETE FROM addresses WHERE region=?',(region,))
   db.executemany('INSERT INTO addresses VALUES(?,?,?,?,?,?,?)',[(region,str(r['id']),r['label'],r['lat'],r['lon'],r.get('source','County address points'),' '.join(tokens(r['label']))) for r in records])
   db.execute("INSERT INTO address_fts(address_fts) VALUES('rebuild')")
 def search(self,query,region,limit=6):
  terms=tokens(query[:180]);limit=max(1,min(limit,10))
  if not terms:return []
  def find(ts):
   expression=' AND '.join('"'+t+'"'+('*' if i==len(ts)-1 else '') for i,t in enumerate(ts))
   with self.connect() as db:
    return db.execute('SELECT a.id,a.label,a.lat,a.lon,a.source FROM address_fts f JOIN addresses a ON a.rowid=f.rowid WHERE address_fts MATCH ? AND a.region=? ORDER BY rank,a.label LIMIT ?',(expression,region,limit)).fetchall()
  rows=find(terms);corrected=False
  if not rows and any(t.isdigit() for t in terms):
   reduced=[t for t in terms if t not in SUFFIXES]
   if reduced!=terms and len(reduced)>1:rows=find(reduced);corrected=bool(rows)
  return [dict(id=r[0],label=r[1],lat=r[2],lon=r[3],source=r[4],name='',kind='County address'+(' · check street suffix' if corrected else ''),suggested_correction=corrected) for r in rows]
