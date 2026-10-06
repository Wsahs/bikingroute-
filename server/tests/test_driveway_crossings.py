import unittest
from server.import_osm import convert
from server.routing import eligible

def example(road='service',extra=None):
 nodes=[{'type':'node','id':i,'lat':26.35,'lon':-80.1+i*.00003} for i in range(1,8)]
 ways=[{'type':'way','id':10,'nodes':[1,2],'tags':{'highway':'footway','footway':'sidewalk'}},{'type':'way','id':11,'nodes':[2,3,4],'tags':dict(highway='footway',footway='crossing',crossing='unmarked',**(extra or {}))},{'type':'way','id':12,'nodes':[4,5],'tags':{'highway':'footway','footway':'sidewalk'}},{'type':'way','id':13,'nodes':[6,3,7],'tags':{'highway':road}}]
 return {'elements':nodes+ways}
class DrivewayTests(unittest.TestCase):
 def crossings(self,doc):return [e for e in convert(doc,sidewalk_policy=lambda points:'Reviewed rule')['edges'] if e['source']=='OpenStreetMap way 11']
 def test_continuous_sidewalk_across_service_entrance_allowed(self):
  edges=self.crossings(example());self.assertTrue(all(eligible(e) for e in edges));self.assertTrue(all(e['crossing_type']=='driveway' for e in edges))
 def test_unmarked_main_road_not_promoted(self):self.assertFalse(any(eligible(e) for e in self.crossings(example('primary'))))
 def test_explicit_footway_ban_still_wins(self):self.assertFalse(any(eligible(e) for e in self.crossings(example(extra={'bicycle':'no'}))))
 def test_missing_sidewalk_endpoint_not_inferred(self):
  doc=example();doc['elements']=[e for e in doc['elements'] if e.get('id')!=12];self.assertFalse(any(eligible(e) for e in self.crossings(doc)))
 def test_explicit_bicycle_permission_does_not_disable_driveway_classification(self):
  for permission in ['yes','designated','permissive']:self.assertTrue(all(eligible(e) for e in self.crossings(example(extra={'bicycle':permission}))))
 def test_travel_along_service_road_is_not_a_sidewalk_crossing(self):
  doc=example();doc['elements'][-1]['nodes']=[6,2,3,4,7]
  self.assertFalse(any(eligible(e) for e in self.crossings(doc)))
