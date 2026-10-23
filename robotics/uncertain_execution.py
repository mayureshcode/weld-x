"""Real complete-job uncertainty trial; no perfect-knowledge job replanning.
The model source is TCP calibration mismatch only: a virtual actual-TCP transform
relative to the nominal tool. It does not claim link, mass or compliance fidelity.
"""
from pathlib import Path
import hashlib,json,time
from dataclasses import replace
import numpy as np
from scipy.spatial.transform import Rotation
from weldx.engine import serial
from weldx.validation import Check,Plan,GATES,Result,ScenarioExecution,scenario_digest
from .cell import RoboticsError,NAMES

def exceeds(value,limit):
    # 1 picometre/radian absolute numerical guard for exact boundary roundoff;
    # declared engineering tolerances and scenario amplitudes are unchanged.
    return value-limit>1e-12

def error(cell,c,perturbed,model,expected,actual):
    commanded=cell.fk(expected);measured=cell.fk(actual)
    rw=Rotation.from_euler('xyz',[c.workpiece.roll_rad,c.workpiece.pitch_rad,c.workpiece.yaw_rad])
    rb=Rotation.from_euler('z',c.base.yaw_rad)
    world=rb.apply(commanded[:3,3])+[c.base.x_m,c.base.y_m,c.base_height_m]
    local=rw.inv().apply(world-[c.workpiece.x_m,c.workpiece.y_m,c.workpiece.z_m])
    desired_rotation=Rotation.from_euler('z',perturbed.base.yaw_rad).inv()*Rotation.from_euler('xyz',[perturbed.workpiece.roll_rad,perturbed.workpiece.pitch_rad,perturbed.workpiece.yaw_rad])*rw.inv()*rb*Rotation.from_matrix(commanded[:3,:3])
    desired=cell.target(perturbed,local,[0,0,0]);target=np.array([desired.position.x,desired.position.y,desired.position.z])
    true_tcp=measured[:3,3]+measured[:3,:3]@np.array(model[:3]);true_rotation=Rotation.from_matrix(measured[:3,:3])*Rotation.from_euler('z',model[3])
    return {'tcp_error_m':float(np.linalg.norm(true_tcp-target)),'orientation_error_rad':float((desired_rotation.inv()*true_rotation).magnitude())}

def run(adapter,c,perturbed,scenario,segments,cancel,deadline):
    cell=adapter.cell;completed=[];observations=[];start=time.monotonic();failure=None
    estimated=sum(info['duration_s'] for name,t,info in segments)+40
    identity=adapter.plans[c.digest()][0]
    record={'scenario':serial(scenario),'scenario_hash':scenario_digest(scenario),'config_hash':c.digest(),
        'adapter_version':adapter.version,'trajectory_id':identity,'outcome':'unknown','complete_job_executed':False,
        'scope':'actual Gazebo open-loop experiment; virtual TCP calibration mismatch, not physical dynamics'}
    if deadline-time.monotonic()<estimated:
        record['reason']='insufficient remaining budget for complete perturbed execution and restoration'
        adapter.reports.append(record)
        return adapter.unknown(c,record['reason'])
    cell.active_deadline=deadline-20;current_name=c.job.segments()[0]
    try:
        adapter.scene.synchronize(perturbed,allow_respawn=True);cell.ready();cell.sync_planning(perturbed)
        initial=dict(zip(segments[0][1].joint_names,segments[0][1].points[0].positions))
        if max(abs(cell.values()[n]-initial[n]) for n in NAMES)>1e-4:
            reset=cell.plan_joint(perturbed,cell.values(),initial);cell.inspect(perturbed,reset);cell.execute_segment(c,reset,cancel)
        for name,trajectory,info in segments:
            current_name=name
            observer=lambda expected,actual:error(cell,c,perturbed,scenario.model,expected,actual)
            observation=cell.execute_segment(c,trajectory,cancel,observer)
            endpoint=observer(dict(zip(trajectory.joint_names,trajectory.points[-1].positions)),cell.values())
            errors=observation['scenario_feedback']+[endpoint]
            max_position=max(e['tcp_error_m'] for e in errors);max_angle=max(e['orientation_error_rad'] for e in errors)
            observations.append({'segment':name,'max_actual_scenario_tcp_error_m':max_position,
                'max_actual_scenario_orientation_error_rad':max_angle,
                'controller_tracking':{k:v for k,v in observation.items() if k!='scenario_feedback'}})
            if exceeds(max_position,c.constraints.position_tolerance_m) or exceeds(max_angle,c.constraints.orientation_tolerance_rad):
                failure=(name,'tcp_tolerance',f'actual perturbed execution residual {max_position}m/{max_angle}rad');break
            completed.append(name)
        record['complete_job_executed']=tuple(completed)==c.job.segments()
    except RoboticsError as exc:
        record['error']={'constraint':exc.constraint,'type':type(exc).__name__,'reason':str(exc)}
        if exc.constraint in ('tcp_tolerance','collision','joint_limits','dynamics'):
            failure=(current_name,exc.constraint,str(exc))
    except Exception as exc:
        record['error']={'constraint':'unknown','type':type(exc).__name__,'reason':str(exc)}
    finally:
        cell.active_cancel=None;cell.active_deadline=None
        try:
            restoration=adapter.scene.synchronize(c,allow_respawn=True);cell.ready();cell.sync_planning(c)
            record['restoration']={'confirmed':True,'readback':restoration}
        except Exception as exc:
            record['restoration']={'confirmed':False,'error':str(exc),'type':type(exc).__name__}
        record.update(completed_segments=completed,segment_observations=observations,elapsed_s=time.monotonic()-start)
    proof=None
    if observations and record['restoration']['confirmed']:
        proof=ScenarioExecution(c.digest(),adapter.version,scenario_digest(scenario),identity,tuple(completed),
            tuple(o['controller_tracking']['feedback_samples'] for o in observations),
            max(o['controller_tracking']['maximum_in_motion_tracking']['joint_error_rad'] for o in observations),
            max(o['max_actual_scenario_tcp_error_m'] for o in observations),
            max(o['max_actual_scenario_orientation_error_rad'] for o in observations),True,
            'Gazebo joint feedback and actual FollowJointTrajectory action feedback; virtual TCP calibration model',
            tuple(o['segment'] for o in observations))
        record['execution_evidence']=serial(proof)
    if not record['restoration']['confirmed']:
        result=adapter.unknown(c,'restoration unconfirmed; all execution authorization blocked');adapter.bound=None
    elif failure:
        record['outcome']='fail';result=replace(adapter.unknown(c,failure[2],failure[:2]),execution_evidence=proof,trajectory_id=identity)
    elif record['complete_job_executed']:
        result=Plan(c.digest(),adapter.version,tuple(Check(s,g,Result.PASS,
            'complete observed perturbed job; exact scenario receipt and verified scene restoration')
            for s in c.job.segments() for g in GATES),identity,proof)
        if proof and proof.confirms(c,scenario,result):record['outcome']='pass'
        else:result=adapter.unknown(c,'complete-job observer receipt did not confirm required evidence')
    else:
        result=adapter.unknown(c,'perturbed execution incomplete: '+str(record.get('error','no complete observed segment sequence')))
    adapter.reports.append(record)
    directory=Path('evidence/phase3/scenarios');directory.mkdir(parents=True,exist_ok=True)
    filename=hashlib.sha256((c.digest()+scenario.id+str(time.monotonic_ns())).encode()).hexdigest()+'.json'
    (directory/filename).write_text(json.dumps(record,indent=2)+'\n')
    return result
