import os, unittest
from unittest.mock import patch
from server.google_maps import dispatch

class GoogleMapsTests(unittest.TestCase):
 def test_autocomplete_accepts_first_letter_and_returns_selectable_predictions(self):
  response={'suggestions':[{'placePrediction':{'placeId':'place-1','text':{'text':'Boca Library, Boca Raton, FL'}}}]}
  with patch('server.google_maps.request',return_value=(200,response)) as request:
   code,data=dispatch('GET','/api/google/autocomplete',{'q':['b'],'session':['test-session']},{})
  self.assertEqual(code,200)
  self.assertEqual(data['suggestions'][0]['id'],'place-1')
  self.assertEqual(request.call_args.args[1]['input'],'b')
  self.assertEqual(request.call_args.args[1]['sessionToken'],'test-session')
 def test_details_rejects_path_injection(self):
  with patch('server.google_maps.request') as request:
   code,_=dispatch('GET','/api/google/place',{'id':['../private']},{})
  self.assertEqual(code,400);request.assert_not_called()
 def test_selected_place_uses_get_and_session(self):
  with patch('server.google_maps.request',return_value=(200,{'id':'abc'})) as request:
   code,_=dispatch('GET','/api/google/place',{'id':['abc'],'session':['test-session']},{})
  self.assertEqual(code,200)
  self.assertIsNone(request.call_args.args[1])
  self.assertIn('sessionToken=test-session',request.call_args.args[0])
 def test_route_always_requests_bicycle(self):
  with patch('server.google_maps.request',return_value=(200,{'routes':[]})) as request:
   dispatch('POST','/api/google/route',{}, {'origin':'a','destination':'b','travelMode':'DRIVE'})
  self.assertEqual(request.call_args.args[1]['travelMode'],'BICYCLE')
 def test_config_never_returns_server_key(self):
  with patch.dict(os.environ,{'GOOGLE_MAPS_API_KEY':'private','GOOGLE_MAPS_BROWSER_KEY':'browser'}):
   self.assertEqual(dispatch('GET','/api/google/config',{},{}),(200,{'browserKey':'browser'}))
