"""Geometry-based maneuvers and explicitly inferred county road context.

Road names label a nearby corridor only. They never change routing geometry,
connectivity, permissions, or eligibility. Ambiguous matches remain unnamed.
"""
import math
from collections import defaultdict

X=111320*math.cos(math.radians(26.375));Y=111320
SOURCE='Palm Beach County Road Centerlines'
def xy(p):return p[0]*X,p[1]*Y
def heading(a,b):return math.degrees(math.atan2((b[0]-a[0])*X,(b[1]-a[1])*Y))%360
def delta(a,b):return (b-a+180)%360-180
def distance(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
 t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def intersects(a,b,c,d):
 def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
 return cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0 and max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1]))

class RoadNames:
 def __init__(self,features):
  self.grid=defaultdict(list)
  for f in features:
   props=f.get('properties',{});name=(props.get('STREET') or '').strip();g=f.get('geometry') or {}
   if not name:continue
   lines=[g['coordinates']] if g.get('type')=='LineString' else g.get('coordinates',[]) if g.get('type')=='MultiLineString' else []
   for line in lines:
    for c,d in zip(line,line[1:]):
     a,b=xy(c),xy(d)
     if a==b:continue
     item=(name,a,b,heading(c,d),props.get('OBJECTID'))
     for i in range(math.floor(min(a[0],b[0])/150),math.floor(max(a[0],b[0])/150)+1):
      for j in range(math.floor(min(a[1],b[1])/150),math.floor(max(a[1],b[1])/150)+1):self.grid[i,j].append(item)
 def context(self,s):
  geom=s.get('geometry') or []
  if len(geom)<2:return None
  a,b=xy(geom[0]),xy(geom[-1]);h=heading(geom[0],geom[-1]);samples=[(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t) for t in (.2,.5,.8)]
  candidates={}
  for p in samples:
   for i in range(math.floor((p[0]-45)/150),math.floor((p[0]+45)/150)+1):
    for j in range(math.floor((p[1]-45)/150),math.floor((p[1]+45)/150)+1):
     for item in self.grid[i,j]:candidates[item]=item
  scores={};ids={};sample_scores={}
  for name,c,d,rh,oid in candidates.values():
   if s['kind']=='crossing':
    if not any(intersects(xy(u),xy(v),c,d) for u,v in zip(geom,geom[1:])):continue
    score=0
   else:
    angle=abs(delta(h,rh));angle=min(angle,180-angle)
    if angle>30:continue
    ds=[distance(p,c,d) for p in samples]
    previous=sample_scores.get(name,[float('inf')]*len(samples))
    sample_scores[name]=[min(x,y) for x,y in zip(previous,ds)]
    score=max(sample_scores[name])
   if name not in scores or score<scores[name]:scores[name]=score;ids[name]=oid
  scores={n:v for n,v in scores.items() if v<=40}
  ordered=sorted(scores,key=scores.get)
  if not ordered:return None
  if len(ordered)>1 and scores[ordered[1]]-scores[ordered[0]]<8:return None
  name=ordered[0]
  return dict(street=name,basis='Intersected county road' if s['kind']=='crossing' else 'Nearby parallel county road',source=SOURCE,source_id=ids[name])

