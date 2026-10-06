import unittest
from server.app import Application
from test_routing import graph
class LiveTests(unittest.TestCase):
 def test_bike_mode_uses_shortest_legal_street_even_when_quietness_unknown(self):
  g=graph([('a','b',100,'street',{'quiet_verified':False}),('a','b',500,'trail')]);app=Application(g)
  code,result=app.dispatch('POST','/api/route',{'start':'a','end':'b','mode':'bicycle'})
  self.assertEqual(code,200);self.assertEqual(result['primary']['distance_m'],100)
 def test_bike_access_and_map_include_permitted_streets(self):
  app=Application(graph([('a','b',100,'street',{'quiet_verified':False})]))
  self.assertTrue(app.dispatch('GET','/api/access?lat=26.35&lon=-80.1&mode=bicycle')[1]['points'])
  self.assertEqual(len(app.dispatch('GET','/api/network?mode=bicycle')[1]['features']),1)
 def test_bike_mode_excludes_unknown_permission(self):
  app=Application(graph([('a','b',100,'street',{'bicycle_allowed':False})]))
  self.assertIsNone(app.dispatch('POST','/api/route',{'start':'a','end':'b','mode':'bicycle'})[1]['primary'])
 def test_graph_refreshes_after_atomic_data_import(self):
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'boca-network.json';g=graph([('a','b',100,'trail')]);p.write_text(json.dumps(g));app=Application(data_dir=folder)
   self.assertEqual(app.load('boca')['edges'][0]['length_m'],100)
   g['edges'][0]['length_m']=250;new=p.with_suffix('.tmp');new.write_text(json.dumps(g));new.replace(p)
   self.assertEqual(app.load('boca')['edges'][0]['length_m'],250)
 def test_display_groups_segments_without_drawing_join_lines(self):
  g=graph([('a','b',100,'trail'),('c','d',100,'trail')])
  for i,e in enumerate(g['edges']):e['source']='same-source';e['name']='Trail';e['geometry']=[[i*2,0],[i*2+1,0]]
  result=Application(g).dispatch('GET','/api/network?display=1')[1]
  self.assertEqual(len(result['features']),1)
  self.assertEqual(result['features'][0]['geometry']['type'],'MultiLineString')
  self.assertEqual(len(result['features'][0]['geometry']['coordinates']),2)
