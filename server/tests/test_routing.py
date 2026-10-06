import unittest
from server.routing import plan, SearchLimitError


def graph(edges, complete=True):
    ids, records = set(), []
    for index, item in enumerate(edges):
        a, b, length, kind = item[:4]
        ids.update((a, b))
        edge = dict(id=str(index), **{'from': a, 'to': b}, length_m=length,
                    kind=kind, bicycle_allowed=True, assessed=True,
                    quiet_verified=True, designated=True, name='Test connection',
                    geometry=[[-80.1, 26.35], [-80.11, 26.36]], source='synthetic test')
        if len(item) > 4:
            edge.update(item[4])
        records.append(edge)
    return dict(nodes=[dict(id=n, lat=26.35, lon=-80.1) for n in ids], edges=records,
                metadata=dict(coverage_complete=complete, name='Synthetic test graph', demo=True))

class RoutingTests(unittest.TestCase):
    def test_long_primary_is_not_replaced_by_a_road(self):
        result = plan(graph([('a','b',20000,'trail'),('a','b',500,'street')]), 'a','b', 5)
        self.assertEqual(result.get('status'), 'primary')
        self.assertEqual(result['primary']['distance_m'], 20000)

    def test_shortest_qualifying_primary(self):
        result = plan(graph([('a','b',500,'trail'),('a','c',100,'sidewalk'),('c','b',100,'crossing')]),'a','b')
        self.assertEqual(result.get('status'), 'primary')
        self.assertEqual(result['primary']['distance_m'], 200)
        self.assertEqual(result['primary']['street_distance_m'], 0)
        self.assertEqual(result['primary']['crossings'], 1)

    def test_minimizes_total_street_distance_not_overall_distance(self):
        result = plan(graph([('a','x',30,'street'),('x','b',10000,'trail'),('a','b',60,'street')]),'a','b')
        self.assertEqual(result.get('status'), 'fallback')
        self.assertEqual(result['alternative']['street_distance_m'], 30)
        self.assertEqual(result['alternative']['distance_m'],10030)

    def test_boundary_confirmation(self):
        result = plan(graph([('a','b',4902.336,'trail'),('a','b',402.336,'street')]),'a','b',5)
        self.assertEqual(result.get('status'), 'confirmation')
        self.assertTrue(result['requires_confirmation'])
        self.assertAlmostEqual(result['extra_seconds'],900)

    def test_over_quarter_mile_does_not_prompt(self):
        result=plan(graph([('a','b',10000,'trail'),('a','b',402.337,'street')]),'a','b',5)
        self.assertEqual(result.get('status'),'primary')

    def test_under_fifteen_minutes_does_not_prompt(self):
        result=plan(graph([('a','b',4695,'trail'),('a','b',200,'street')]),'a','b',5)
        self.assertEqual(result.get('status'),'primary')

    def test_sum_all_street_segments_for_threshold(self):
        result=plan(graph([('a','b',10000,'trail'),('a','x',250,'street'),('x','b',250,'street')]),'a','b',5)
        self.assertEqual(result.get('status'),'primary')

    def test_search_other_alternative_when_minimum_street_option_too_slow(self):
        result=plan(graph([('a','b',10000,'trail'),('a','x',5,'street'),('x','b',9000,'trail'),
                           ('a','y',100,'street'),('y','b',500,'trail')]),'a','b',5)
        self.assertEqual(result.get('status'),'confirmation')
        self.assertEqual(result['alternative']['street_distance_m'],100)

    def test_unknown_access_is_not_permission(self):
        result=plan(graph([('a','b',100,'sidewalk',{'bicycle_allowed':None})],False),'a','b')
        self.assertEqual(result.get('status'),'insufficient_data')

    def test_unassessed_and_closed_edges_excluded(self):
        for attrs in ({'assessed':False},{'closed':True},{'bicycle_allowed':False}):
            result=plan(graph([('a','b',100,'trail',attrs)]),'a','b')
            self.assertEqual(result.get('status'),'no_route')

    def test_street_must_have_quiet_evidence(self):
        result=plan(graph([('a','b',100,'street',{'quiet_verified':False})]),'a','b')
        self.assertEqual(result.get('status'),'no_route')

    def test_crossing_must_be_designated(self):
        result=plan(graph([('a','b',100,'crossing',{'designated':False})]),'a','b')
        self.assertEqual(result.get('status'),'no_route')

    def test_direction_is_respected(self):
        result=plan(graph([('a','b',100,'trail')]),'b','a')
        self.assertEqual(result.get('status'),'no_route')

    def test_disconnected_is_not_an_error(self):
        result=plan(graph([('a','x',100,'trail'),('b','y',100,'trail')]),'a','b')
        self.assertEqual(result.get('status'),'no_route')

    def test_same_endpoint_zero_distance(self):
        result=plan(graph([('a','b',100,'trail')]),'a','a')
        self.assertEqual(result.get('status'),'primary')
        self.assertEqual(result['primary']['distance_m'],0)

    def test_invalid_speed_rejected(self):
        for speed in (0,-1,float('nan'),float('inf'),100):
            with self.assertRaises(ValueError):
                plan(graph([('a','b',100,'trail')]),'a','b',speed)

    def test_unknown_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            plan(graph([('a','b',100,'trail')]),'x','b')

    def test_invalid_edge_lengths_rejected(self):
        for length in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                plan(graph([('a','b',length,'trail')]),'a','b')

    def test_search_limit_never_claims_no_route(self):
        with self.assertRaises(SearchLimitError):
            plan(graph([('a','b',100,'trail')]),'a','b',max_states=0)

    def test_positive_cycles_cannot_improve_route(self):
        result=plan(graph([('a','x',10,'street'),('x','a',10,'street'),('x','b',100,'trail')]),'a','b')
        self.assertEqual(result.get('status'),'fallback')
        self.assertEqual(result['alternative']['street_distance_m'],10)
