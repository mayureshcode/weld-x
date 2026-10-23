"""Real complete-job uncertainty trial; no perfect-knowledge job replanning.
The model source is TCP calibration mismatch only: a virtual actual-TCP transform
relative to the nominal tool. It does not claim link, mass or compliance fidelity.
"""
from pathlib import Path
import hashlib,json,time
import numpy as np
from scipy.spatial.transform import Rotation
from weldx.engine import serial
from weldx.validation import Check,Plan,GATES,Result
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
    # Reserve restoration time before changing experimental geometry. Conservative
    # wall estimate uses 1x simulation even when the server requests faster physics.
    estimated=sum(info['duration_s'] for name,t,info in segments)+40
    if deadline-time.monotonic()<estimated:
        adapter.reports.append({'scenario':serial(scenario),'config_hash':c.digest(),'outcome':'unknown','complete_job_executed':False,'reason':'insufficient remaining budget for complete perturbed execution and restoration'})
        return adapter.unknown(c,'insufficient remaining budget for complete perturbed Gazebo execution and restoration')
    cell.active_deadline=deadline-20;current_name=c.job.segments()[0]
    record={'scenario':serial(scenario),'config_hash':c.digest(),'outcome':'unknown','complete_job_executed':False,'scope':'actual Gazebo open-loop experiment; virtual TCP calibration mismatch, not a physical dynamics model'}
    try:
        adapter.scene.synchronize(perturbed,allow_respawn=True);cell.ready();cell.sync_planning(perturbed)
        initial=dict(zip(segments[0][1].joint_names,segments[0][1].points[0].positions))
        if max(abs(cell.values()[n]-initial[n]) for n in NAMES)>1e-4:
            reset=cell.plan_joint(perturbed,cell.values(),initial);cell.inspect(perturbed,reset);cell.execute_segment(c,reset,cancel)
        for name,trajectory,info in segments:
            current_name=name
            observer=lambda expected,actual:error(cell,c,perturbed,scenario.model,expected,actual)
            observation=cell.execute_segment(c,trajectory,cancel,observer if name.endswith(':weld') else None)
            endpoint=observer(dict(zip(trajectory.joint_names,trajectory.points[-1].positions)),cell.values())
            errors=observation['scenario_feedback']+[endpoint]
            max_position=max(e['tcp_error_m'] for e in errors);max_angle=max(e['orientation_error_rad'] for e in errors)
            observations.append({'segment':name,'max_actual_scenario_tcp_error_m':max_position,'max_actual_scenario_orientation_error_rad':max_angle,'controller_tracking':{k:v for k,v in observation.items() if k!='scenario_feedback'}})
            if exceeds(max_position,c.constraints.position_tolerance_m) or exceeds(max_angle,c.constraints.orientation_tolerance_rad):
                failure=(name,'tcp_tolerance',f'actual perturbed execution residual {max_position}m/{max_angle}rad');break
            completed.append(name)
        complete=tuple(completed)==c.job.segments()
        record.update(outcome='fail' if failure else 'pass' if complete else 'unknown',complete_job_executed=complete)
        if failure:return adapter.unknown(c,failure[2],failure[:2])
        if not complete:return adapter.unknown(c,'perturbed complete-job execution incomplete')
        return Plan(c.digest(),adapter.version,tuple(Check(s,g,Result.PASS,'actual complete perturbed job executed; '+g+' checked on fixed trajectories and observed feedback') for s in c.job.segments() for g in GATES),adapter.plans[c.digest()][0])
    except RoboticsError as e:
        record['reason']=str(e)
        if e.constraint=='tcp_tolerance':
            record['outcome']='fail';return adapter.unknown(c,str(e),(current_name,'tcp_tolerance'))
        return adapter.unknown(c,'perturbed execution could not be confirmed: '+str(e))
    finally:
        cell.active_cancel=None;cell.active_deadline=None
        record.update(completed_segments=completed,segment_observations=observations,elapsed_s=time.monotonic()-start)
        adapter.reports.append(record)
        directory=Path('evidence/phase2/scenarios');directory.mkdir(parents=True,exist_ok=True)
        filename=hashlib.sha256((c.digest()+scenario.id).encode()).hexdigest()+'.json';(directory/filename).write_text(json.dumps(record,indent=2)+'\n')
        # Failed restoration raises: it must not be hidden by a scenario success.
        adapter.scene.synchronize(c,allow_respawn=True);cell.ready();cell.sync_planning(c)
