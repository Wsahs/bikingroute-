"""Rebuild the expanded Boca network from retained, source-attributed inputs."""
import json
from pathlib import Path
from server.import_osm import convert
from server.jurisdictions import boca_policy
from server.gis_network import merge_pedestrians
from server.routing import eligible

def rebuild(folder=Path('data')):
 policy=boca_policy(folder/'sources/pbc-municipalities.geojson')
 graph=convert(json.loads((folder/'boca-source.osm.json').read_text()),bounds=[26.32,-80.245,26.43,-80.055],sidewalk_policy=policy)
 source=folder/'sources/pbc-pedestrians.geojson';manifest=json.loads((folder/'sources/pbc-pedestrians-manifest.json').read_text())
 graph=merge_pedestrians(graph,json.loads(source.read_text())['features'],policy,manifest['retrieved_at'])
 graph['metadata']['limitations'][1]='Conventional-bicycle sidewalk defaults apply in reviewed Boca/unincorporated Palm Beach areas; explicit restrictions still apply. Other unknown permissions remain excluded.'
 graph['metadata']['audit']['eligible_directed_segments']=sum(eligible(e) for e in graph['edges'])
 p=folder/'boca-network.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(graph,separators=(',',':')));t.replace(p)
 print(graph['metadata']['audit'],graph['metadata']['county_existing_features_imported'],flush=True)
if __name__=='__main__':rebuild()
