"""Find a mapped trip without inventing address-to-network connections."""
import math
from server.access import access_points
from server.path_access import with_path_access
from server.routing import eligible, Network, plan

def coordinates(value):
 if not isinstance(value,dict):raise ValueError('Select both addresses from the suggestions.')
 for key,limit in [('lat',90),('lng',180)]:
  n=value.get(key)
  if isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) or abs(n)>limit:raise ValueError('Invalid selected address coordinates.')
 return value

def _trip(graph,origin,destination):
 origin=coordinates(origin);destination=coordinates(destination)
 graph=with_path_access(graph,[origin,destination])
 result={'status':'coverage_gap','primary':None,'alternative':None,'requires_confirmation':False,'door_to_door_verified':False,'search_radius_m':500,'warnings':['Address-to-path connections are unverified. Distances and times cover only the mapped path.']}
 starts=access_points(graph,eligible,origin['lat'],origin['lng'])
 ends=access_points(graph,eligible,destination['lat'],destination['lng'])
 pairs=sorted([(a['distance_m']+b['distance_m'],a,b) for a in starts for b in ends if a['component']==b['component']],key=lambda p:p[0])
 if not pairs:
  result['message']='We found your addresses, but cannot connect them with our current sidewalk data. This does not mean sidewalks are absent. Try another trip or use the Google cycling planner.'
  return result
 network=Network(graph);fallback=None
 for _,a,b in pairs:
  if a['id']==b['id']:continue
  candidate=plan(network,a['id'],b['id'])
  approaches={'origin':a,'destination':b}
  if candidate['primary']:
   return dict(candidate,approaches=approaches,door_to_door_verified=False,search_radius_m=500,warnings=result['warnings']+candidate['warnings'])
  if candidate['alternative'] and fallback is None:fallback=dict(candidate,approaches=approaches,door_to_door_verified=False,requires_confirmation=True,search_radius_m=500,warnings=result['warnings']+candidate['warnings'])
 if fallback:return fallback
 result['message']='The mapped paths near these addresses do not form a usable continuous route in the requested direction. Coverage is incomplete; we have not ruled out a real sidewalk route.'
 return result


def trip(graph,origin,destination,crossing_choices=None):
 from server.crossing_options import apply_options
 choices={} if crossing_choices is None else crossing_choices
 selected=_trip(apply_options(graph,choices),origin,destination)
 preview=_trip(apply_options(graph,choices,preview=True),origin,destination) if any(e.get('crossing_option') and choices.get(e['crossing_option']['id']) is None for e in graph['edges']) else selected
 candidate=preview.get('primary')
 pending={s['crossing_option']['id']:s['crossing_option'] for s in (candidate or {}).get('segments',[]) if s.get('crossing_option') and s.get('approval_required')}
 current=selected.get('primary')
 if pending and (not current or candidate['distance_m']+1<current['distance_m']):
  selected['crossing_proposal']=candidate
  selected['crossing_choices']=list(pending.values())
  selected['proposal_approaches']=preview['approaches']
  selected['proposal_message']='Optional mapped route with unmarked side-street crossings. Approve each crossing separately before selecting it. Address approaches remain unverified.'
 if any(s.get('crossing_option') for s in (current or {}).get('segments',[])):
  selected['warnings'].append('Includes individually approved unmarked crossings. Traffic conditions and current accessibility have not been verified.')
 return selected
