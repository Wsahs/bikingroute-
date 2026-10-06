import json,tempfile,unittest
from pathlib import Path
from server.jurisdictions import boca_policy
class JurisdictionTests(unittest.TestCase):
 def test_explicit_unincorporated_polygon_uses_state_rule(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'j.json';p.write_text(json.dumps({'features':[{'properties':{'MUNINAME':'Unincorporated'},'geometry':{'type':'Polygon','coordinates':[[[-80.24,26.33],[-80.21,26.33],[-80.21,26.4],[-80.24,26.4],[-80.24,26.33]]]}}]}))
   self.assertTrue(boca_policy(p)([{'lat':26.36,'lon':-80.22}]))
