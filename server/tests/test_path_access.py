import unittest
from server.path_access import with_path_access
from server.routing import plan
class PathAccessTests(unittest.TestCase):
 def graph(self):
  return {'nodes':[{'id':'a','lat':26,'lon':-80},{'id':'b','lat':26,'lon':-79.98}], 'edges':[{'id':'e','from':'a','to':'b','geometry':[[-80,26],[-79.98,26]],'length_m':2000,'kind':'path','bicycle_allowed':True,'assessed':True}]}
 def test_mid_segment_access_preserves_geometry_distance_and_direction(self):
  original=self.graph();g=with_path_access(original,[{'lat':26.0001,'lng':-79.99}]);n=g['nodes'][-1]
  self.assertAlmostEqual(n['lat'],26);self.assertAlmostEqual(sum(e['length_m'] for e in g['edges']),2000)
  self.assertAlmostEqual(plan(g,n['id'],'b')['primary']['distance_m'],1000)
  self.assertIsNone(plan(g,'b',n['id'])['primary']);self.assertEqual(len(original['nodes']),2)
 def test_reverse_edges_share_access_points(self):
  g=self.graph();e=g['edges'][0];g['edges'].append(dict(e,id='r',**{'from':'b','to':'a'},geometry=list(reversed(e['geometry']))))
  out=with_path_access(g,[{'lat':26,'lng':-79.99}]);self.assertEqual(len(out['nodes']),3);self.assertEqual(len(out['edges']),4)
 def test_restricted_paths_and_distant_addresses_do_not_get_connections(self):
  g=self.graph();g['edges'][0]['bicycle_allowed']=False;self.assertEqual(len(with_path_access(g,[{'lat':26,'lng':-79.99}])['nodes']),2)
  self.assertEqual(len(with_path_access(self.graph(),[{'lat':27,'lng':-79.99}])['nodes']),2)
 def test_two_addresses_on_same_edge_can_route_between_projections(self):
  out=with_path_access(self.graph(),[{'lat':26.0001,'lng':-79.995},{'lat':26.0001,'lng':-79.985}]);self.assertEqual(len(out['nodes']),4)
  r=plan(out,out['nodes'][2]['id'],out['nodes'][3]['id']);self.assertAlmostEqual(r['primary']['distance_m'],1000)
