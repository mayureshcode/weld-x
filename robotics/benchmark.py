"""Predeclared benchmark evaluation, explicit rejected vs incomplete vs accepted."""
import json,rclpy,time,threading
from pathlib import Path
from weldx.model import Configuration
from weldx.engine import Engine,Journal,serial
from .adapter import RosAdapter

def main():
    directory=Path('benchmarks/recovery_v1');c=Configuration.model_validate_json((directory/'configuration.json').read_text());meta=json.loads((directory/'preregistration.json').read_text())
    import hashlib
    assert hashlib.sha256(Path(meta['strict_job_path']).read_bytes()).hexdigest()==meta['strict_job_sha256']
    rclpy.init();a=RosAdapter()
    try:
        e=Engine(c,Journal('.runtime/recovery-v1-evaluation.jsonl'),a);result=e.detect()
        failures=[{'scenario':serial(t.scenario),'checks':[serial(v) for v in t.plan.checks if v.result.value=='fail']} for t in result.robustness.trials if t.outcome.value=='fail']
        report={'configuration_hash':c.digest(),'result':'accepted' if result.qualifies(c,a) else 'rejected' if result.robustness.outcome.value=='fail' else 'incomplete','nominal':result.nominal.outcome(c,a.version).value,'robustness':result.robustness.outcome.value,'boundary_tested':len(result.robustness.trials),'boundary_failures':failures,'groups':serial(result.robustness.groups),'elapsed_s':result.elapsed_s,'mc_target':.99,'mc_declared_per_source':100,'actual_mc_complete_jobs_executed':0,'measurement_compensation':'none; no measured physical specifications or independent-error compensation is claimed','limitations':'Boundary preflight rejects invalid commanded paths; screened survivors are unknown, not successful jobs. Monte Carlo acceptance is not attempted when a mandatory boundary fails.'}
        (directory/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n');(directory/'validation-evidence.json').write_text(json.dumps(serial(result),indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['boundary_failures','groups']},indent=2))
    finally:a.cell.active_cancel=None;a.cell.active_deadline=None;a.close();rclpy.shutdown()

if __name__=='__main__':main()
