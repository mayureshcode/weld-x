"""Receipt integrity tests. All adapters here are explicitly labelled unit doubles."""
import dataclasses,unittest,threading,time
from weldx.robustness import aggregate,scenarios,Trial
from weldx.validation import Result
from .support import configuration,TestAdapter

class ReceiptTests(unittest.TestCase):
 def setUp(self):
  self.c=configuration();self.a=TestAdapter();self.s=next(scenarios(self.c,'search'))
  self.p=self.a.validate(self.c,self.s,threading.Event(),time.monotonic()+10)
 def result(self,p):return aggregate(self.c,'search',[Trial(self.s,p,Result.PASS)],self.a.version)
 def test_plan_pass_without_execution_cannot_pass_boundary(self):
  r=self.result(dataclasses.replace(self.p,execution_evidence=None))
  self.assertEqual(r.trials[0].outcome,Result.UNKNOWN);self.assertEqual(r.groups[0].boundary_executed,0)
 def test_exact_receipt_preserves_complete_execution(self):
  r=self.result(self.p);self.assertEqual(r.trials[0].outcome,Result.PASS)
  self.assertEqual(r.groups[0].boundary_executed,1);self.assertEqual(r.groups[0].boundary_passed,1)
  self.assertEqual(r.groups[0].mc_not_run,self.c.uncertainty.mc_count)
 def test_stale_receipt_is_unknown(self):
  for change in [dict(scenario_hash='stale'),dict(config_hash='stale'),dict(adapter_version='stale'),
                 dict(trajectory_id='stale'),dict(completed_segments=()),dict(restored=False),
                 dict(feedback_samples_per_segment=(0,)*len(self.c.job.segments())),
                 dict(maximum_tcp_error_m=.1),dict(maximum_tracking_error_rad=float('nan'))]:
   with self.subTest(change=change):
    p=dataclasses.replace(self.p,execution_evidence=dataclasses.replace(self.p.execution_evidence,**change))
    self.assertEqual(self.result(p).trials[0].outcome,Result.UNKNOWN)
 def test_rate_is_unavailable_for_partial_mc(self):
  s=next(s for s in scenarios(self.c,'search') if s.kind=='mc');p=self.a.validate(self.c,s,threading.Event(),time.monotonic()+10)
  self.assertIsNone(aggregate(self.c,'search',[Trial(s,p,Result.PASS)]).groups[0].empirical_rate)
 def test_planning_only_failures_do_not_invent_empirical_mc_rate(self):
  from weldx.validation import Check
  trials=[]
  for s in scenarios(self.c,'search'):
   p=self.a.validate(self.c,s,threading.Event(),time.monotonic()+10)
   if s.kind=='mc':
    checks=tuple(dataclasses.replace(c,result=Result.FAIL) for c in p.checks)
    p=dataclasses.replace(p,checks=checks,execution_evidence=None)
   trials.append(Trial(s,p,p.outcome(self.c,self.a.version)))
  r=aggregate(self.c,'search',trials)
  self.assertTrue(all(g.empirical_rate is None and g.mc_executed==0 for g in r.groups))
  self.assertEqual(r.outcome,Result.UNKNOWN)
