import unittest
from server.directions import RoadNames, directions

def road(name, points):
 return {'properties':{'STREET':name,'OBJECTID':1},'geometry':{'type':'LineString','coordinates':points}}
def segment(points,kind='sidewalk',name='Sidewalk',distance=100):
 return dict(geometry=points,kind=kind,name=name,distance_m=distance)
class DirectionsTests(unittest.TestCase):
 def test_parallel_official_street_is_context_not_sidewalk_identity(self):
  index=RoadNames([road('W Palmetto Park Rd',[[-80.2,26.35],[-80.19,26.35]])])
  s=segment([[-80.199,26.3501],[-80.198,26.3501]])
  match=index.context(s)
  self.assertEqual(match['street'],'W Palmetto Park Rd')
  self.assertEqual(match['basis'],'Nearby parallel county road')
 def test_perpendicular_nearby_road_not_assigned_to_sidewalk(self):
  index=RoadNames([road('Wrong Rd',[[-80.2,26.349],[-80.2,26.351]])])
  self.assertIsNone(index.context(segment([[-80.2002,26.3501],[-80.1998,26.3501]])))
 def test_two_equally_close_roads_are_ambiguous(self):
  index=RoadNames([road('North Rd',[[-80.2,26.3502],[-80.19,26.3502]]),road('South Rd',[[-80.2,26.35],[-80.19,26.35]])])
  self.assertIsNone(index.context(segment([[-80.199,26.3501],[-80.198,26.3501]])))
 def test_crossing_names_only_intersected_road(self):
  index=RoadNames([road('Main Rd',[[-80.2,26.35],[-80.19,26.35]])])
  self.assertEqual(index.context(segment([[-80.195,26.3499],[-80.195,26.3501]],'crossing'))['street'],'Main Rd')
  self.assertIsNone(index.context(segment([[-80.195,26.3501],[-80.195,26.3502]],'crossing')))
 def test_turns_and_arrival_keep_exact_distance(self):
  rows=directions([segment([[-80,26],[-79.999,26]],name='East Trail'),segment([[-79.999,26],[-79.999,25.999]],name='South Trail')])
  self.assertEqual(rows[1]['maneuver'],'right')
  self.assertIn('South Trail',rows[1]['instruction'])
  self.assertEqual(rows[-1]['maneuver'],'arrive')
  self.assertEqual(sum(r['distance_m'] for r in rows),200)
 def test_driveways_merge_but_street_sections_stay_separate(self):
  ss=[segment([[-80,26],[-79.999,26]],name='Main Trail'),segment([[-79.999,26],[-79.9989,26]],'crossing','Sidewalk across driveway',10),segment([[-79.9989,26],[-79.998,26]],name='Main Trail'),segment([[-79.998,26],[-79.997,26]],'street','Main Rd')]
  rows=directions(ss)
  self.assertEqual(rows[0]['distance_m'],210)
  self.assertEqual(rows[0]['driveways'],1)
  self.assertEqual(rows[1]['kind'],'street')
 def test_sharp_turn_on_same_named_path_not_hidden(self):
  rows=directions([segment([[-80,26],[-79.999,26]],name='Trail'),segment([[-79.999,26],[-79.999,25.999]],name='Trail')])
  self.assertEqual(rows[1]['maneuver'],'right')

 def test_crossing_pieces_become_one_instruction(self):
  idx=RoadNames([road('Main Rd',[[-80.2,26.35],[-80.19,26.35]])])
  ss=[segment([[-80.195,26.3498],[-80.195,26.3499]],'crossing',distance=10),segment([[-80.195,26.3499],[-80.195,26.3501]],'crossing',distance=20),segment([[-80.195,26.3501],[-80.195,26.3502]],'crossing',distance=10)]
  rows=directions(ss,idx)
  self.assertEqual(len(rows),2)
  self.assertEqual(rows[0]['instruction'],'Cross Main Rd')
  self.assertEqual(rows[0]['distance_m'],40)
 def test_long_path_can_match_multiple_county_road_segments(self):
  idx=RoadNames([road('Main Rd',[[-80.2,26.35],[-80.198,26.35],[-80.196,26.35],[-80.194,26.35],[-80.19,26.35]])])
  self.assertEqual(idx.context(segment([[-80.199,26.3501],[-80.191,26.3501]]))['street'],'Main Rd')

 def test_curbramp_is_included_in_crossing_not_a_tiny_turn(self):
  ss=[segment([[-80,26],[-79.999,26]],'crossing',distance=100),segment([[-79.999,26],[-79.999,25.99998]],distance=2),segment([[-79.999,25.99998],[-79.998,25.99998]],name='Trail')]
  rows=directions(ss)
  self.assertEqual(rows[0]['distance_m'],102)
  self.assertEqual(len(rows),3)

 def test_tiny_hairpin_is_not_hidden_as_curb_approach(self):
  rows=directions([segment([[-80,26],[-79.999,26]],'crossing'),segment([[-79.999,26],[-79.99905,26]],distance=5),segment([[-79.99905,26],[-80,26]],name='Trail')])
  self.assertEqual(rows[1]['maneuver'],'uturn')
 def test_absorbed_curb_preserves_exit_heading(self):
  rows=directions([segment([[-80,26],[-79.999,26]],'crossing'),segment([[-79.999,26],[-79.999,25.99998]],distance=2),segment([[-79.999,25.99998],[-79.998,25.99998]],name='Trail')])
  self.assertEqual(rows[1]['maneuver'],'left')
