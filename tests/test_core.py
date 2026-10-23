import dataclasses
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from pydantic import ValidationError
from weldx.model import Configuration, Base
from weldx.validation import GATES, Check, Plan, Result
from weldx.robustness import SOURCES, Trial, aggregate, scenarios, wilson
from weldx.engine import Candidate, Denied, Engine, Journal, grid, rank_key, refine
from .support import configuration, TestAdapter

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.journal = Journal(Path(self.tmp.name)/'audit.jsonl')
        self.adapter = TestAdapter()
        self.engine = Engine(configuration(), self.journal, self.adapter)
    def tearDown(self):
        self.tmp.cleanup()
    def recovered(self):
        self.engine.detect()
        self.engine.search()
        approval = self.engine.approve(self.engine.recommended, self.engine.config.digest(), 'Test engineer')
        self.engine.apply(approval['id'])
        return approval
    def test_schema_units_and_unknown_fields(self):
        for update in [{'units':'mm,deg'}, {'unknown':1}, {'revision':0}, {'base':{'x_m':float('nan'),'y_m':0}}, {'base':{'x_m':0,'y_m':0,'z_m':1}}]:
            with self.subTest(update=update), self.assertRaises(ValidationError):
                configuration(**update)
    def test_search_and_uncertainty_schema(self):
        data = configuration().model_dump(mode='json')
        data['search']['x_m']['minimum'] = 99
        with self.assertRaises(ValidationError): Configuration.model_validate(data)
        data = configuration().model_dump(mode='json')
        data['uncertainty']['heldout_seed'] = data['uncertainty']['search_seed']
        with self.assertRaises(ValidationError): Configuration.model_validate(data)
    def test_immutable_configuration_and_digest(self):
        c = configuration()
        self.assertEqual(c.digest(), Configuration.model_validate_json(c.model_dump_json()).digest())
        with self.assertRaises(ValidationError): c.base.x_m=1
        self.assertNotEqual(c.digest(), c.model_copy(update={'revision':2}).digest())
    def test_multi_seam_job_segment_order(self):
        c=Configuration.model_validate_json(Path('examples/job_02.json').read_text())
        self.assertEqual(c.job.segments()[3], 'seam_1->seam_2:transition')
        self.assertEqual(len(c.job.segments()), 7)
    def test_all_five_example_jobs_parse(self):
        for path in Path('examples').glob('job_*.json'):
            self.assertTrue(Configuration.model_validate_json(path.read_text()).job.seams)
    def test_grid_and_refinement_bounds(self):
        e=self.engine
        self.assertTrue(all(e.config.search.contains(b) for b in grid(e.config.search)))
        e.detect(); e.search()
        self.assertTrue(all(e.config.search.contains(b) for b in refine(list(e.candidates.values()),e.config.search)))
        self.assertLessEqual(len(e.candidates), e.config.search.max_candidates)
    def test_extremely_fine_grid_is_lazy(self):
        c=configuration()
        s=c.search.model_copy(update={'x_m':c.search.x_m.model_copy(update={'step':1e-12})})
        iterator=grid(s)
        self.assertTrue(s.contains(next(iterator)))
    def test_missing_duplicate_and_stale_checks_unknown(self):
        e=self.engine
        p=e.evaluate(e.config,'search',threading.Event(),time.monotonic()+10).nominal
        self.assertEqual(p.outcome(e.config,e.adapter.version),Result.PASS)
        for altered in [dataclasses.replace(p,checks=p.checks[:-1]),dataclasses.replace(p,checks=p.checks+(p.checks[0],)),dataclasses.replace(p,config_hash='stale'),dataclasses.replace(p,trajectory_id=None)]:
            self.assertEqual(altered.outcome(e.config,e.adapter.version),Result.UNKNOWN)
    def test_hard_failure_cannot_be_overridden(self):
        self.adapter.fail=True
        result=self.engine.detect()
        self.assertFalse(result.qualifies(self.engine.config,self.adapter))
        self.assertEqual(result.nominal.outcome(self.engine.config,self.adapter.version),Result.FAIL)
        with self.assertRaises(Denied): self.engine.execute()
    def test_unavailable_runtime_never_authorizes(self):
        e=Engine(configuration(),self.journal)
        r=e.revalidate()
        self.assertEqual(r.nominal.outcome(e.config,e.adapter.version),Result.UNKNOWN)
        self.assertFalse(e.authorized())
        with self.assertRaises(Denied):e.execute()
    def test_fixed_scenarios_reproducible_and_heldout_separate(self):
        c=configuration()
        self.assertEqual(tuple(scenarios(c,'search')),tuple(scenarios(c,'search')))
        self.assertNotEqual(tuple(scenarios(c,'search')),tuple(scenarios(c,'heldout')))
        self.assertEqual(set(s.source for s in scenarios(c,'search')),set(SOURCES))
    def test_robustness_unknown_insufficient_duplicate_and_boundary(self):
        c=configuration()
        r=self.engine.evaluate(c,'heldout',threading.Event(),time.monotonic()+10).robustness
        self.assertEqual(r.outcome,Result.PASS)
        self.assertEqual(aggregate(c,'heldout',r.trials[:-1]).outcome,Result.UNKNOWN)
        self.assertEqual(aggregate(c,'heldout',r.trials+(r.trials[0],)).outcome,Result.UNKNOWN)
        changed=list(r.trials)
        # A confirmed failure needs the corresponding failed constraint record.
        checks=list(changed[0].plan.checks);checks[0]=dataclasses.replace(checks[0],result=Result.FAIL)
        changed[0]=dataclasses.replace(changed[0],plan=dataclasses.replace(changed[0].plan,checks=tuple(checks)),outcome=Result.FAIL)
        self.assertEqual(aggregate(c,'heldout',changed).outcome,Result.FAIL)
        larger=c.model_copy(update={'uncertainty':c.uncertainty.model_copy(update={'min_mc_count':100})})
        self.assertEqual(aggregate(larger,'heldout',r.trials).outcome,Result.UNKNOWN)
    def test_wilson_interval_not_certain_at_all_success(self):
        lo,hi=wilson(3,3)
        self.assertGreater(lo,0)
        self.assertLess(lo,1)
        self.assertAlmostEqual(hi,1)
    def test_budget_and_no_solution(self):
        self.adapter.fail=True
        e=self.engine;e.detect();e.search()
        self.assertIsNone(e.recommended)
        self.assertLessEqual(e.last_search['candidate_count'],e.config.search.max_candidates)
        self.assertTrue(any(x['kind']=='no_solution' for x in self.journal.events))
    def test_ranking_deterministic_and_feasible_first(self):
        e=self.engine;e.detect();e.search()
        ranked=sorted(e.candidates.values(),key=lambda c:rank_key(c,self.adapter,e.config))
        self.assertEqual(e.recommended,ranked[0].id)
        self.assertEqual(ranked[0].relocation_m,min(c.relocation_m for c in ranked))
    def test_approval_requires_exact_hash_and_candidate(self):
        e=self.engine;e.detect();e.search()
        for candidate, digest, engineer in [('fake',e.config.digest(),'Engineer'),(e.recommended,'stale','Engineer'),(e.recommended,e.config.digest(),'')]:
            with self.assertRaises(Denied): e.approve(candidate,digest,engineer)
    def test_version_application_and_single_use_approval(self):
        before=self.engine.config.digest()
        approval=self.recovered()
        self.assertEqual(self.engine.config.revision,2)
        self.assertNotEqual(before,self.engine.config.digest())
        self.assertFalse(self.engine.authorized())
        with self.assertRaises(Denied):self.engine.apply(approval['id'])
        with self.assertRaises(Denied):self.engine.execute()
    def test_complete_test_double_workflow_and_single_use_execution(self):
        self.recovered()
        self.engine.revalidate()
        self.assertTrue(self.engine.authorized())
        self.assertTrue(self.engine.execute())
        self.assertEqual(self.engine.stage,'COMPLETE')
        with self.assertRaises(Denied):self.engine.execute()
    def test_stale_model_and_health_reject_execution(self):
        self.engine.revalidate()
        self.adapter.version='changed'
        self.assertFalse(self.engine.authorized())
        with self.assertRaises(Denied):self.engine.execute()
    def test_disconnect_revokes_authorization(self):
        self.engine.revalidate();self.adapter.ready=False
        self.assertFalse(self.engine.authorized())
        with self.assertRaises(Denied):self.engine.execute()
    def test_revalidation_failure_and_bounded_stop(self):
        self.recovered();self.adapter.heldout_fail=True
        self.engine.revalidate()
        self.assertEqual(self.engine.stage,'STOPPED')
        self.assertFalse(self.engine.authorized())
        self.engine.recoveries=self.engine.config.max_recoveries
        with self.assertRaises(Denied):self.engine.search()
    def test_cancelled_validation_never_authorizes(self):
        cancel=threading.Event();cancel.set()
        self.engine.revalidate(cancel)
        self.assertFalse(self.engine.authorized())
    def test_incomplete_observed_execution_rejected(self):
        self.engine.revalidate();self.adapter.execution_incomplete=True
        self.assertFalse(self.engine.execute())
        self.assertEqual(self.engine.stage,'STOPPED')
    def test_controller_exception_records_stop(self):
        self.engine.revalidate();self.adapter.execution_error=True
        with self.assertRaises(RuntimeError):self.engine.execute()
        self.assertEqual(self.engine.stage,'STOPPED')
        self.assertFalse(self.engine.authorized())
        self.assertTrue(any(x['kind']=='execution_error' for x in self.journal.events))
    def test_audit_roundtrip_and_tampering(self):
        self.engine.detect()
        reread=Journal(self.journal.path)
        self.assertEqual(reread.events,self.journal.events)
        lines=self.journal.path.read_text().splitlines()
        record=json.loads(lines[0]);record['kind']='tampered';lines[0]=json.dumps(record)
        self.journal.path.write_text('\n'.join(lines)+'\n')
        with self.assertRaises(Denied):Journal(self.journal.path)
    def test_snapshot_json_contract(self):
        self.engine.detect();self.engine.search()
        data=json.loads(json.dumps(self.engine.snapshot(),allow_nan=False))
        self.assertIn('health',data);self.assertIn('candidates',data);self.assertIn('audit',data)
        self.assertEqual(data['configuration']['job']['id'],'job_01')
    def test_operation_lock(self):
        self.engine._begin('fixture')
        with self.assertRaises(Denied):self.engine.detect()
        self.engine._end()

if __name__=='__main__':unittest.main()
