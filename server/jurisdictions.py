"""Conventional bicycle sidewalk defaults, limited to reviewed jurisdictions."""
import json
from functools import lru_cache
from pathlib import Path
SOURCE='https://www.myboca.us/2223/Bike-Pedestrian-Safety'
STATE='https://www.flsenate.gov/Laws/Statutes/2025/316.2065'
def ring_contains(x,y,ring):
 inside=False
 for a,b in zip(ring,ring[1:]+ring[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside
def contains(g,x,y):
 polygons=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
 return any(ring_contains(x,y,p[0]) and not any(ring_contains(x,y,r) for r in p[1:]) for p in polygons)
def boca_policy(path):
 features=json.loads(Path(path).read_text())['features']
 boxes=[]
 for f in features:
  if f['properties']['MUNINAME']=='Unincorporated':continue
  g=f['geometry'];polygons=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];xy=[point for polygon in polygons for ring in polygon for point in ring]
  boxes.append((min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy),f))
 @lru_cache(maxsize=250000)
 def jurisdiction(x,y):
  if not (-80.245<=x<=-80.055 and 26.32<=y<=26.43):return None
  for minx,miny,maxx,maxy,f in boxes:
   if minx<=x<=maxx and miny<=y<=maxy and contains(f['geometry'],x,y):
    return SOURCE if f['properties']['MUNINAME']=='Boca Raton' else None
  # This pilot rectangle is entirely in Palm Beach County. Outside municipal
  # polygons, apply the state sidewalk rule; this never applies to general trails.
  return STATE
 def policy(points):
  bases=[jurisdiction(p['lon'],p['lat']) for p in points]
  return 'Conventional bicycle sidewalk default: '+', '.join(sorted(set(bases))) if bases and all(bases) else None
 return policy
