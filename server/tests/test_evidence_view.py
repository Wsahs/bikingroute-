import json,sqlite3,tempfile,unittest
from pathlib import Path
from server.evidence import build,around_address
from server.app import Application
class EvidenceViewTests(unittest.TestCase):
 def test_outlines_stay_evidence_and_driveways_are_not_called_sidewalks(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);features=[]
   for kind,lon in [('SIDEWALK',-80.1),('DRIVEWAY',-80.1),('SIDEWALK',-80.2)]:features.append({'type':'Feature','properties':{'TYPE':kind},'geometry':{'type':'LineString','coordinates':[[lon,26.35],[lon,26.3501]]}})
   (p/'pbc-sidewalks.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}));build(p,p/'evidence.sqlite')
   r=around_address(p/'evidence.sqlite',26.35,-80.1);self.assertEqual(len(r['features']),1);self.assertFalse(r['routing_verified']);self.assertFalse(r['features'][0]['properties']['routing_verified'])
   code,r=Application(data_dir=p).dispatch('GET','/api/sidewalk-evidence?lat=26.35&lon=-80.1');self.assertEqual(code,200);self.assertEqual(len(r['features']),1)
 def test_invalid_coordinates_rejected(self):
  for query in ['lat=nan&lon=-80','lat=91&lon=-80','lat=26&lon=inf']:
   code,_=Application().dispatch('GET','/api/sidewalk-evidence?'+query);self.assertEqual(code,400)
 def test_unavailable_database_returns_no_claim_of_verified_coverage(self):
  with tempfile.TemporaryDirectory() as folder:
   r=around_address(Path(folder)/'missing',26,-80);self.assertFalse(r['routing_verified']);self.assertEqual(r['features'],[])
