import unittest
from server.import_osm import convert
from server.routing import eligible


def document(tags=None, node_tags=None):
    return {'elements': [
        {'type':'node','id':1,'lat':26.35,'lon':-80.10,'tags': node_tags or {}},
        {'type':'node','id':2,'lat':26.351,'lon':-80.10},
        {'type':'way','id':99,'nodes':[1,2], 'tags':tags or {'highway':'path','bicycle':'yes'}}]}

class DataTests(unittest.TestCase):
    def test_connected_bidirectional_explicit_bicycle_path(self):
        result=convert(document())
        self.assertEqual(len(result['edges']),2)
        self.assertTrue(all(eligible(e) for e in result['edges']))
        self.assertGreater(result['edges'][0]['length_m'],100)
        self.assertFalse(result['metadata']['coverage_complete'])

    def test_sidewalk_unknown_permission_excluded(self):
        result=convert(document({'highway':'footway','footway':'sidewalk'}))
        self.assertEqual(len(result['edges']),2)
        self.assertFalse(any(eligible(e) for e in result['edges']))

    def test_road_sidewalk_tag_does_not_become_separate_path(self):
        result=convert(document({'highway':'residential','sidewalk':'both','bicycle':'yes'}))
        self.assertEqual(len(result['edges']),2)
        self.assertEqual(result['edges'][0]['kind'],'street')
        self.assertFalse(eligible(result['edges'][0]))
        self.assertEqual(result['metadata']['audit']['roads_with_unseparated_sidewalks'],1)

    def test_documented_curb_ramps_do_not_disconnect_paths(self):
        for kerb in ('lowered', 'flush', 'no'):
            with self.subTest(kerb=kerb):
                result=convert(document(node_tags={'barrier':'kerb','kerb':kerb}))
                self.assertTrue(any(eligible(e) for e in result['edges']))

    def test_curb_ramp_does_not_override_explicit_restriction(self):
        result=convert(document(node_tags={'barrier':'kerb','kerb':'lowered','bicycle':'no'}))
        self.assertFalse(any(eligible(e) for e in result['edges']))

    def test_unknown_or_raised_curb_remains_unresolved(self):
        for kerb in ('raised', 'yes', None):
            result=convert(document(node_tags={'barrier':'kerb','kerb':kerb}))
            self.assertFalse(any(eligible(e) for e in result['edges']))

    def test_barrier_node_blocks_even_if_way_allows_bicycles(self):
        result=convert(document(node_tags={'barrier':'gate'}))
        self.assertEqual(len(result['edges']),2)
        self.assertFalse(any(eligible(e) for e in result['edges']))

    def test_conditional_access_excluded(self):
        result=convert(document({'highway':'cycleway','bicycle:conditional':'no @ (sunset-sunrise)'}))
        self.assertEqual(len(result['edges']),2)
        self.assertFalse(any(eligible(e) for e in result['edges']))

    def test_private_way_excluded(self):
        result=convert(document({'highway':'path','bicycle':'yes','access':'private'}))
        self.assertEqual(len(result['edges']),2)
        self.assertFalse(any(eligible(e) for e in result['edges']))

    def test_reverse_one_way(self):
        result=convert(document({'highway':'cycleway','oneway':'-1'}))
        self.assertEqual(len(result['edges']),1)
        self.assertEqual(result['edges'][0]['from'],'2')

    def test_no_connection_created_for_coincident_unshared_nodes(self):
        doc=document()
        doc['elements'] += [{'type':'node','id':3,'lat':26.351,'lon':-80.10},
            {'type':'node','id':4,'lat':26.352,'lon':-80.10},
            {'type':'way','id':100,'nodes':[3,4],'tags':{'highway':'cycleway'}}]
        result=convert(doc)
        self.assertEqual(len(result['edges']),4)
        self.assertFalse(any(e['from']=='2' and e['to']=='3' for e in result['edges']))

    def test_missing_node_never_bridged(self):
        doc=document()
        doc['elements'][-1]['nodes']=[1,666,2]
        result=convert(doc)
        self.assertEqual(len(result['edges']),0)
        self.assertEqual(result['metadata']['audit']['missing_node_segments'],2)

    def test_remark_means_incomplete_download(self):
        doc=document();doc['remark']='runtime error: timed out'
        with self.assertRaises(ValueError):
            convert(doc)

class SidewalkPolicyTests(unittest.TestCase):
    def test_reviewed_sidewalk_default_does_not_require_osm_bicycle_tag(self):
        g=convert(document({'highway':'footway','footway':'sidewalk'}),sidewalk_policy=lambda points: 'Reviewed jurisdiction')
        self.assertTrue(all(eligible(e) for e in g['edges']))
        self.assertEqual(g['edges'][0]['permission_basis'],'Reviewed jurisdiction')
    def test_default_never_overrides_explicit_restriction(self):
        for extra in [{'bicycle':'no'},{'access':'private'},{'bicycle:conditional':'no @ (night)'}]:
            g=convert(document(dict(highway='footway',footway='sidewalk',**extra)),sidewalk_policy=lambda points:'Reviewed jurisdiction')
            self.assertFalse(any(eligible(e) for e in g['edges']))
    def test_general_trail_not_assumed_to_be_public_sidewalk(self):
        g=convert(document({'highway':'path'}),sidewalk_policy=lambda points:'Reviewed jurisdiction')
        self.assertFalse(any(eligible(e) for e in g['edges']))
    def test_unmarked_crossing_still_excluded(self):
        g=convert(document({'highway':'footway','footway':'crossing','crossing':'unmarked'}),sidewalk_policy=lambda points:'Reviewed jurisdiction')
        self.assertFalse(any(eligible(e) for e in g['edges']))
    def test_marked_crossing_node_supplies_missing_way_designation(self):
        g=convert(document({'highway':'footway','footway':'crossing','bicycle':'yes'}, {'highway':'crossing','crossing':'marked'}))
        self.assertTrue(all(eligible(e) for e in g['edges']))
    def test_pedestrian_refuge_island_keeps_crossing_connected(self):
        g=convert(document({'highway':'footway','footway':'traffic_island'}),sidewalk_policy=lambda points:'Reviewed sidewalk law')
        self.assertTrue(all(eligible(e) for e in g['edges']))
        self.assertTrue(all(e['kind']=='sidewalk' for e in g['edges']))
    def test_traffic_island_does_not_override_bicycle_ban(self):
        g=convert(document({'highway':'footway','footway':'traffic_island','bicycle':'no'}),sidewalk_policy=lambda points:'Reviewed sidewalk law')
        self.assertFalse(any(eligible(e) for e in g['edges']))
