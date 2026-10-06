import unittest
from server.access import access_points
class AccessTests(unittest.TestCase):
 def test_isolated_path_cannot_hide_other_nearby_network(self):
  nodes=[{'id':str(i),'lat':26.35,'lon':-80.1+i*.00001} for i in range(12)]
  edges=[{'from':str(i),'to':str(i+1),'name':'Small path'} for i in range(9)]+[{'from':'10','to':'11','name':'Through path'}]
  points=access_points({'nodes':nodes,'edges':edges},lambda e:True,26.35,-80.1)
  self.assertTrue(any(p['name']=='Through path' for p in points))
 def test_distance_stays_straight_line_and_outside_radius_excluded(self):
  g={'nodes':[{'id':'a','lat':0,'lon':0},{'id':'b','lat':0,'lon':.0001}],'edges':[{'from':'a','to':'b'}]}
  self.assertEqual(access_points(g,lambda e:True,26,-80),[])
