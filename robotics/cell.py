"""Actual Jazzy MoveIt planning, FCL scene checks and Gazebo controller execution.

No success-path mock or fallback. Service/action failures raise evidence-bearing errors.
"""
from __future__ import annotations
from collections import deque
from copy import deepcopy
import json,math,threading,time,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.action import ActionClient
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Pose,PoseStamped
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.msg import (CollisionObject,PlanningScene,PlanningSceneComponents,
    AllowedCollisionEntry,LinkPadding,Constraints,JointConstraint,RobotState)
from moveit_msgs.srv import (ApplyPlanningScene,GetPlanningScene,GetStateValidity,
    GetPositionIK,GetPositionFK,GetMotionPlan,GetCartesianPath)
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTolerance
from builtin_interfaces.msg import Duration
from controller_manager_msgs.srv import ListControllers
from weldx.model import Configuration

NAMES=tuple(f'joint_{i}' for i in range(1,7))

class RoboticsError(RuntimeError):
    def __init__(self,constraint,reason,segment=None):
        super().__init__(reason);self.constraint=constraint;self.segment=segment

class Cell(Node):
    def __init__(self):
        super().__init__('weldx_robotics_backend')
        self.active_cancel=None;self.active_deadline=None;self.active_segment=None;self.controller_states={};self.controller_checked=0.;self._controller_future=None
        self.state=None;self.last_feedback=0.;self.trace=deque(maxlen=100000)
        self.create_subscription(JointState,'/joint_states',self._observe,50)
        self.rpc_clients={name:self.create_client(typ,name) for name,typ in [
            ('/apply_planning_scene',ApplyPlanningScene),('/get_planning_scene',GetPlanningScene),
            ('/check_state_validity',GetStateValidity),('/compute_ik',GetPositionIK),
            ('/compute_fk',GetPositionFK),('/plan_kinematic_path',GetMotionPlan),
            ('/compute_cartesian_path',GetCartesianPath),('/controller_manager/list_controllers',ListControllers)]}
        self.controller=ActionClient(self,FollowJointTrajectory,'/joint_trajectory_controller/follow_joint_trajectory')
        self._spin_executor=SingleThreadedExecutor();self._spin_executor.add_node(self)
        self._running=True;self.thread=threading.Thread(target=self._spin,daemon=True);self.thread.start()
        self.health_timer=self.create_timer(1.,self._poll_controllers)
        self.urdf=ET.parse('/workspace/.runtime/generated/weldx.urdf')
        self.joints={j.get('name'):j for j in self.urdf.findall('joint')}
        self.by_child={j.find('child').get('link'):j for j in self.joints.values()}
        self.limits={n:tuple(float(self.joints[n].find('limit').get(k)) for k in ['lower','upper']) for n in NAMES}
    def _poll_controllers(self):
        client=self.rpc_clients['/controller_manager/list_controllers']
        if not client.service_is_ready() or (self._controller_future and not self._controller_future.done()):return
        self._controller_future=client.call_async(ListControllers.Request())
        def observed(future):
            if future.exception() is None:
                self.controller_states={c.name:c.state for c in future.result().controller};self.controller_checked=time.monotonic()
        self._controller_future.add_done_callback(observed)
    def _spin(self):
        while self._running and self.context.ok():self._spin_executor.spin_once(timeout_sec=.1)
    def close(self):
        # Stop the spin producer BEFORE draining its workers or destroying ROS handles.
        self.health_timer.cancel();self._running=False;self.thread.join(timeout=3)
        if self.thread.is_alive():raise RoboticsError('controller','ROS spin thread did not stop cleanly')
        self._spin_executor.shutdown(timeout_sec=5)
        self._spin_executor.remove_node(self);self.destroy_node()
    def _observe(self,msg):
        self.state=msg;self.last_feedback=time.monotonic()
        self.trace.append({'wall_s':self.last_feedback,'sim_s':msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9,'position':dict(zip(msg.name,msg.position))})
    def wait(self,future,timeout=30,cancel=None):
        deadline=min(time.monotonic()+timeout,self.active_deadline or float("inf"));cancel=cancel or self.active_cancel
        while not future.done() and time.monotonic()<deadline:
            if cancel and cancel.is_set():raise RoboticsError('controller','operation cancelled')
            time.sleep(.005)
        if not future.done():raise RoboticsError('controller','ROS operation timed out')
        return future.result()
    def call(self,name,request,timeout=10):
        client=self.rpc_clients[name]
        if self.active_cancel and self.active_cancel.is_set():raise RoboticsError('controller','operation cancelled')
        if self.active_deadline is not None:
            timeout=min(timeout,self.active_deadline-time.monotonic())
            if timeout<=0:raise RoboticsError('controller','computation budget exhausted')
        if not client.wait_for_service(timeout_sec=min(3,timeout)):raise RoboticsError('controller',name+' unavailable')
        return self.wait(client.call_async(request),timeout)
    def ready(self):
        deadline=time.monotonic()+15
        while (self.state is None or not all(c.service_is_ready() for c in self.rpc_clients.values())) and time.monotonic()<deadline:time.sleep(.05)
        if self.state is None or time.monotonic()-self.last_feedback>2:raise RoboticsError('controller','live joint-state feedback unavailable')
        active={c.name:c.state for c in self.call('/controller_manager/list_controllers',ListControllers.Request()).controller}
        self.controller_states=active;self.controller_checked=time.monotonic()
        if active.get('joint_trajectory_controller')!='active':raise RoboticsError('controller','trajectory controller not active')
        return active
    def joint_state(self,values):
        msg=JointState();msg.name=list(NAMES);msg.position=[float(values[n]) for n in NAMES];return msg
    def values(self,state=None):
        state=state or self.state
        if state is None:raise RoboticsError('controller','missing joint feedback')
        return {n:v for n,v in zip(state.name,state.position) if n in NAMES}
    def fk(self,values,link='weld_tcp'):
        chain=[];current=link
        while current in self.by_child:
            j=self.by_child[current];chain.append(j);current=j.find('parent').get('link')
        transform=np.eye(4)
        for j in reversed(chain):
            origin=j.find('origin');xyz=[0.,0.,0.] if origin is None else list(map(float,origin.get('xyz','0 0 0').split()));rpy=[0.,0.,0.] if origin is None else list(map(float,origin.get('rpy','0 0 0').split()))
            fixed=np.eye(4);fixed[:3,:3]=Rotation.from_euler('xyz',rpy).as_matrix();fixed[:3,3]=xyz;transform=transform@fixed
            if j.get('type')=='revolute':
                axis=np.array(list(map(float,j.find('axis').get('xyz').split())));rot=np.eye(4);rot[:3,:3]=Rotation.from_rotvec(axis*values[j.get('name')]).as_matrix();transform=transform@rot
        return transform
    def verify_fk(self):
        req=GetPositionFK.Request();req.header.frame_id='base_link';req.fk_link_names=['weld_tcp'];req.robot_state.joint_state=self.state
        res=self.call('/compute_fk',req)
        if res.error_code.val!=1:raise RoboticsError('tcp_tolerance','MoveIt FK failed')
        actual=res.pose_stamped[0].pose;matrix=self.fk(self.values());p=np.array([actual.position.x,actual.position.y,actual.position.z]);q=[actual.orientation.x,actual.orientation.y,actual.orientation.z,actual.orientation.w]
        position_error=float(np.linalg.norm(matrix[:3,3]-p));orientation_error=float((Rotation.from_matrix(matrix[:3,:3]).inv()*Rotation.from_quat(q)).magnitude())
        if position_error>1e-8 or orientation_error>1e-8:raise RoboticsError('tcp_tolerance','independent FK disagrees with MoveIt')
        return {'position_error_m':position_error,'orientation_error_rad':orientation_error}
    def target(self,c,point,rpy):
        # Workpiece-local -> cell world -> robot-base planning frame.
        rw=Rotation.from_euler('xyz',[c.workpiece.roll_rad,c.workpiece.pitch_rad,c.workpiece.yaw_rad]);rb=Rotation.from_euler('z',c.base.yaw_rad)
        world=rw.apply(point)+np.array([c.workpiece.x_m,c.workpiece.y_m,c.workpiece.z_m])
        position=rb.inv().apply(world-np.array([c.base.x_m,c.base.y_m,c.base_height_m]))
        rotation=rb.inv()*rw*Rotation.from_euler('xyz',rpy)
        pose=Pose();pose.position.x,pose.position.y,pose.position.z=map(float,position)
        pose.orientation.x,pose.orientation.y,pose.orientation.z,pose.orientation.w=map(float,rotation.as_quat());return pose
    def _box(self,name,dimensions,pose):
        obj=CollisionObject();obj.id=name;obj.header.frame_id='base_link';obj.operation=CollisionObject.ADD
        shape=SolidPrimitive();shape.type=SolidPrimitive.BOX;shape.dimensions=list(map(float,dimensions));obj.primitives=[shape];obj.primitive_poses=[pose];return obj
    def sync_planning(self,c):
        scene=PlanningScene();scene.is_diff=True;scene.robot_state.is_diff=True
        for name,dimensions,location in [('fixture',[.22,.30,.20],c.fixture),('workpiece',[.18,.24,.05],c.workpiece)]:
            fake=c.model_copy(update={'workpiece':location});pose=self.target(fake,[0,0,0],[0,0,0]);scene.world.collision_objects.append(self._box(name,dimensions,pose))
        floor=Pose();floor.position.z=-.055-c.base_height_m;floor.orientation.w=1.
        scene.world.collision_objects.append(self._box('floor',[4,4,.1],floor))
        req=GetPlanningScene.Request();req.components.components=PlanningSceneComponents.ALLOWED_COLLISION_MATRIX
        acm=self.call('/get_planning_scene',req).scene.allowed_collision_matrix
        for name in ['floor','base_link']:
            if name not in acm.entry_names:
                acm.entry_names.append(name)
                for row in acm.entry_values:row.enabled.append(False)
                acm.entry_values.append(AllowedCollisionEntry(enabled=[False]*len(acm.entry_names)))
        i=acm.entry_names.index('floor');j=acm.entry_names.index('base_link');acm.entry_values[i].enabled[j]=True;acm.entry_values[j].enabled[i]=True
        scene.allowed_collision_matrix=acm
        scene.link_padding=[LinkPadding(link_name=link.get('name'),padding=c.constraints.minimum_clearance_m) for link in self.urdf.findall('link') if link.find('collision') is not None]
        request=ApplyPlanningScene.Request();request.scene=scene
        if not self.call('/apply_planning_scene',request).success:raise RoboticsError('collision','planning scene application rejected')
    def validity(self,values):
        req=GetStateValidity.Request();req.group_name='manipulator';req.robot_state.joint_state=self.joint_state(values)
        response=self.call('/check_state_validity',req)
        return response.valid,[(c.contact_body_1,c.contact_body_2) for c in response.contacts]
    def ik(self,c,pose,start):
        req=GetPositionIK.Request();i=req.ik_request;i.group_name='manipulator';i.ik_link_name='weld_tcp';i.robot_state.joint_state=self.joint_state(start);i.pose_stamped=PoseStamped();i.pose_stamped.header.frame_id='base_link';i.pose_stamped.pose=pose;i.avoid_collisions=True;i.timeout.sec=1
        result=self.call('/compute_ik',req)
        if result.error_code.val!=1:raise RoboticsError('ik',f'collision-aware IK error {result.error_code.val}; target {pose.position}')
        return self.values(result.solution.joint_state)
    def plan_joint(self,c,start,target):
        req=GetMotionPlan.Request();m=req.motion_plan_request;m.group_name='manipulator';m.allowed_planning_time=c.constraints.planning_timeout_s;m.num_planning_attempts=2;m.max_velocity_scaling_factor=.2;m.max_acceleration_scaling_factor=.2;m.start_state.joint_state=self.joint_state(start)
        m.goal_constraints=[Constraints(name='weldx_target',joint_constraints=[JointConstraint(joint_name=n,position=target[n],tolerance_above=.00001,tolerance_below=.00001,weight=1.) for n in NAMES])]
        res=self.call('/plan_kinematic_path',req,timeout=c.constraints.planning_timeout_s+5).motion_plan_response
        if res.error_code.val!=1:raise RoboticsError('collision',f'MoveIt complete motion plan rejected: {res.error_code.val}')
        return res.trajectory.joint_trajectory
    def cartesian(self,c,start,poses,speed):
        req=GetCartesianPath.Request();req.header.frame_id='base_link';req.start_state.joint_state=self.joint_state(start);req.group_name='manipulator';req.link_name='weld_tcp';req.waypoints=poses;req.max_step=.005;req.avoid_collisions=True;req.revolute_jump_threshold=.3;req.max_velocity_scaling_factor=.2;req.max_acceleration_scaling_factor=.2;req.cartesian_speed_limited_link='weld_tcp';req.max_cartesian_speed=speed
        res=self.call('/compute_cartesian_path',req,timeout=20)
        if res.error_code.val!=1 or res.fraction<1.-1e-8:raise RoboticsError('continuity',f'collision-aware Cartesian fraction {res.fraction}, error {res.error_code.val}')
        trajectory=self.limit_tcp_speed(res.solution.joint_trajectory,speed)
        self.inspect_cartesian(c,start,trajectory,poses)
        return trajectory
    def inspect_cartesian(self,c,start,trajectory,poses):
        initial=self.fk(start);vertices=[initial[:3,3]]+[np.array([p.position.x,p.position.y,p.position.z]) for p in poses]
        last=poses[-1].orientation;target_rotation=Rotation.from_quat([last.x,last.y,last.z,last.w])
        maximum=0.
        for p in trajectory.points:
            actual=self.fk(dict(zip(trajectory.joint_names,p.positions)));distances=[]
            for a,b in zip(vertices,vertices[1:]):
                delta=b-a;t=float(np.clip(np.dot(actual[:3,3]-a,delta)/max(np.dot(delta,delta),1e-20),0,1))
                distances.append(float(np.linalg.norm(actual[:3,3]-(a+t*delta))))
            maximum=max(maximum,min(distances))
            angle=float((Rotation.from_matrix(actual[:3,:3]).inv()*target_rotation).magnitude())
            if maximum>c.constraints.position_tolerance_m or angle>c.constraints.orientation_tolerance_rad:
                raise RoboticsError('tcp_tolerance',f'planned Cartesian path/orientation residual {maximum}m/{angle}rad')
        end=self.fk(dict(zip(trajectory.joint_names,trajectory.points[-1].positions)))
        if np.linalg.norm(end[:3,3]-vertices[-1])>c.constraints.position_tolerance_m:raise RoboticsError('tcp_tolerance','Cartesian endpoint misses exact requested target')
    def tcp_speed(self,trajectory):
        maximum=0.;last=None
        for p in trajectory.points:
            values=dict(zip(trajectory.joint_names,p.positions));xyz=self.fk(values)[:3,3]
            t=p.time_from_start.sec+p.time_from_start.nanosec*1e-9
            if last is not None and t>last[0]:maximum=max(maximum,float(np.linalg.norm(xyz-last[1])/(t-last[0])))
            if p.velocities:
                # Directional derivative of the actual model TCP, not flange velocity.
                eps=1e-5;after={n:values[n]+eps*v for n,v in zip(trajectory.joint_names,p.velocities)}
                maximum=max(maximum,float(np.linalg.norm(self.fk(after)[:3,3]-xyz)/eps))
            last=(t,xyz)
        return maximum
    def limit_tcp_speed(self,trajectory,speed):
        # Jazzy GetCartesianPath returned timing ignored max_cartesian_speed in our test.
        # Conservative uniform retiming preserves positions, reduces velocity/acceleration.
        result=deepcopy(trajectory);factor=max(1.,self.tcp_speed(result)/speed*1.05)
        for p in result.points:
            ns=round((p.time_from_start.sec+p.time_from_start.nanosec*1e-9)*factor*1e9)
            p.time_from_start=Duration(sec=ns//1000000000,nanosec=ns%1000000000)
            p.velocities=[v/factor for v in p.velocities];p.accelerations=[v/(factor*factor) for v in p.accelerations]
        if self.tcp_speed(result)>speed+1e-8:raise RoboticsError('timing','TCP speed retiming failed')
        return result
    def inspect(self,c,trajectory):
        if not trajectory.points:raise RoboticsError('continuity','empty trajectory')
        names=trajectory.joint_names;minimum=float('inf');previous=None;previous_t=None
        for p in trajectory.points:
            values=dict(zip(names,p.positions));minimum=min(minimum,*(min(values[n]-self.limits[n][0],self.limits[n][1]-values[n]) for n in NAMES))
            if minimum<0:raise RoboticsError('joint_limits','joint position outside model limits')
            t=p.time_from_start.sec+p.time_from_start.nanosec*1e-9
            if previous_t is not None and t<=previous_t:raise RoboticsError('timing','non-increasing trajectory timestamps')
            if p.velocities and max(map(abs,p.velocities))>c.constraints.max_joint_velocity_rad_s+1e-6:raise RoboticsError('dynamics','planned joint velocity exceeds declaration')
            if p.accelerations and max(map(abs,p.accelerations))>c.constraints.max_joint_acceleration_rad_s2+1e-6:raise RoboticsError('dynamics','planned joint acceleration exceeds declaration')
            valid,contacts=self.validity(values)
            if not valid:raise RoboticsError('collision','FCL rejects trajectory state: '+str(contacts))
            previous=values;previous_t=t
        return {'points':len(trajectory.points),'joint_limit_margin_rad':minimum,'collision_padding_m':c.constraints.minimum_clearance_m,'duration_s':previous_t,'maximum_planned_tcp_speed_m_s':self.tcp_speed(trajectory)}
    def build_job(self,c):
        self.sync_planning(c);current=self.values();valid,contacts=self.validity(current)
        if not valid:raise RoboticsError('collision','initial state in collision: '+str(contacts))
        segments=[]
        for i,seam in enumerate(c.job.seams):
            self.active_segment=f'{c.job.seams[i-1].id}->{seam.id}:transition' if i else seam.id+':approach'
            rpy=seam.tool_rpy_rad
            approach=list(seam.points_m[0]);approach[2]+=seam.approach_m
            pre=self.target(c,approach,rpy)
            target=self.ik(c,pre,current)
            move=self.plan_joint(c,current,target);info=self.inspect(c,move)
            name=f'{c.job.seams[i-1].id}->{seam.id}:transition' if i else seam.id+':approach'
            if i:segments.append((name,move,info))
            current=dict(zip(move.joint_names,move.points[-1].positions))
            self.active_segment=seam.id+':approach'
            enter=self.cartesian(c,current,[self.target(c,seam.points_m[0],rpy)],seam.weld_speed_m_s*2);info=self.inspect(c,enter)
            # Merge the first free-space approach and ingress into one mandatory segment.
            if not i:
                enter=join_trajectories(move,enter);info=self.inspect(c,enter)
            segments.append((seam.id+':approach',enter,info));current=dict(zip(enter.joint_names,enter.points[-1].positions))
            self.active_segment=seam.id+':weld'
            weld=self.cartesian(c,current,[self.target(c,p,rpy) for p in seam.points_m[1:]],seam.weld_speed_m_s);info=self.inspect(c,weld)
            segments.append((seam.id+':weld',weld,info));current=dict(zip(weld.joint_names,weld.points[-1].positions))
            retreat=list(seam.points_m[-1]);retreat[2]+=seam.retreat_m
            self.active_segment=seam.id+':retreat'
            leave=self.cartesian(c,current,[self.target(c,retreat,rpy)],seam.weld_speed_m_s*2);info=self.inspect(c,leave)
            segments.append((seam.id+':retreat',leave,info));current=dict(zip(leave.joint_names,leave.points[-1].positions))
        return segments
    def execute_segment(self,c,trajectory,cancel=None,scenario_observer=None):
        expected_start=dict(zip(trajectory.joint_names,trajectory.points[0].positions))
        if max(abs(expected_start[n]-self.values()[n]) for n in NAMES)>c.constraints.max_tracking_error_rad:raise RoboticsError('continuity','observed start state does not match validated trajectory')
        if not self.controller.wait_for_server(timeout_sec=5):raise RoboticsError('controller','trajectory action unavailable')
        goal=FollowJointTrajectory.Goal();goal.trajectory=trajectory
        goal.goal_tolerance=[JointTolerance(name=n,position=.0001,velocity=.02) for n in NAMES]
        goal.goal_time_tolerance=Duration(sec=3)
        feedback=[];scenario_feedback=[]
        def observe(message):
            f=message.feedback
            if len(f.desired.positions)!=6 or len(f.actual.positions)!=6:return
            expected=dict(zip(f.joint_names,f.desired.positions));actual=dict(zip(f.joint_names,f.actual.positions))
            a=self.fk(expected);b=self.fk(actual)
            if scenario_observer:scenario_feedback.append(scenario_observer(expected,actual))
            feedback.append({'joint_error_rad':max(abs(expected[n]-actual[n]) for n in NAMES),
                'tcp_error_m':float(np.linalg.norm(a[:3,3]-b[:3,3])),
                'orientation_error_rad':float((Rotation.from_matrix(a[:3,:3]).inv()*Rotation.from_matrix(b[:3,:3])).magnitude())})
        handle=self.wait(self.controller.send_goal_async(goal,feedback_callback=observe),10)
        if not handle.accepted:raise RoboticsError('controller','trajectory goal rejected')
        result=handle.get_result_async();deadline=min(time.monotonic()+c.constraints.execution_timeout_s,self.active_deadline or float("inf"))
        while not result.done() and time.monotonic()<deadline:
            if cancel and cancel.is_set():
                self.wait(handle.cancel_goal_async(),5);raise RoboticsError('controller','software cancellation acknowledged/requested')
            time.sleep(.005)
        if not result.done():self.wait(handle.cancel_goal_async(),5);raise RoboticsError('timing','execution timed out; cancel requested')
        status=result.result()
        if status.status!=4 or status.result.error_code!=0:raise RoboticsError('controller',f'controller execution failed: {status.status}/{status.result.error_code}: {status.result.error_string}')
        time.sleep(.05)
        expected=dict(zip(trajectory.joint_names,trajectory.points[-1].positions));observed=self.values()
        error=max(abs(expected[n]-observed[n]) for n in NAMES)
        tcp_expected=self.fk(expected);tcp_observed=self.fk(observed)
        position_error=float(np.linalg.norm(tcp_expected[:3,3]-tcp_observed[:3,3]))
        orientation_error=float((Rotation.from_matrix(tcp_expected[:3,:3]).inv()*Rotation.from_matrix(tcp_observed[:3,:3])).magnitude())
        if error>c.constraints.max_tracking_error_rad or position_error>c.constraints.position_tolerance_m or orientation_error>c.constraints.orientation_tolerance_rad:raise RoboticsError('tcp_tolerance',f'observed joint/TCP endpoint tracking outside tolerance: {error}, {position_error}, {orientation_error}')
        if not feedback:raise RoboticsError('controller','no trajectory action tracking feedback')
        tracking={k:max(f[k] for f in feedback) for k in feedback[0]}
        if tracking['joint_error_rad']>c.constraints.max_tracking_error_rad or tracking['tcp_error_m']>c.constraints.position_tolerance_m or tracking['orientation_error_rad']>c.constraints.orientation_tolerance_rad:
            raise RoboticsError('tcp_tolerance','observed in-motion tracking outside tolerance: '+str(tracking))
        return {'scenario_feedback':scenario_feedback,'feedback_samples':len(feedback),'maximum_in_motion_tracking':tracking,'joint_error_rad':error,'tcp_position_error_m':position_error,'tcp_orientation_error_rad':orientation_error,'observed':observed,'controller_status':status.status}


def join_trajectories(first,second):
    if first.joint_names!=second.joint_names:raise RoboticsError('continuity','joint order changed between subsegments')
    if max(abs(a-b) for a,b in zip(first.points[-1].positions,second.points[0].positions))>1e-5:raise RoboticsError('continuity','discontinuous approach subsegments')
    joined=deepcopy(first)
    offset=first.points[-1].time_from_start.sec+first.points[-1].time_from_start.nanosec*1e-9
    initial=second.points[0].time_from_start.sec+second.points[0].time_from_start.nanosec*1e-9
    for original in second.points[1:]:
        point=deepcopy(original);seconds=offset+original.time_from_start.sec+original.time_from_start.nanosec*1e-9-initial
        nanoseconds=round(seconds*1e9);point.time_from_start=Duration(sec=nanoseconds//1000000000,nanosec=nanoseconds%1000000000);joined.points.append(point)
    return joined
