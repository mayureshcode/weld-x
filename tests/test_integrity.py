import dataclasses
import tempfile
import threading
import time
import unittest
from pathlib import Path
from weldx.engine import Denied, Engine, Journal, rank_key
from weldx.model import Base
from weldx.validation import Result
from .support import configuration, TestAdapter

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.adapter=TestAdapter()
        self.e=Engine(configuration(),Journal(Path(self.tmp.name)/'a.jsonl'),self.adapter)
    def tearDown(self):self.tmp.cleanup()
    def test_scene_hash_mismatch_blocks(self):
        self.adapter.synchronize=lambda *args:'wrong-scene'
        self.e.revalidate();self.assertFalse(self.e.authorized());self.assertEqual(self.e.stage,'STOPPED')
    def test_scene_sync_error_blocks_and_is_recorded(self):
        def fail(*args):raise RuntimeError('scene unavailable fixture')
        self.adapter.synchronize=fail;self.e.revalidate()
        self.assertFalse(self.e.authorized());self.assertTrue(any(x['kind']=='scene_synchronization_error' for x in self.e.journal.events))
    def test_tracking_error_threshold_enforced(self):
        execute=self.adapter.execute
        self.adapter.execute=lambda *args:dataclasses.replace(execute(*args),tracking_error_rad=1.0)
        self.e.revalidate();self.assertFalse(self.e.execute());self.assertEqual(self.e.stage,'STOPPED')
    def test_config_mutation_invalidates_authorization(self):
        self.e.revalidate();self.e.config=self.e.config.model_copy(update={'base':Base(x_m=0.1,y_m=0)})
        self.assertFalse(self.e.authorized())
        with self.assertRaises(Denied):self.e.execute()
    def test_missing_audit_health_revokes(self):
        self.e.revalidate();self.e.journal.healthy=False
        self.assertFalse(self.e.authorized())
    def test_search_attempt_budget_and_rejections_audited(self):
        self.adapter.fail=True;self.e.detect()
        for _ in range(self.e.config.search.max_attempts):self.e.search()
        with self.assertRaises(Denied):self.e.search()
        self.assertEqual(self.e.journal.events[-1]['kind'],'operation_rejected')
    def test_cumulative_time_budget(self):
        self.e.detect();self.e.search_seconds=self.e.config.search.total_seconds
        with self.assertRaises(Denied):self.e.search()
    def test_expired_evaluation_is_incomplete(self):
        r=self.e.evaluate(self.e.config,'search',threading.Event(),time.monotonic()-1)
        self.assertEqual(r.nominal.outcome(self.e.config,self.adapter.version),Result.UNKNOWN)
        self.assertFalse(r.qualifies(self.e.config,self.adapter))
    def test_backend_planning_exception_is_unknown(self):
        def fail(*args):raise RuntimeError('planner fixture crash')
        self.adapter.validate=fail;r=self.e.detect()
        self.assertEqual(r.nominal.outcome(self.e.config,self.adapter.version),Result.UNKNOWN)
        self.assertTrue(any(x['kind']=='adapter_error' for x in self.e.journal.events))
    def test_hard_failure_ranks_after_qualifying_candidate(self):
        self.e.detect();self.e.search();good=next(iter(self.e.candidates.values()))
        self.adapter.fail=True;r=self.e.evaluate(good.configuration,'search',threading.Event(),time.monotonic()+10)
        bad=dataclasses.replace(good,evaluation=r,relocation_m=0)
        self.assertLess(rank_key(good,self.adapter,self.e.config),rank_key(bad,self.adapter,self.e.config))
    def test_nonfinite_measurement_rejected(self):
        r=self.e.evaluate(self.e.config,'search',threading.Event(),time.monotonic()+10)
        checks=list(r.nominal.checks);checks[0]=dataclasses.replace(checks[0],margin=float('nan'))
        invalid=dataclasses.replace(r.nominal,checks=tuple(checks))
        self.assertEqual(invalid.outcome(self.e.config,self.adapter.version),Result.UNKNOWN)
    def test_non_string_engineer_rejected(self):
        self.e.detect();self.e.search()
        with self.assertRaises(Denied):self.e.approve(self.e.recommended,self.e.config.digest(),123)
    def test_invalid_adapter_plan_contract_fails_closed(self):
        self.e.revalidate();self.adapter.validate=lambda *args:None
        self.e.detect();self.assertFalse(self.e.authorized())
        self.assertTrue(any(x['kind']=='adapter_error' for x in self.e.journal.events))
    def test_invalid_execution_contract_stops(self):
        self.e.revalidate();self.adapter.execute=lambda *args:None
        with self.assertRaises(TypeError):self.e.execute()
        self.assertEqual(self.e.stage,'STOPPED');self.assertFalse(self.e.authorized())
    def test_unknown_mc_does_not_publish_failure_rate(self):
        from weldx.robustness import aggregate
        r=self.e.evaluate(self.e.config,'heldout',threading.Event(),time.monotonic()+10)
        trials=list(r.robustness.trials)
        i=next(i for i,t in enumerate(trials) if t.scenario.kind=='mc')
        trials[i]=dataclasses.replace(trials[i],outcome=Result.UNKNOWN)
        summary=aggregate(self.e.config,'heldout',trials)
        group=next(g for g in summary.groups if g.source==trials[i].scenario.source)
        self.assertIsNone(group.empirical_rate);self.assertIsNone(group.wilson95)
