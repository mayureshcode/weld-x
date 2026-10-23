"""Hard failures remain failures without inventing incomplete Monte Carlo rates."""
import dataclasses,threading,time,unittest
from .support import configuration,TestAdapter
from weldx.robustness import scenarios,Trial,aggregate
from weldx.validation import Check,Plan,GATES,Result

class BoundaryEvidenceTests(unittest.TestCase):
 def test_confirmed_boundary_failure_rejects_even_before_mc(self):
  c=configuration();s=next(scenarios(c,'search'))
  p=Plan(c.digest(),'unit-test',tuple(Check(seg,g,Result.FAIL if g=='tcp_tolerance' else Result.UNKNOWN,'labelled unit fixture') for seg in c.job.segments() for g in GATES))
  result=aggregate(c,'search',[Trial(s,p,Result.FAIL)])
  self.assertEqual(result.outcome,Result.FAIL);self.assertIsNone(result.groups[0].empirical_rate)
 def test_opposed_base_fixture_boundaries_exist(self):
  c=configuration();ss=[s for s in scenarios(c,'search') if s.source=='combined' and s.kind=='boundary']
  self.assertTrue(any(s.base[0]*s.fixture[0]<0 and s.base[1]*s.fixture[1]<0 for s in ss))
 def test_corrupted_duplicate_boundary_is_not_trusted(self):
  c=configuration();s=next(scenarios(c,'search'));p=Plan(c.digest(),'unit-test',())
  self.assertEqual(aggregate(c,'search',[Trial(s,p,Result.FAIL)]*2).outcome,Result.UNKNOWN)
