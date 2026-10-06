import tempfile,unittest
from pathlib import Path
from server.addresses import AddressIndex
class AddressTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.index=AddressIndex(Path(self.tmp.name)/'a.sqlite')
  self.index.replace('boca',[{'id':'1','label':'123 Verbena Way, Boca Raton, FL 33433','lat':26.35,'lon':-80.16},{'id':'2','label':'124 Verbena Way, Boca Raton, FL 33433','lat':26.35,'lon':-80.16}])
 def tearDown(self):self.tmp.cleanup()
 def test_prefix(self):self.assertEqual(len(self.index.search('12','boca')),2)
 def test_wrong_suffix_keeps_house_number(self):
  r=self.index.search('123 verbena rd.','boca');self.assertEqual(r[0]['label'],'123 Verbena Way, Boca Raton, FL 33433');self.assertTrue(r[0]['suggested_correction'])
 def test_unknown_house_is_not_invented(self):self.assertEqual(self.index.search('999 verbena','boca'),[])
 def test_region_isolated(self):self.assertEqual(self.index.search('123','hollywood'),[])
 def test_punctuation_safe(self):self.index.search('" OR * --','boca')
