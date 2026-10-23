"""Actual complete nominal job test. No robustness or approval claim."""
import argparse,json,time
from pathlib import Path
import rclpy
from weldx.model import Configuration
from .cell import Cell,RoboticsError

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default='examples/commissioning_two_seam.json');p.add_argument('--execute',action='store_true');args=p.parse_args()
    rclpy.init();cell=Cell();start=time.monotonic();report={'config_file':args.config,'result':'failed','scope':'actual MoveIt/FCL/Gazebo nominal integration, not robustness or approval-gated production execution'}
    try:
        c=Configuration.model_validate_json(Path(args.config).read_text());report['config_hash']=c.digest();report['controllers']=cell.ready();report['fk_cross_check']=cell.verify_fk()
        segments=cell.build_job(c);report['planned_segments']=[{'segment':name,**info} for name,trajectory,info in segments];report['executed_segments']=[]
        if args.execute:
            for name,trajectory,info in segments:
                evidence=cell.execute_segment(c,trajectory);report['executed_segments'].append({'segment':name,**evidence});print('EXECUTED',name,evidence,flush=True)
        report['complete_job_executed']=bool(args.execute and len(report['executed_segments'])==len(segments));report['result']='passed'
    except Exception as exc:
        report['error']={'type':type(exc).__name__,'constraint':getattr(exc,'constraint',None),'reason':str(exc)}
        raise
    finally:
        report['elapsed_s']=time.monotonic()-start;Path('evidence/phase2/nominal-job.json').write_text(json.dumps(report,indent=2)+'\n');Path('evidence/phase2/nominal-job-trace.json').write_text(json.dumps(list(cell.trace))+'\n');cell.close();rclpy.shutdown()

if __name__=='__main__':main()
