"""Fast hard-constraint boundary rejection on actual planned full-job paths.
No scenario can PASS here. Passing this screen is inconclusive until collision
validation and complete perturbed execution have run. No compensation is assumed.
"""
import time
from weldx.robustness import scenarios,Trial
from weldx.validation import Result
from .perturbation import perturb
from .uncertain_execution import error,exceeds

def boundaries(adapter,c,phase,cancel,deadline):
    cached=adapter.plans.get(c.digest());trials=[]
    if not cached:return trials
    for scenario in scenarios(c,phase):
        if scenario.kind!='boundary':continue
        if cancel.is_set() or time.monotonic()>=deadline:break
        perturbed=perturb(c,scenario);failure=None;maximum=0.;angle=0.
        for name,trajectory,info in cached[1]:
            if not name.endswith(':weld'):continue
            for point in trajectory.points:
                q=dict(zip(trajectory.joint_names,point.positions));e=error(adapter.cell,c,perturbed,scenario.model,q,q)
                maximum=max(maximum,e['tcp_error_m']);angle=max(angle,e['orientation_error_rad'])
                if exceeds(maximum,c.constraints.position_tolerance_m) or exceeds(angle,c.constraints.orientation_tolerance_rad):
                    failure=(name,'tcp_tolerance');break
            if failure:break
        reason=f'fixed-command boundary preflight: model TCP error {maximum:.9g} m, orientation {angle:.9g} rad; '+('declared constraint fails' if failure else 'screen inconclusive; collision and complete perturbed execution still required')
        plan=adapter.unknown(c,reason,failure);outcome=plan.outcome(c,adapter.version)
        trials.append(Trial(scenario,plan,outcome))
        adapter.reports.append({'scenario':scenario.__dict__,'config_hash':c.digest(),'outcome':outcome.value,'complete_job_executed':False,'maximum_screened_tcp_error_m':maximum,'reason':reason,'scope':'kinematic boundary preflight on actual model and nominal trajectories; not a complete-job success'})
    return trials
