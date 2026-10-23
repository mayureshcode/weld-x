"""Purpose-labelled unit-test double. NOT robot kinematics or simulation evidence."""
from pathlib import Path
import hashlib
from weldx.model import Configuration
from weldx.validation import Check, Execution, GATES, Plan, Result

def configuration(**updates):
    c = Configuration.model_validate_json(Path('examples/job_01.json').read_text())
    data = c.model_dump(mode='json')
    data['model_version'] = 'TEST-DOUBLE-NOT-A-ROBOT'
    data['search'].update(max_candidates=6, max_seconds=10)
    data['uncertainty'].update(mc_count=3,min_mc_count=3)
    data.update(updates)
    return Configuration.model_validate(data)

class TestAdapter:
    """Only exercises orchestration. Never wired to the dashboard or production."""
    version = 'TEST-DOUBLE-ONLY/v1'
    ready = True
    def __init__(self):
        self.calls = []
        self.fail = False
        self.heldout_fail = False
        self.execution_incomplete = False
        self.execution_error = False
    def health(self):
        return {'adapter':'test-double','robot_model':'not-a-robot'}
    def synchronize(self, config, cancel, deadline):
        return config.digest()
    def validate(self, config, scenario, cancel, deadline):
        self.calls.append((config.digest(), scenario.id))
        fails = self.fail or (self.heldout_fail and scenario.id.startswith('heldout:'))
        checks = tuple(Check(s,g,Result.FAIL if fails and g=='collision' else Result.PASS,
                             'unit-test fixture only', margin=0.2) for s in config.job.segments() for g in GATES)
        return Plan(config.digest(), self.version, checks, 'test-plan:'+config.digest())
    def execute(self, config, plan, cancel, deadline):
        if self.execution_error:
            raise RuntimeError('deliberate controller fixture error')
        segments = config.job.segments()[:-1] if self.execution_incomplete else config.job.segments()
        return Execution(config.digest(), plan.trajectory_id, segments, True, False, 0.001, 'TEST DOUBLE ONLY')
