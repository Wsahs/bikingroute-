import unittest
from unittest.mock import patch
from server.app import Application
from test_routing import graph

class SidewalkTripTests(unittest.TestCase):
 def request(self,g,payload=None):
  return Application(g).dispatch('POST','/api/sidewalk-trip',payload or {'origin':{'lat':26.35,'lng':-80.1},'destination':{'lat':26.36,'lng':-80.11}})
 def test_coordinate_validation(self):
  code,_=self.request(graph([('a','b',100,'trail')]),{'origin':{'lat':False,'lng':-80},'destination':{'lat':26,'lng':-80}})
  self.assertEqual(code,400)
 def test_approaches_never_become_verified_route_geometry(self):
  with patch('server.sidewalk_trip.access_points',side_effect=[[{'id':'a','component':'a','distance_m':80}],[{'id':'b','component':'a','distance_m':120}]]):
   code,result=self.request(graph([('a','b',100,'trail')]))
  self.assertEqual(code,200)
  self.assertEqual(result['primary']['distance_m'],100)
  self.assertFalse(result['door_to_door_verified'])
  self.assertEqual(result['approaches']['origin']['distance_m'],80)
 def test_empty_coverage_is_not_proof_of_no_sidewalk(self):
  with patch('server.sidewalk_trip.access_points',return_value=[]):code,result=self.request(graph([('a','b',100,'trail')]))
  self.assertEqual(code,200);self.assertEqual(result['status'],'coverage_gap');self.assertIsNone(result['primary'])
 def test_street_fallback_is_not_automatically_primary(self):
  with patch('server.sidewalk_trip.access_points',side_effect=[[{'id':'a','component':'a','distance_m':0}],[{'id':'b','component':'a','distance_m':0}]]):
   code,result=self.request(graph([('a','b',100,'street')]))
  self.assertIsNone(result['primary']);self.assertTrue(result['requires_confirmation'])
