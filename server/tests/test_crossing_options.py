import unittest
from server.crossing_options import apply_options, catalog
from server.routing import eligible
class CrossingOptionTests(unittest.TestCase):
 def graph(self):
  return {'edges':[{'kind':'crossing','bicycle_allowed':True,'assessed':True,'designated':False,'crossing_option':{'id':'42','name':'Example Street'}}]}
 def test_default_stays_excluded(self):self.assertFalse(eligible(apply_options(self.graph(),{})['edges'][0]))
 def test_preview_and_accept_are_distinct(self):
  e=apply_options(self.graph(),{},True)['edges'][0];self.assertTrue(eligible(e));self.assertTrue(e['approval_required'])
  e=apply_options(self.graph(),{'42':True})['edges'][0];self.assertTrue(eligible(e));self.assertFalse(e['approval_required'])
 def test_decline_excludes_crossing_even_in_preview(self):self.assertFalse(eligible(apply_options(self.graph(),{'42':False},True)['edges'][0]))
 def test_choice_cannot_override_bicycle_ban(self):
  g=self.graph();g['edges'][0]['bicycle_allowed']=False;self.assertFalse(eligible(apply_options(g,{'42':True})['edges'][0]))
 def test_choices_must_be_boolean(self):
  with self.assertRaises(ValueError):apply_options(self.graph(),{'42':'yes'})
 def document(self,road='residential'):
  nodes=[{'type':'node','id':i,'lat':26.35+(i-2)*.00005,'lon':-80.1} for i in range(1,6)]
  def way(i,ns,t):return {'type':'way','id':i,'nodes':ns,'tags':t}
  return {'elements':nodes+[way(42,[1,2,3],{'highway':'footway','footway':'crossing','crossing':'unmarked'}),way(43,[4,1],{'highway':'footway','footway':'sidewalk'}),way(44,[3,5],{'highway':'footway','footway':'sidewalk'}),way(45,[4,2,5],{'highway':road,'name':'Example Street'})]}
 def test_catalog_requires_side_street_and_reviewed_jurisdiction(self):
  self.assertIn('42',catalog(self.document(),lambda _:True))
  self.assertFalse(catalog(self.document('primary'),lambda _:True))
  self.assertFalse(catalog(self.document(),lambda _:False))
 def test_catalog_rejects_road_overlap(self):
  doc=self.document();doc['elements'][-1]['nodes']=[1,2,3];self.assertFalse(catalog(doc,lambda _:True))
 def test_catalog_requires_sidewalk_at_both_ends(self):
  doc=self.document();doc['elements'][-2]['tags'].pop('footway');self.assertFalse(catalog(doc,lambda _:True))
 def test_trip_requires_each_choice_and_recalculates_after_decline(self):
  from unittest.mock import patch
  from server.sidewalk_trip import trip
  from test_routing import graph
  g=graph([('a','b',1000,'path'),('a','c',50,'crossing',{'designated':False,'crossing_option':{'id':'42','name':'One'}}),('c','b',50,'crossing',{'designated':False,'crossing_option':{'id':'43','name':'Two'}})])
  def access(_g,_e,lat,lon):return [{'id':'a' if lat==26 else 'b','component':'a','distance_m':0}]
  with patch('server.sidewalk_trip.with_path_access',side_effect=lambda g,_:g),patch('server.sidewalk_trip.access_points',side_effect=access):
   def run(choices):return trip(g,{'lat':26,'lng':-80},{'lat':27,'lng':-80},choices)
   initial=run({});self.assertEqual(initial['primary']['distance_m'],1000);self.assertEqual(len(initial['crossing_choices']),2)
   partial=run({'42':True});self.assertEqual(partial['primary']['distance_m'],1000);self.assertEqual([c['id'] for c in partial['crossing_choices']],['43'])
   yes=run({'42':True,'43':True});self.assertEqual(yes['primary']['distance_m'],100);self.assertNotIn('crossing_proposal',yes);self.assertTrue(any('unmarked' in w for w in yes['warnings']))
   no=run({'42':False});self.assertEqual(no['primary']['distance_m'],1000);self.assertNotIn('crossing_proposal',no)
