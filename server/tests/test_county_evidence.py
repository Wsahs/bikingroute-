import unittest
from server.county_evidence import supplement, matches
from server.import_osm import convert
from server.routing import eligible

class CountyEvidenceTests(unittest.TestCase):
 def doc(self,tags=None):
  return {'elements':[{'type':'node','id':1,'lat':26.35,'lon':-80.1},{'type':'node','id':2,'lat':26.351,'lon':-80.1},{'type':'way','id':42,'nodes':[1,2],'tags':tags or {'highway':'footway'}}]}
 def feature(self,kind='Sidewalk',coords=None):
  return {'properties':{'osm_id':42,'OBJECTID':9,'Existing_T':kind},'geometry':{'type':'LineString','coordinates':coords or [[-80.099999,26.35],[-80.099999,26.351]]}}
 def test_matching_complete_geometry_supplies_missing_sidewalk_classification(self):
  raw=self.doc();doc,report=supplement(raw,[self.feature()]);self.assertEqual(doc['elements'][-1]['tags']['footway'],'sidewalk');self.assertNotIn('footway',raw['elements'][-1]['tags']);self.assertEqual(report['sidewalk_ways'],1)
 def test_partial_line_cannot_classify_whole_way(self):
  doc,_=supplement(self.doc(),[self.feature(coords=[[-80.1,26.35],[-80.1,26.3501]])]);self.assertNotIn('footway',doc['elements'][-1]['tags'])
 def test_parallel_path_is_not_same_geometry(self):
  doc,_=supplement(self.doc(),[self.feature(coords=[[-80.1001,26.35],[-80.1001,26.351]])]);self.assertNotIn('footway',doc['elements'][-1]['tags'])
 def test_bicycle_ban_still_blocks_supplemented_sidewalk(self):
  doc,_=supplement(self.doc({'highway':'footway','bicycle':'no'}),[self.feature()]);g=convert(doc,sidewalk_policy=lambda _:'Reviewed');self.assertFalse(any(eligible(e) for e in g['edges']))
 def test_missing_crossing_marking_can_use_county_evidence(self):
  doc,report=supplement(self.doc({'highway':'footway','footway':'crossing'}),[self.feature('Crosswalk - Ladder')]);self.assertEqual(doc['elements'][-1]['tags']['crossing'],'marked');self.assertEqual(report['marked_crossing_ways'],1)
 def test_explicit_unmarked_crossing_is_not_overridden(self):
  doc,_=supplement(self.doc({'highway':'footway','footway':'crossing','crossing':'unmarked'}),[self.feature('Crosswalk - Ladder')]);self.assertEqual(doc['elements'][-1]['tags']['crossing'],'unmarked')

 def test_same_vertices_in_different_order_cannot_create_shortcut(self):
  a=[[-80.1,26.35],[-80.1,26.351],[-80.099,26.351],[-80.099,26.35]]
  self.assertFalse(matches(a,[a[0],a[2],a[1],a[3]]))
