"""Actual ROS/Gazebo integration smoke: feedback -> MoveIt plan -> controller -> feedback."""
import json
from pathlib import Path
import threading,time
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.action import ActionClient
from sensor_msgs.msg import JointState
from controller_manager_msgs.srv import ListControllers
from moveit_msgs.srv import GetMotionPlan,GetPositionFK
from moveit_msgs.msg import Constraints,JointConstraint
from control_msgs.action import FollowJointTrajectory

class Probe(Node):
    def __init__(self):
        super().__init__('weldx_integration_probe')
        self.state=None;self.trace=[]
        self.create_subscription(JointState,'/joint_states',self.observe,20)
    def observe(self,msg):
        self.state=msg
        self.trace.append({'stamp_s':msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9,'names':list(msg.name),'position':list(msg.position),'wall_s':time.monotonic()})
    def wait(self,future,timeout=30):
        deadline=time.monotonic()+timeout
        while not future.done() and time.monotonic()<deadline:time.sleep(.01)
        if not future.done():raise TimeoutError('ROS operation timed out')
        return future.result()
    def client(self,typ,name):
        c=self.create_client(typ,name)
        if not c.wait_for_service(timeout_sec=20):raise TimeoutError(name)
        return c

def main():
    rclpy.init();node=Probe();executor=MultiThreadedExecutor(num_threads=2);executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    try:
        deadline=time.monotonic()+20
        while node.state is None and time.monotonic()<deadline:time.sleep(.05)
        assert node.state is not None,'no actual joint feedback'
        before=node.state
        controllers=node.wait(node.client(ListControllers,'/controller_manager/list_controllers').call_async(ListControllers.Request()))
        active={c.name:c.state for c in controllers.controller}
        assert active.get('joint_trajectory_controller')=='active',active
        req=GetMotionPlan.Request();m=req.motion_plan_request;m.group_name='manipulator';m.allowed_planning_time=5.;m.num_planning_attempts=2;m.max_velocity_scaling_factor=.2;m.max_acceleration_scaling_factor=.2
        m.start_state.joint_state=before;m.start_state.is_diff=False
        target=[.2,-.15,.15,.1,-.1,.1];names=[f'joint_{i}' for i in range(1,7)]
        constraints=Constraints(name='real_motion_smoke')
        constraints.joint_constraints=[JointConstraint(joint_name=n,position=v,tolerance_above=.0001,tolerance_below=.0001,weight=1.) for n,v in zip(names,target)]
        m.goal_constraints=[constraints]
        response=node.wait(node.client(GetMotionPlan,'/plan_kinematic_path').call_async(req)).motion_plan_response
        assert response.error_code.val==1,f'MoveIt planning error {response.error_code.val}'
        trajectory=response.trajectory.joint_trajectory
        assert len(trajectory.points)>1,'no planned trajectory'
        action=ActionClient(node,FollowJointTrajectory,'/joint_trajectory_controller/follow_joint_trajectory')
        assert action.wait_for_server(timeout_sec=10),'controller action unavailable'
        goal=FollowJointTrajectory.Goal();goal.trajectory=trajectory
        accepted=node.wait(action.send_goal_async(goal));assert accepted.accepted,'controller rejected trajectory'
        result=node.wait(accepted.get_result_async(),60)
        assert result.result.error_code==0,result.result.error_string
        time.sleep(.2);after=node.state
        observed=dict(zip(after.name,after.position));initial=dict(zip(before.name,before.position))
        final=dict(zip(trajectory.joint_names,trajectory.points[-1].positions))
        error=max(abs(observed[n]-final[n]) for n in names)
        movement=max(abs(observed[n]-initial[n]) for n in names)
        assert error<.02,(error,observed,final)
        assert movement>.05,('no observed articulated motion',movement)
        fk=GetPositionFK.Request();fk.header.frame_id='base_link';fk.fk_link_names=['weld_tcp'];fk.robot_state.joint_state=after
        tcp=node.wait(node.client(GetPositionFK,'/compute_fk').call_async(fk));assert tcp.error_code.val==1
        report={'scope':'actual Gazebo + gz_ros2_control + MoveIt; not a test double','result':'passed','controllers':active,'joint_feedback_samples':len(node.trace),'planned_points':len(trajectory.points),'controller_status':result.status,'controller_error_code':result.result.error_code,'observed_max_joint_movement_rad':movement,'endpoint_max_joint_tracking_error_rad':error,'initial':initial,'observed_final':observed,'planned_final':final,'observed_tcp_position_m':[tcp.pose_stamped[0].pose.position.x,tcp.pose_stamped[0].pose.position.y,tcp.pose_stamped[0].pose.position.z],'limitations':['planning scene environment not yet synchronized in this smoke test','does not establish complete welding job execution or robustness']}
        Path('evidence/phase2/actual-motion-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
        Path('evidence/phase2/actual-motion-trace.json').write_text(json.dumps(node.trace)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        executor.shutdown();node.destroy_node();rclpy.shutdown();thread.join(timeout=3)

if __name__=='__main__':main()
