import unittest
from server.app import Application
from test_routing import graph

class APITests(unittest.TestCase):
    def setUp(self):
        self.app=Application(graph([('a','b',100,'trail')],False))

    def test_status_discloses_incomplete_coverage(self):
        code,result=self.app.dispatch('GET','/api/status')
        self.assertEqual(code,200)
        self.assertFalse(result['coverage']['coverage_complete'])

    def test_route_returns_engine_result(self):
        code,result=self.app.dispatch('POST','/api/route',{'start':'a','end':'b'})
        self.assertEqual(code,200)
        self.assertEqual(result['status'],'primary')
        self.assertEqual(result['primary']['distance_m'],100)

    def test_unknown_nodes_get_actionable_error(self):
        code,result=self.app.dispatch('POST','/api/route',{'start':'fake','end':'b'})
        self.assertEqual(code,400)
        self.assertIn('error',result)

    def test_invalid_coordinates_rejected(self):
        for lat in ('nan','inf','100','hello'):
            code,result=self.app.dispatch('GET','/api/access?lat='+lat+'&lon=-80.1')
            self.assertEqual(code,400)

    def test_far_address_is_not_silently_connected(self):
        code,result=self.app.dispatch('GET','/api/access?lat=25&lon=-81')
        self.assertEqual(code,200)
        self.assertEqual(result['points'],[])

    def test_missing_dataset_is_unavailable_not_no_route(self):
        code,result=Application().dispatch('POST','/api/route',{'start':'a','end':'b'})
        self.assertEqual(code,503)
        self.assertEqual(result['code'],'coverage_unavailable')

    def test_demo_is_explicitly_labeled(self):
        code,result=self.app.dispatch('POST','/api/route',{'dataset':'demo','scenario':'detour','start':'start','end':'finish'})
        self.assertEqual(code,200)
        self.assertTrue(result['coverage']['demo'])
        self.assertEqual(result['status'],'confirmation')

    def test_invalid_request_types(self):
        for data in ([],None,{'start':[],'end':{}},{'start':'a','end':'b','speed_mph':False}):
            code,result=self.app.dispatch('POST','/api/route',data)
            self.assertEqual(code,400)

    def test_unknown_dataset_is_rejected(self):
        code,result=self.app.dispatch('POST','/api/route',{'dataset':'other','start':'a','end':'b'})
        self.assertEqual(code,400)

    def test_network_only_exposes_eligible_edges(self):
        app=Application(graph([('a','b',100,'trail'),('b','c',100,'street',{'quiet_verified':False})]))
        code,result=app.dispatch('GET','/api/network')
        self.assertEqual(code,200)
        self.assertEqual(len(result['features']),1)
