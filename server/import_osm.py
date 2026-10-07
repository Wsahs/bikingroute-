"""Import OSM topology conservatively; never infer sidewalks from road centerlines."""
import argparse
import collections
import datetime
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request
from server.routing import eligible

BOCA_BOUNDS = [26.32, -80.20, 26.43, -80.055]  # south, west, north, east; a pilot area, not county coverage


def meters(a, b):
    lat1, lat2 = math.radians(a['lat']), math.radians(b['lat'])
    dlat, dlon = lat2-lat1, math.radians(b['lon']-a['lon'])
    value = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(value)))


def conditional(tags):
    return any('conditional' in key or key in ('opening_hours', 'bicycle:forward', 'bicycle:backward') for key in tags)


def blocked(tags):
    return tags.get('access') in ('no','private','customers','permit','destination') or tags.get('bicycle') in ('no','private','dismount','destination') or conditional(tags)


def convert(document, name='Boca Raton pilot', bounds=None, sidewalk_policy=None):
    if document.get('remark') or not isinstance(document.get('elements'), list):
        raise ValueError('Incomplete or invalid map download; no network was imported')
    raw_nodes = {str(e['id']): e for e in document['elements'] if e['type']=='node'}
    nodes = [dict(id=nid, lat=n['lat'], lon=n['lon']) for nid,n in raw_nodes.items()]
    audit = collections.Counter(missing_node_segments=0, roads_with_unseparated_sidewalks=0,
                                input_ways=0, excluded_directed_segments=0, eligible_directed_segments=0)
    edges = []
    node_ways=collections.defaultdict(list)
    for element in document['elements']:
        if element['type']=='way' and 'highway' in element.get('tags',{}):
            for node in element.get('nodes',[]):node_ways[str(node)].append(element)
    def driveway_crossing(way):
        ids=[str(n) for n in way.get('nodes',[])]
        if len(ids)<3 or any(n not in raw_nodes for n in ids):return False
        if sum(meters(raw_nodes[a],raw_nodes[b]) for a,b in zip(ids,ids[1:]))>35:return False
        for endpoint in (ids[0],ids[-1]):
            if not any(w['id']!=way['id'] and w['tags'].get('footway')=='sidewalk' for w in node_ways[endpoint]):return False
        roads=[w for n in ids[1:-1] for w in node_ways[n] if w['tags']['highway'] not in ('footway','path','cycleway','pedestrian','steps')]
        crossing_segments={frozenset((a,b)) for a,b in zip(ids,ids[1:])}
        if any(frozenset((str(a),str(b))) in crossing_segments for w in roads for a,b in zip(w['nodes'],w['nodes'][1:])):return False
        return bool(roads) and all(w['tags']['highway']=='service' for w in roads)
    # Turn restrictions require a movement-aware importer; conservatively exclude
    # every member way of any returned restriction, rather than ignoring it.
    restricted_ways = set()
    for element in document['elements']:
        if element['type']=='relation' and element.get('tags',{}).get('type')=='restriction':
            restricted_ways.update(str(m['ref']) for m in element.get('members',[]) if m['type']=='way')
    source_date = document.get('osm3s',{}).get('timestamp_osm_base', 'Unknown')
    for way in document['elements']:
        if way['type']!='way' or 'highway' not in way.get('tags',{}):
            continue
        audit['input_ways'] += 1
        tags = way['tags']; highway = tags['highway']
        crossing = tags.get('footway')=='crossing' or tags.get('cycleway')=='crossing'
        if crossing:
            kind='crossing'
        elif tags.get('footway') in ('sidewalk','traffic_island'):
            kind='sidewalk'
        elif highway in ('path','cycleway','footway','pedestrian','bridleway'):
            kind='trail' if tags.get('surface') in ('dirt','ground','gravel','unpaved') else 'path'
        else:
            kind='street'
        if kind=='street' and any(k.startswith('sidewalk') and v not in ('no','none','separate') for k,v in tags.items()):
            audit['roads_with_unseparated_sidewalks'] += 1
        scope=None
        if sidewalk_policy and kind in ('sidewalk','crossing'):
            points=[raw_nodes[str(n)] for n in way.get('nodes',[]) if str(n) in raw_nodes]
            scope=sidewalk_policy(points) if len(points)==len(way.get('nodes',[])) else None
        basis=scope if 'bicycle' not in tags else None
        permission = bool(basis) or tags.get('bicycle') in ('yes','designated','permissive') or (highway=='cycleway' and 'bicycle' not in tags)
        permission = permission and not blocked(tags) and str(way['id']) not in restricted_ways
        designation = crossing and (tags.get('crossing') in ('marked','zebra','traffic_signals','uncontrolled') or tags.get('crossing:markings') not in (None,'no'))
        if crossing and not designation and 'crossing' not in tags and 'crossing:markings' not in tags:
            for node_id in way.get('nodes',[]):
                nt=raw_nodes.get(str(node_id),{}).get('tags',{})
                if nt.get('highway')=='crossing' and (nt.get('crossing') in ('marked','zebra','traffic_signals','uncontrolled') or nt.get('crossing:markings') not in (None,'no')):
                    designation=True
                    break
        driveway=bool(crossing and scope and driveway_crossing(way))
        if driveway:designation=True
        oneway = tags.get('oneway:bicycle', tags.get('oneway', 'no'))
        # Do not interpret reversible/time-dependent direction as two-way.
        if oneway not in ('yes','1','true','-1','no','0','false'):
            permission=False
        ids = [str(n) for n in way.get('nodes',[])]
        for index,(a,b) in enumerate(zip(ids,ids[1:])):
            if a not in raw_nodes or b not in raw_nodes:
                audit['missing_node_segments'] += 1
                continue
            na,nb = raw_nodes[a],raw_nodes[b]
            length = meters(na,nb)
            if length <= 0:
                continue
            node_blocked=False
            for node in (na,nb):
                nt=node.get('tags',{})
                # A documented curb ramp is traversable geometry, not an access ban.
                ramp = nt.get('barrier') == 'kerb' and nt.get('kerb') in ('lowered', 'flush', 'no')
                if blocked(nt) or (nt.get('barrier') and not ramp and nt.get('bicycle') not in ('yes','designated')):
                    node_blocked=True
            directions = [(a,b)] if oneway in ('yes','1','true') else [(b,a)] if oneway=='-1' else [(a,b),(b,a)]
            for src,dst in directions:
                edge=dict(id='%s:%s:%s'%(way['id'],index,src), **{'from':src,'to':dst},
                    length_m=length,kind=kind,bicycle_allowed=bool(permission and not node_blocked),
                    assessed=bool(permission and not node_blocked),quiet_verified=False,
                    designated=bool(designation),crossing_type='driveway' if driveway else 'marked' if designation else 'unverified',name='Sidewalk across driveway' if driveway else tags.get('name',kind.title()),
                    geometry=[[raw_nodes[src]['lon'],raw_nodes[src]['lat']],[raw_nodes[dst]['lon'],raw_nodes[dst]['lat']]],
                    source='OpenStreetMap way '+str(way['id']),source_date=source_date,permission_basis=basis or 'Explicit OSM bicycle access')
                reasons=[]
                if not permission:reasons.append('way_access_unresolved_or_restricted')
                if node_blocked:reasons.append('node_barrier_or_access_restriction')
                if kind=='crossing' and not designation:reasons.append('crossing_not_designated')
                if kind=='street':reasons.append('street_quietness_unverified')
                edge['exclusion_reasons']=reasons
                if way.get('county_evidence'):edge['county_evidence']=way['county_evidence']
                edges.append(edge)
                audit['eligible_directed_segments' if eligible(edge) else 'excluded_directed_segments'] += 1
    return dict(nodes=nodes,edges=edges,metadata=dict(name=name,coverage_complete=False,demo=False,
        bounds=bounds or BOCA_BOUNDS,source_date=source_date,imported_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        attribution='© OpenStreetMap contributors, ODbL',audit=dict(audit),
        limitations=['Pilot map only; not comprehensive county coverage.',
        'Unknown bicycle permissions and conditional restrictions are excluded.',
        'Street quietness has not been verified; live street fallback is unavailable until evidence is imported.',
        'Road-tagged sidewalks are audited but cannot be routed without separate geometry and verified connections.',
        'Mapped eligibility is not an on-site survey or a guarantee of current conditions.']))


def download(bounds, output):
    bbox=','.join(str(v) for v in bounds)
    query='[out:json][timeout:150];way["highway"]('+bbox+')->.roads;(.roads;node(w.roads);rel(bw.roads)["type"="restriction"];);out body;'
    request=urllib.request.Request('https://overpass-api.de/api/interpreter',
        data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'Sidepath-development/0.1 (mapping coverage research)'})
    with urllib.request.urlopen(request,timeout=180) as response:
        doc=json.load(response)
    result=convert(doc,bounds=bounds)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix('.tmp');temp.write_text(json.dumps(result,separators=(',',':')));temp.replace(output)
    output.with_name('boca-source.osm.json').write_text(json.dumps(doc,separators=(',',':')))
    print(json.dumps(result['metadata'],indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='data/boca-network.json')
    parser.add_argument('--bounds',type=float,nargs=4,default=BOCA_BOUNDS,metavar=('S','W','N','E'))
    args=parser.parse_args();download(args.bounds,args.output)
