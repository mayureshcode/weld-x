"""Fail-closed bridge from WELD-X contracts to real Jazzy/Harmonic operations.
Nominal plans are real. Uncertainty failures are necessary-condition checks on the
same open-loop trajectories. Potential successes require complete perturbed Gazebo execution within budget.
Insufficient execution evidence remains UNKNOWN and cannot authorize recovery.
"""
from pathlib import Path
import hashlib,json,math,threading,time
import numpy as np
from scipy.spatial.transform import Rotation
from weldx.validation import Check,Plan,Execution,GATES,Result
from weldx.model import Base
from weldx.engine import serial
from .cell import Cell,RoboticsError,NAMES
from .scene import SceneTransport

class RosAdapter:
    version='jazzy-harmonic:abb-45f4769:cell-v3:open-loop-calibration-model'
    def __init__(self):
        self.cell=Cell();self.scene=SceneTransport();self.plans={};self.reports=[];self.bound=None
        self.dependency_signature=self._fingerprint();self.version=type(self).version+':'+self.dependency_signature[:16]
    def _fingerprint(self):
        files=list(Path(__file__).parent.glob('*.py'))+[Path('/workspace/.runtime/generated/weldx.urdf'),Path('/var/lib/dpkg/status')]
        files += [Path('/workspace/weldx') / n for n in ('model.py','validation.py','robustness.py','engine.py')]
        files+=list(Path('/workspace/ros_ws/install/weldx_bringup/share/weldx_bringup/config').glob('*'))
        files+=list(Path('/workspace/ros_ws/install/weldx_description/share/weldx_description/worlds').glob('*'))
        for link in self.cell.urdf.findall('link'):
            for mesh in link.findall('collision/geometry/mesh'):files.append(Path(mesh.get('filename').removeprefix('file://')))
        digest=hashlib.sha256()
        for file in sorted(set(files)):
            digest.update(str(file).encode());digest.update(file.read_bytes())
        return digest.hexdigest()
    def intact(self):return self._fingerprint()==self.dependency_signature
    @property
    def ready(self):
        return self.intact() and self.cell.context.ok() and time.monotonic()-self.cell.last_feedback<2 and time.monotonic()-self.cell.controller_checked<3 and self.cell.controller_states.get('joint_trajectory_controller')=='active' and time.monotonic()-self.scene.last<2 and all(c.service_is_ready() for c in self.cell.rpc_clients.values())
    def health(self):
        fresh=time.monotonic()-self.cell.last_feedback<2
        return {'dependency_integrity':'unchanged' if self.intact() else 'CHANGED_RESTART_AND_REVALIDATE', 'adapter':'real_ROS2','ros':'connected' if fresh else 'feedback_stale',
            'gazebo':'live_pose_feedback' if time.monotonic()-self.scene.last<2 else 'pose_feedback_stale',
            'moveit':'services_ready' if self.cell.rpc_clients['/compute_ik'].service_is_ready() else 'unavailable',
            'controllers':self.cell.controller_states.get('joint_trajectory_controller','unavailable') if time.monotonic()-self.cell.controller_checked<3 else 'status_stale',
            'robot_model':'ABB_IRB120_provisional_physical_fidelity',
            'execution':'exact nominal and complete robustness gates required',
            'uncertainty':'open-loop screening and complete Gazebo execution when budget permits; model mismatch restricted to TCP calibration'}
    def telemetry(self):
        poses={}
        for name in ['weldx_robot','base_link','fixture','workpiece']:
            p=self.scene.observed.get(name)
            if p:poses[name]={'position':[p.position.x,p.position.y,p.position.z],'orientation':[p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w]}
        return {'entity_poses':poses,'robot_base_pose':poses.get('base_link'),
            'joint_positions':self.cell.values() if self.cell.state else {},
            'feedback_age_s':time.monotonic()-self.cell.last_feedback if self.cell.state else None,
            'live':time.monotonic()-self.cell.last_feedback<2 and time.monotonic()-self.scene.last<2,
            'evidence_scope':'observed Gazebo joint states; candidate previews are not execution',
            'last_runtime_reports':self.reports[-8:]}
    def synchronize(self,c,cancel,deadline):
        self.bound=None;self.cell.active_cancel=None;self.cell.active_deadline=None
        if not self.intact() or cancel.is_set() or time.monotonic()>=deadline:return None
        # Never apply a candidate via set_pose ack alone.
        self.scene.synchronize(c,allow_respawn=True);self.cell.sync_planning(c);self.cell.ready();self.cell.verify_fk()
        if not self.intact() or cancel.is_set() or time.monotonic()>=deadline:return None
        self.bound=c.digest();return self.bound
    def unknown(self,c,reason,failed=None):
        return Plan(c.digest(),self.version,tuple(Check(s,g,Result.FAIL if failed==(s,g) else Result.UNKNOWN,reason) for s in c.job.segments() for g in GATES))
    def validate(self,c,scenario,cancel,deadline):
        if not self.intact():return self.unknown(c,'runtime/model/controller dependencies changed; restart and revalidate')
        if cancel.is_set() or time.monotonic()>=deadline:return self.unknown(c,'cancelled or computation budget exhausted')
        if (c.tcp.x_m,c.tcp.y_m,c.tcp.z_m,c.tcp.roll_rad,c.tcp.pitch_rad,c.tcp.yaw_rad)!=(0,0,.12,0,0,0):
            return self.unknown(c,'this verified model currently supports only the declared 0.12 m axial torch TCP')
        self.cell.active_cancel=cancel;self.cell.active_deadline=deadline
        if scenario.kind!='nominal':return self.uncertainty(c,scenario,cancel,deadline)
        try:
            self.cell.ready();self.cell.verify_fk();segments=self.cell.build_job(c)
            if tuple(s[0] for s in segments)!=c.job.segments():raise RoboticsError('continuity','complete segment order mismatch')
            checks=[]
            for name,trajectory,info in segments:
                # Additional access requirements beyond configured pose/collision are not invented.
                for gate in GATES:
                    reason={'reachability':'full trajectory generated by model-based IK and OMPL',
                        'ik':'all mandatory Cartesian paths completed, collision-aware IK',
                        'joint_limits':'all returned joint states within exact source limits',
                        'collision':'MoveIt FCL checks on returned path states with declared link padding; discrete, not continuous guarantee',
                        'continuity':'ordered complete approach/weld/retreat/transitions; Cartesian fraction 1.0',
                        'tcp_tolerance':'requested Cartesian paths use exact model TCP; observed tracking is separately checked on execution',
                        'access':'configured tool orientation and collision constraints enforced; no additional process-access model declared',
                        'dynamics':'returned velocity and acceleration arrays checked against configured limits',
                        'timing':'strictly increasing trajectory timestamps; weld TCP speed independently retimed and verified',
                        'controller':'live joint feedback and initialized trajectory controller verified'}[gate]
                    checks.append(Check(name,gate,Result.PASS,reason,
                        measurement=info['maximum_planned_tcp_speed_m_s'] if gate=='timing' else None,
                        margin=info['joint_limit_margin_rad'] if gate=='joint_limits' else None))
            identity=hashlib.sha256((c.digest()+json.dumps([{'name':n,**i} for n,t,i in segments],sort_keys=True)+str(time.monotonic_ns())).encode()).hexdigest()
            self.plans[c.digest()]=(identity,segments)
            return Plan(c.digest(),self.version,tuple(checks),identity)
        except RoboticsError as e:
            # Failed call vs confirmed constraint violation must remain distinguishable.
            confirmed=e.constraint in ('joint_limits','collision','ik','continuity','dynamics','timing','tcp_tolerance') and 'timed out' not in str(e) and 'unavailable' not in str(e)
            return self.unknown(c,str(e),(e.segment or self.cell.active_segment or c.job.segments()[0],e.constraint) if confirmed else None)
    def preflight_boundaries(self,c,phase,cancel,deadline):
        from .preflight import boundaries
        return boundaries(self,c,phase,cancel,deadline)
    def uncertainty(self,c,scenario,cancel,deadline):
        cached=self.plans.get(c.digest())
        if not cached:return self.unknown(c,'no exact nominal trajectory available for open-loop uncertainty screening')
        _,segments=cached;m=scenario.model
        from .perturbation import perturb
        perturbed=perturb(c,scenario)
        checks=[];failed=None;maximum=0.
        try:
            self.cell.sync_planning(perturbed)
            for name,trajectory,info in segments:
                if cancel.is_set() or time.monotonic()>=deadline:return self.unknown(c,'scenario budget exhausted')
                # Fixed commands: no perfect-knowledge replanning under perturbation.
                for p in trajectory.points:
                    values=dict(zip(trajectory.joint_names,p.positions));valid,contacts=self.cell.validity(values)
                    if not valid:failed=(name,'collision',str(contacts));break
                    if name.endswith(':weld'):
                        nominal=self.cell.fk(values);actual=nominal.copy()
                        actual[:3,3]+=nominal[:3,:3]@np.array(m[:3]);actual[:3,:3]=actual[:3,:3]@Rotation.from_euler('z',m[3]).as_matrix()
                        seam=next(s for s in c.job.seams if name==s.id+':weld')
                        # Compare each commanded nominal TCP to the same workpiece-relative target under error.
                        # Convert nominal base point into nominal workpiece coordinates.
                        world=Rotation.from_euler('z',c.base.yaw_rad).apply(nominal[:3,3])+[c.base.x_m,c.base.y_m,c.base_height_m]
                        rw=Rotation.from_euler('xyz',[c.workpiece.roll_rad,c.workpiece.pitch_rad,c.workpiece.yaw_rad])
                        local=rw.inv().apply(world-[c.workpiece.x_m,c.workpiece.y_m,c.workpiece.z_m])
                        desired=self.cell.target(perturbed,local,seam.tool_rpy_rad)
                        pos=np.array([desired.position.x,desired.position.y,desired.position.z]);q=desired.orientation
                        error=float(np.linalg.norm(actual[:3,3]-pos));maximum=max(maximum,error)
                        angle=float((Rotation.from_matrix(actual[:3,:3]).inv()*Rotation.from_quat([q.x,q.y,q.z,q.w])).magnitude())
                        if error-c.constraints.position_tolerance_m>1e-12 or angle-c.constraints.orientation_tolerance_rad>1e-12:
                            failed=(name,'tcp_tolerance',f'open-loop necessary-condition failure: TCP {error:.9g} m, orientation {angle:.9g} rad');break
                if failed:break
            if not failed:
                from .uncertain_execution import run
                return run(self,c,perturbed,scenario,segments,cancel,deadline)
            reason=failed[2]
            plan=self.unknown(c,reason,(failed[0],failed[1]))
            self.reports.append({'scenario':serial(scenario),'config_hash':c.digest(),'outcome':'fail' if failed else 'unknown','maximum_screened_tcp_error_m':maximum,'reason':reason,'scope':'open-loop model/FCL necessary-condition screening, not successful simulated job execution'})
            return plan
        finally:
            self.cell.active_cancel=None;self.cell.active_deadline=None
            self.cell.sync_planning(c)
    def execute(self,c,plan,cancel,deadline):
        if self.bound!=c.digest() or self.plans.get(c.digest(),(None,))[0]!=plan.trajectory_id:raise RoboticsError('controller','exact scene/trajectory binding missing or stale')
        if not self.ready:raise RoboticsError('controller','runtime health or dependency binding is stale')
        self.cell.active_cancel=cancel;self.cell.active_deadline=deadline
        self.scene.synchronize(c);self.cell.sync_planning(c);self.cell.ready();completed=[];maximum=0.
        segments=self.plans[c.digest()][1]
        initial=dict(zip(segments[0][1].joint_names,segments[0][1].points[0].positions))
        if max(abs(self.cell.values()[n]-initial[n]) for n in NAMES)>1e-4:
            reset=self.cell.plan_joint(c,self.cell.values(),initial);self.cell.inspect(c,reset);self.cell.execute_segment(c,reset,cancel)
        for name,trajectory,info in segments:
            if cancel.is_set() or time.monotonic()>=deadline:break
            e=self.cell.execute_segment(c,trajectory,cancel);maximum=max(maximum,e['maximum_in_motion_tracking']['joint_error_rad']);completed.append(name)
        return Execution(c.digest(),plan.trajectory_id,tuple(completed),tuple(completed)==c.job.segments(),cancel.is_set(),maximum,'observed Gazebo/controller execution; no physical welding')
    def close(self):self.cell.close()
