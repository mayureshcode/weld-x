"""Real self-collision and cancel/hold integration tests, virtual cell only."""
import json,time,threading,rclpy,random
from pathlib import Path
from copy import deepcopy
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from robotics.cell import Cell,NAMES
from weldx.model import Configuration

def main():
 rclpy.init();cell=Cell();c=Configuration.model_validate_json(Path('examples/commissioning_two_seam.json').read_text());report={'scope':'isolated real simulator diagnostics, not robustness/approval-authorized commissioning execution','result':'failed'}
 try:
  cell.ready();cell.sync_planning(c);rng=random.Random(20261023);hit=None
  for index in range(200):
   q={n:rng.uniform(*cell.limits[n]) for n in NAMES};valid,contacts=cell.validity(q)
   self_contacts=[pair for pair in contacts if all(body not in ['fixture','floor','workpiece'] for body in pair)]
   if self_contacts:hit={'sample_index':index,'seed':20261023,'joint_positions':q,'contacts':self_contacts};break
  assert hit is not None,'No self-collision fixture found; self-collision detection remains unverified'
  report['self_collision']=hit
  start=cell.values();target=dict(start);target['joint_1']+=.08
  trajectory=cell.plan_joint(c,start,target);report['cancel_path']=cell.inspect(c,trajectory)
  slow=deepcopy(trajectory)
  for p in slow.points:
   ns=round((p.time_from_start.sec+p.time_from_start.nanosec*1e-9)*5e9);p.time_from_start=Duration(sec=ns//1000000000,nanosec=ns%1000000000);p.velocities=[v/5 for v in p.velocities];p.accelerations=[a/25 for a in p.accelerations]
  goal=FollowJointTrajectory.Goal();goal.trajectory=slow
  handle=cell.wait(cell.controller.send_goal_async(goal),10);assert handle.accepted
  time.sleep(.3);during=cell.values();cancel=cell.wait(handle.cancel_goal_async(),5);result=cell.wait(handle.get_result_async(),10)
  assert cancel.goals_canceling,'Controller did not acknowledge cancellation';assert result.status==5,f'Expected canceled action, got {result.status}'
  time.sleep(.3);first=cell.values();time.sleep(.3);second=cell.values();drift=max(abs(first[n]-second[n]) for n in NAMES)
  assert max(abs(during[n]-start[n]) for n in NAMES)>1e-5,'Cancel test did not observe movement'
  assert drift<.001,f'Canceled controller did not settle: {drift}'
  report['cancellation']={'action_status':result.status,'cancel_acknowledged':True,'observed_movement_rad':max(abs(during[n]-start[n]) for n in NAMES),'post_cancel_drift_rad':drift,'hold_observation_wall_s':.3,'scope':'software-level simulated hold; not a certified emergency stop'}
  report['result']='passed';print(json.dumps(report,indent=2),flush=True)
 finally:Path('evidence/phase2/actual-collision-cancel-tests.json').write_text(json.dumps(report,indent=2)+'\n');cell.close();rclpy.shutdown()

if __name__=='__main__':main()
