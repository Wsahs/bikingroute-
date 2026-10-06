import unittest
from server.gis_network import merge_pedestrians

class SourceLinksTests(unittest.TestCase):
 def graph(self,bicycle=True):
  return {'nodes':[{'id':'a','lat':26.35,'lon':-80.1},{'id':'b','lat':26.351,'lon':-80.1}], 'edges':[{'id':'42:0:a','from':'a','to':'b','kind':'sidewalk','bicycle_allowed':bicycle,'assessed':True,'length_m':111,'geometry':[[-80.1,26.35],[-80.1,26.351]]}], 'metadata':{}}
 def feature(self,osm_id=42,kind='Sidewalk',offset=.000001):
  return {'properties':{'osm_id':osm_id,'Existing_T':kind},'geometry':{'type':'LineString','coordinates':[[-80.1+offset,26.35],[-80.1+offset,26.351]]}}
 def links(self,g):return [e for e in g['edges'] if e.get('connection_basis')]
 def test_shared_source_id_and_submeter_endpoint_connect(self):
  g=merge_pedestrians(self.graph(),[self.feature()],lambda _: 'Reviewed')
  self.assertEqual(len(self.links(g)),4)
 def test_proximity_without_shared_id_never_connects(self):
  self.assertFalse(self.links(merge_pedestrians(self.graph(),[self.feature(99)],lambda _:'Reviewed')))
 def test_restricted_osm_feature_never_connects(self):
  self.assertFalse(self.links(merge_pedestrians(self.graph(False),[self.feature()],lambda _:'Reviewed')))
 def test_distant_same_id_never_connects(self):
  self.assertFalse(self.links(merge_pedestrians(self.graph(),[self.feature(offset=.0001)],lambda _:'Reviewed')))
 def test_pathway_requires_eligible_matching_osm_feature(self):
  g=merge_pedestrians(self.graph(),[self.feature(kind='Pathway')],lambda _:'Reviewed')
  self.assertTrue(any(e['id'].startswith('pbc:') for e in g['edges']))
  g=merge_pedestrians(self.graph(False),[self.feature(kind='Pathway')],lambda _:'Reviewed')
  self.assertFalse(any(e['id'].startswith('pbc:') for e in g['edges']))
