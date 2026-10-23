import tempfile,unittest
from pathlib import Path
from weldx.engine import Engine,Journal,Denied
from .support import configuration,TestAdapter

class ApplicationSyncTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.a=TestAdapter();self.e=Engine(configuration(),Journal(Path(self.tmp.name)/'a.jsonl'),self.a)
  self.e.detect();self.e.search();self.approval=self.e.approve(self.e.recommended,self.e.config.digest(),'Labelled unit-test engineer')
 def tearDown(self):self.tmp.cleanup()
 def test_apply_synchronizes_exact_new_version_and_requires_revalidation(self):
  seen=[];self.a.synchronize=lambda c,*args:seen.append(c.digest()) or c.digest()
  old=self.e.config;new=self.e.apply(self.approval['id'])
  self.assertEqual(new.revision,old.revision+1);self.assertEqual(seen,[new.digest()])
  self.assertFalse(self.e.authorized());self.assertIsNone(self.e.approval)
  self.assertEqual(self.e.stage,'APPLY')
  with self.assertRaises(Denied):self.e.execute()
 def test_unconfirmed_apply_stops_without_rollback_or_reused_approval(self):
  self.a.synchronize=lambda *args:None
  c=self.e.apply(self.approval['id']);self.assertEqual(c.revision,2)
  self.assertEqual(self.e.stage,'STOPPED');self.assertFalse(self.e.authorized())
  self.assertTrue(any(e['kind']=='application_synchronization_unconfirmed' for e in self.e.journal.events))
  with self.assertRaises(Denied):self.e.apply(self.approval['id'])
 def test_observed_runtime_drift_revokes_authorization(self):
  self.e.apply(self.approval['id']);self.e.revalidate();self.assertTrue(self.e.authorized())
  self.a.binding_valid=lambda c:False
  self.assertFalse(self.e.authorized())
  with self.assertRaises(Denied):self.e.execute()
