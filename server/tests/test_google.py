import unittest
from unittest.mock import patch
from server.app import Application

class GoogleTests(unittest.TestCase):
 def test_google_config_does_not_expose_server_key(self):
  with patch.dict('os.environ',{'GOOGLE_MAPS_API_KEY':'private-key','GOOGLE_MAPS_BROWSER_KEY':''}):
   code,result=Application().dispatch('GET','/api/google/config')
  self.assertEqual(code,200)
  self.assertNotIn('private-key',str(result))
 def test_google_route_rejects_missing_places(self):
  for payload in ({},{'origin':'','destination':'abc'},{'origin':[], 'destination':'abc'}):
   code,result=Application().dispatch('POST','/api/google/route',payload)
   self.assertEqual(code,400)
 def test_google_search_rejects_short_query(self):
  code,result=Application().dispatch('GET','/api/google/search?q=a')
  self.assertEqual(code,200)
  self.assertEqual(result['places'],[])
 def test_missing_key_is_explicitly_unavailable(self):
  with patch.dict('os.environ',{'GOOGLE_MAPS_API_KEY':''}):
   code,result=Application().dispatch('POST','/api/google/route',{'origin':'place-a','destination':'place-b'})
  self.assertEqual(code,503)
  self.assertIn('error',result)
