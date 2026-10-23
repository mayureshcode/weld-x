"""One evidence object for the recorded paired experiment; no human data invented."""
from pathlib import Path
import json,hashlib
import pandas as pd
root=Path(__file__).resolve().parent.parent
source=root/'evidence/phase3/policy-comparison/results.json'
blocks=json.loads(source.read_text());protocol=json.loads((root/'benchmarks/policy_comparison_v1/protocol.json').read_text())
assert len(blocks)==len(protocol['jobs'])*len(protocol['search_seed_blocks'])
rows=[];candidates=[];executions=[]
for b in blocks:
 assert b['candidate_count']<=protocol['candidate_budget_per_block']
 for c in b['candidates']:candidates.append({'block':b['block'],**c})
 for p in b['policies']:rows.append({'block':b['block'],**p})
 for key,e in b['nominal_execution_records'].items():executions.append({'block':b['block'],'candidate_id':key,'outcome':e['outcome'],'heldout':e.get('heldout_boundary_status','unknown')})
df=pd.DataFrame(rows);cf=pd.DataFrame(candidates);ef=pd.DataFrame(executions)
assert len(df)==len(blocks)*len(protocol['policies']);assert cf.groupby('block').size().sum()==sum(b['candidate_count'] for b in blocks)
counts=[]
for b in blocks:
 subset=cf[cf.block==b['block']]
 row={'block':b['block'],'total':len(subset),'nominally_infeasible':int((subset.nominal=='fail').sum()),
      'nominally_feasible_not_robust':int(((subset.nominal=='pass')&(subset.robustness=='fail')).sum()),
      'robustly_feasible':int(((subset.nominal=='pass')&(subset.robustness=='pass')).sum())}
 row['unknown']=row['total']-sum(row[k] for k in ('nominally_infeasible','nominally_feasible_not_robust','robustly_feasible'))
 assert row['unknown']>=0;counts.append(row)
# Independent direct-list headline check, not another aggregation of the frame.
raw_nominal=sum(c['nominal']=='pass' for b in blocks for c in b['candidates'])
assert raw_nominal==int((cf.nominal=='pass').sum())
raw_unique_pass=sum(e['outcome']=='pass' for b in blocks for e in b['nominal_execution_records'].values())
assert raw_unique_pass==int((ef.outcome=='pass').sum())
summary=[]
for name in protocol['policies']:
 g=df[df.policy==name]
 summary.append({'policy':name,'blocks':len(g),'selected':int(g.selected_candidate.notna().sum()),
     'nominal_pass_records':int((g.nominal_complete_execution_outcome=='pass').sum()),
     'heldout_boundary_fail_records':int((g.heldout_boundary_status=='fail').sum()),
     'fully_qualified':int((g.robustness_status=='pass').sum()),
     'relocation_m':g.relocation_m.dropna().tolist(),'joint_limit_margin_rad':g.joint_limit_margin_rad.dropna().tolist(),
     'policy_wall_time_s':None,'human_task_time_s':None})
evidence={'source':str(source.relative_to(root)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'population':'two existing jobs × two preregistered search seed blocks; shared actual candidate pool per block; no statistical independence of policy replay outcomes',
 'metrics':{'blocks':len(blocks),'candidate_evaluations':len(cf),'nominally_feasible_candidates':raw_nominal,'unique_nominal_executions':len(ef),'unique_nominal_execution_passes':raw_unique_pass,'qualified_candidates':int(((cf.nominal=='pass')&(cf.robustness=='pass')).sum())},
 'policy_summary':summary,'candidate_class_counts':counts,'manual_trial_available':False,
 'paired_replay':'The same cached candidate can be selected by multiple policies. Actual execution is reused, not counted as independent repeated executions.',
 'missing_measurements':['Human manual selection/task time','Independent per-policy search wall time','Monte Carlo empirical complete-job success rate'],
 'comparison_plan':[{'question':'Which evaluated placements passed nominal versus robust gates?','grain':'actual candidate per job/seed block','unit':'candidate count','finding':'No nominally feasible candidate qualified robustly' if not any(c['robustly_feasible'] for c in counts) else 'Some candidates qualified','delivery':'stacked count chart and policy lookup table','reason':'Mutually exclusive complete pool classes; not reliability probabilities'},
 {'question':'Does a nominal execution demonstrate robustness?','grain':'unique selected candidate execution per block','unit':'observed job outcome','delivery':'prose/table','reason':'Shared replay is not independent policy performance or a human study'}]}
out=root/'evidence/phase3/analysis';out.mkdir(parents=True,exist_ok=True)
(out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');df.to_csv(out/'policy-records.csv',index=False)
labels=[r['block'] for r in counts];series=[]
for key,label in [('nominally_feasible_not_robust','Nominal feasible, robustness failed'),('nominally_infeasible','Nominal infeasible'),('unknown','Unknown/incomplete'),('robustly_feasible','Robustly feasible')]:
 values=[r[key] for r in counts]
 if any(values):series.append({'label':label,'valueKind':'count','role':'base','data':values})
spec={'version':1,'form':'categorical-bars','mode':'stacked','orientation':'horizontal','title':'Nominal feasibility did not produce a robustness-qualified placement' if evidence['metrics']['qualified_candidates']==0 else 'Actual candidate validation outcomes','aside':'Shared evaluated pools, not job reliability rates','labels':labels,'axis':{'zero':True},'series':series}
(out/'candidate-status-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
print(json.dumps({'metrics':evidence['metrics'],'policies':[(p['policy'],p['nominal_pass_records'],p['fully_qualified']) for p in summary]}))
