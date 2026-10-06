import unittest
from server.gis_network import merge_pedestrians
class GISNetworkTests(unittest.TestCase):
 def feature(self,kind,xy):return {'type':'Feature','properties':{'Existing_T':kind,'name':'Example'},'geometry':{'type':'LineString','coordinates':xy}}
 def test_existing_sidewalk_and_marked_crosswalk_connect(self):
  features=[self.feature('Sidewalk',[[0,0],[0,.001]]),self.feature('Crosswalk - Standard',[[0,.001],[0,.002]])]
  g=merge_pedestrians({'nodes':[],'edges':[],'metadata':{}},features,lambda points:'Reviewed law')
  self.assertEqual(len(g['edges']),4);self.assertEqual(len(g['nodes']),3)
 def test_no_proposed_or_unmarked_edges(self):
  fs=[self.feature(None,[[0,0],[0,.001]]),self.feature('Crosswalk - Unmarked',[[0,0],[0,.001]])]
  fs[0]['properties']['Proposed_T']='Sidewalk'
  self.assertFalse(merge_pedestrians({'nodes':[],'edges':[],'metadata':{}},fs,lambda points:'Reviewed law')['edges'])
 def test_does_not_snap_nearby_parallel_sidewalks(self):
  fs=[self.feature('Sidewalk',[[0,0],[0,.001]]),self.feature('Sidewalk',[[.00001,0],[.00001,.001]])]
  g=merge_pedestrians({'nodes':[],'edges':[],'metadata':{}},fs,lambda points:'Reviewed law');self.assertEqual(len(g['nodes']),4)