def directions(segments,index=None):
 groups=[]
 for number,s in enumerate(segments):
  geom=s.get('geometry') or []
  if len(geom)<2:continue
  context=index.context(s) if index else None
  raw=s.get('name','').strip();generic=raw.lower() in ('','sidewalk','path','crossing','trail','street','county-mapped sidewalk') or raw.startswith('County-mapped crosswalk')
  driveway=raw=='Sidewalk across driveway'
  if driveway and groups and groups[-1]['kind'] in ('sidewalk','path','trail') and abs(delta(groups[-1]['heading_out'],heading(geom[0],geom[-1])))<45:
   g=groups[-1];g['distance_m']+=s['distance_m'];g['driveways']+=1;g['end']=geom[-1];g['segment_end']=number;continue
  name=(context['street'] if context else '') if generic else raw
  kind=s['kind'];label=('the sidewalk along ' if kind=='sidewalk' else 'the path alongside ' if kind in ('path','trail') and context else '')+name if name else 'the mapped '+kind
  if kind=='crossing':label=context['street'] if context else (raw if not generic else 'the mapped crossing')
  start_h=heading(geom[0],geom[1]);end_h=heading(geom[-2],geom[-1]);last=groups[-1] if groups else None
  if last and last['label']==label and last['kind']==kind and abs(delta(last['heading_out'],start_h))<45:
   last['distance_m']+=s['distance_m'];last['heading_out']=end_h;last['end']=geom[-1];last['segment_end']=number;continue
  groups.append(dict(kind=kind,label=label,distance_m=s['distance_m'],heading_in=start_h,heading_out=end_h,start=geom[0],end=geom[-1],context=context,driveways=1 if driveway else 0,segment_start=number,segment_end=number))
 # Treat contiguous crossing geometry as a single action when the road name
 # is consistent; preserve distinct roads and significant direction changes.
 merged=[]
 for g in groups:
  last=merged[-1] if merged else None
  same_cross=last and last['kind']==g['kind']=='crossing' and abs(delta(last['heading_out'],g['heading_in']))<45 and (not last['context'] or not g['context'] or last['context']['street']==g['context']['street'])
  if same_cross:
   last['distance_m']+=g['distance_m'];last['end']=g['end'];last['heading_out']=g['heading_out'];last['segment_end']=g['segment_end']
   if g['context']:last['context']=g['context'];last['label']=g['label']
  else:merged.append(g)
 groups=merged
 # Include tiny unnamed curb approaches in their adjacent crossing instruction,
 # instead of asking riders to make separate five-metre turns at curb ramps.
 i=0
 while i<len(groups):
  g=groups[i]
  if g['kind']=='sidewalk' and not g['context'] and g['distance_m']<=15:
   if i and groups[i-1]['kind']=='crossing' and abs(delta(groups[i-1]['heading_out'],g['heading_in']))<=100:
    a=groups[i-1];a['distance_m']+=g['distance_m'];a['end']=g['end'];a['heading_out']=g['heading_out'];a['segment_end']=g['segment_end'];del groups[i];continue
   if i+1<len(groups) and groups[i+1]['kind']=='crossing' and abs(delta(g['heading_out'],groups[i+1]['heading_in']))<=100:
    b=groups[i+1];b['distance_m']+=g['distance_m'];b['start']=g['start'];b['heading_in']=g['heading_in'];b['segment_start']=g['segment_start'];del groups[i];continue
  i+=1
 # Remove short unnamed interruptions only when both neighbors independently
 # identify the same corridor. Never cross a street or join distinct names.
 i=1
 while i<len(groups)-1:
  a,g,b=groups[i-1:i+2]
  if g['distance_m']<=35 and g['kind']!='crossing' and not g['context'] and a['label']==b['label'] and a['kind']==g['kind']==b['kind'] and abs(delta(a['heading_out'],b['heading_in']))<45:
   a['distance_m']+=g['distance_m']+b['distance_m'];a['driveways']+=g['driveways']+b['driveways'];a['end']=b['end'];a['heading_out']=b['heading_out'];a['segment_end']=b['segment_end'];del groups[i:i+2]
  else:i+=1
 rows=[]
 for i,g in enumerate(groups):
  angle=delta(groups[i-1]['heading_out'],g['heading_in']) if i else 0
  maneuver='depart' if i==0 else 'uturn' if abs(angle)>150 else 'right' if angle>35 else 'left' if angle< -35 else 'straight'
  action={'right':'Turn right onto','left':'Turn left onto','uturn':'Make a U-turn onto','straight':'Continue on','depart':'Head '+['north','northeast','east','southeast','south','southwest','west','northwest'][int((g['heading_in']+22.5)/45)%8]+' on'}[maneuver]
  if g['kind']=='crossing':maneuver='cross';instruction=('Cross '+g['label']) if g['context'] else ('Follow '+g['label'])
  else:instruction=action+' '+g['label']
  rows.append(dict(g,maneuver=maneuver,instruction=instruction))
 if groups:rows.append(dict(kind='arrival',maneuver='arrive',instruction='Arrive at the selected path access point',distance_m=0,start=groups[-1]['end'],end=groups[-1]['end'],segment_start=len(segments)-1,segment_end=len(segments)-1,driveways=0,context=None))
 return rows
