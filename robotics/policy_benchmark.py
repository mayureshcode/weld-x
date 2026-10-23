"""Preregistered, non-authorizing paired actual-robotics policy experiment."""
import json,time,threading,hashlib,math
from pathlib import Path
import rclpy
from weldx.model import Configuration
from weldx.engine import Engine,Journal,Candidate,grid,refine,rank_key,serial
from weldx.validation import Result
from weldx.robustness import scenarios,aggregate
from .adapter import RosAdapter

def nominal_rank(c):
    margins=[v.margin for v in c.evaluation.nominal.checks if v.constraint=='joint_limits' and v.margin is not None]
    b=c.configuration.base
    return (-min(margins) if margins else float('inf'),c.relocation_m,b.x_m,b.y_m,b.yaw_rad)

def main():
    directory=Path('evidence/phase3/policy-comparison');directory.mkdir(parents=True,exist_ok=True)
    protocol=json.loads(Path('benchmarks/policy_comparison_v1/protocol.json').read_text())
    for path,digest in protocol['input_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    # Freeze all scenario definitions before any actual evaluation.
    configs=[]
    for path in protocol['jobs']:
        original=Configuration.model_validate_json(Path(path).read_text())
        for seed in protocol['search_seed_blocks']:
            c=original.model_copy(update={'uncertainty':original.uncertainty.model_copy(update={'search_seed':seed,'heldout_seed':protocol['heldout_seed']})})
            configs.append((path,seed,c))
    frozen=[{'job_path':p,'seed':seed,'config':c.model_dump(mode='json'),'search':serial(tuple(scenarios(c,'search'))),'heldout':serial(tuple(scenarios(c,'heldout')))} for p,seed,c in configs]
    manifest=directory/'frozen-scenarios.json';manifest.write_text(json.dumps(frozen,indent=2)+'\n')
    rclpy.init();adapter=RosAdapter();results=[];cancel=threading.Event()
    try:
        for path,seed,c in configs:
            start=time.monotonic();deadline=start+protocol['wall_budget_per_block_s'];block=f'{c.job.id}-{seed}'
            engine=Engine(c,Journal(directory/(block+'.jsonl')),adapter);candidates=[];metrics=[];seen=set()
            source=iter(grid(c.search));fine=iter(())
            for index in range(protocol['candidate_budget_per_block']):
                if time.monotonic()>=deadline:break
                if index==6:
                    good=[v for v in candidates if v.evaluation.nominal.outcome(v.configuration,adapter.version)==Result.PASS]
                    fine=iter(refine(sorted(good,key=nominal_rank)[:1],c.search))
                base=None
                for iterator in (fine,source):
                    for proposed in iterator:
                        key=(proposed.x_m,proposed.y_m,proposed.yaw_rad)
                        if key not in seen and c.search.contains(proposed):seen.add(key);base=proposed;break
                    if base is not None:break
                if base is None:break
                cc=c.model_copy(update={'base':base});evaluation=engine.evaluate(cc,'search',cancel,deadline)
                candidate=Candidate(cc.digest(),c.digest(),cc,evaluation,math.hypot(base.x_m-c.base.x_m,base.y_m-c.base.y_m));candidates.append(candidate)
                engine._event('comparison_candidate',serial(candidate))
                metrics.append({'candidate_id':candidate.id,'base':base.model_dump(),'status':evaluation.status(cc,adapter).value,
                    'nominal':evaluation.nominal.outcome(cc,adapter.version).value,'robustness':evaluation.robustness.outcome.value,
                    'elapsed_s':evaluation.elapsed_s,'groups':serial(evaluation.robustness.groups)})
            nominal=[v for v in candidates if v.evaluation.nominal.outcome(v.configuration,adapter.version)==Result.PASS]
            robust=[v for v in candidates if v.evaluation.qualifies(v.configuration,adapter)]
            selected={'fixed_original_placement_proxy':next((v for v in candidates if v.configuration.base==c.base),None),
                'nominal_first_feasible':nominal[0] if nominal else None,'nominal_ranked':min(nominal,key=nominal_rank) if nominal else None,
                'robust_hard_gated':min(robust,key=lambda v:rank_key(v,adapter,c)) if robust else None}
            executions={};policies=[]
            for policy,v in selected.items():
                record={'policy':policy,'selected_candidate':v.id if v else None,'manual_human_trial':False,
                    'candidate_count':len(candidates),'relocation_m':v.relocation_m if v else None,
                    'joint_limit_margin_rad':-nominal_rank(v)[0] if v and v in nominal else None,
                    'robustness_status':v.evaluation.robustness.outcome.value if v else 'no_qualifying_candidate',
                    'nominal_complete_execution_outcome':'not_run','heldout_boundary_status':'not_run',
                    'mc_empirical_rate':None,'note':'Paired replay, not separate full search wall-clock benchmark or commissioning approval.'}
                if v and v in nominal:
                    cc=v.configuration
                    if v.id not in executions:
                        observed={'scope':'actual nominal execution harness, not robust/approved commissioning','outcome':'unknown'}
                        try:
                            adapter.synchronize(cc,cancel,time.monotonic()+60)
                            execution=adapter.execute(cc,v.evaluation.nominal,cancel,time.monotonic()+cc.constraints.execution_timeout_s)
                            heldout=adapter.preflight_boundaries(cc,'heldout',cancel,time.monotonic()+60)
                            summary=aggregate(cc,'heldout',heldout,adapter.version)
                            observed.update(outcome='pass' if execution.success and execution.completed_segments==cc.job.segments() else 'fail',execution=serial(execution),heldout_boundary_status=summary.outcome.value,heldout_groups=serial(summary.groups))
                        except Exception as exc:
                            observed['error']={'type':type(exc).__name__,'message':str(exc)}
                        executions[v.id]=observed
                    record.update(nominal_complete_execution_outcome=executions[v.id]['outcome'],heldout_boundary_status=executions[v.id].get('heldout_boundary_status','unknown'))
                policies.append(record)
            result={'block':block,'source_job':path,'config_hash':c.digest(),'seed':seed,'candidate_count':len(candidates),
                'pool_evaluation_elapsed_s':sum(m['elapsed_s'] for m in metrics),'total_wall_s':time.monotonic()-start,
                'termination':'candidate_budget' if len(candidates)==protocol['candidate_budget_per_block'] else 'time_budget',
                'candidates':metrics,'policies':policies,'nominal_execution_records':executions,
                'manual_baseline_status':'unavailable; fixed placement is a proxy, not measured human performance',
                'limitations':'No simulated MC success rate, physical probability, significance or successful approved recovery is claimed.'}
            results.append(result);(directory/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            print(block,'candidates',len(candidates),[(p['policy'],p['nominal_complete_execution_outcome'],p['robustness_status']) for p in policies],flush=True)
    finally:
        adapter.cell.active_cancel=None;adapter.cell.active_deadline=None
        # Restore the actual reference scene even when an experiment fails.
        try:adapter.synchronize(Configuration.model_validate_json(Path(protocol['jobs'][0]).read_text()),threading.Event(),time.monotonic()+60)
        finally:adapter.close();rclpy.shutdown()

if __name__=='__main__':main()
