"""Run all predefined nominal fixtures through actual planning and execution.
Explicit test harness, not approval/robustness-authorized commissioning execution.
"""
import argparse,json,time,rclpy
from pathlib import Path
from weldx.model import Configuration
from .cell import Cell
from .scene import SceneTransport

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output-dir',default='evidence/phase2');args=parser.parse_args();output=Path(args.output_dir);output.mkdir(parents=True,exist_ok=True)
 manifest=json.loads(Path('benchmarks/nominal_jobs/manifest.json').read_text());rclpy.init();cell=Cell();scene=SceneTransport();reports=[]
 try:
  cell.ready()
  for path in manifest['jobs']:
   c=Configuration.model_validate_json(Path(path).read_text());start=time.monotonic();record={'job':c.job.id,'config_hash':c.digest(),'path':path,'result':'failed','completed_segments':[],'scope':manifest['scope']}
   try:
    scene.synchronize(c);segments=cell.build_job(c);record['planned_segments']=[{'segment':n,**info} for n,t,info in segments]
    for name,t,info in segments:
     evidence=cell.execute_segment(c,t);evidence.pop('scenario_feedback',None);record['completed_segments'].append({'segment':name,**evidence})
    assert tuple(s['segment'] for s in record['completed_segments'])==c.job.segments();record['result']='passed'
   except Exception as e:record['error']={'type':type(e).__name__,'constraint':getattr(e,'constraint',None),'reason':str(e)}
   finally:
    record['elapsed_s']=time.monotonic()-start;reports.append(record);(output/'nominal-suite.json').write_text(json.dumps(reports,indent=2)+'\n');print(c.job.id,record['result'],record.get('error',''),flush=True)
  if any(r['result']!='passed' for r in reports):raise SystemExit(1)
 finally:cell.close();rclpy.shutdown()

if __name__=='__main__':main()
