"""Actual complete-job fixture, not acceptance of a robustness benchmark."""
import json,time,threading,unittest
from pathlib import Path
import rclpy
from weldx.model import Configuration
from weldx.robustness import NOMINAL,Scenario
from weldx.validation import Result
from weldx.engine import serial
from robotics.adapter import RosAdapter
from robotics.model_view import scene_evidence

class ObservedScenarioTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  rclpy.init();cls.a=RosAdapter();cls.c=Configuration.model_validate_json(Path('examples/commissioning_two_seam.json').read_text());cls.cancel=threading.Event()
 @classmethod
 def tearDownClass(cls):cls.a.cell.active_cancel=None;cls.a.cell.active_deadline=None;cls.a.close();rclpy.shutdown()
 def test_observed_complete_small_fixture_error_receipt(self):
  a=self.a;c=self.c;a.synchronize(c,self.cancel,time.monotonic()+60)
  nominal=a.validate(c,NOMINAL,self.cancel,time.monotonic()+90)
  self.assertEqual(nominal.outcome(c,a.version),Result.PASS)
  s=Scenario('integration:small-fixture-error','fixture','mc',1701,fixture=(.0001,0,0,0))
  p=a.validate(c,s,self.cancel,time.monotonic()+240)
  Path('evidence/phase3/actual-complete-scenario.json').write_text(json.dumps({'nominal':serial(nominal),'scenario':serial(s),'result':serial(p),'outcome':p.outcome(c,a.version).value},indent=2)+'\n')
  self.assertEqual(p.outcome(c,a.version),Result.PASS);self.assertTrue(p.execution_evidence.confirms(c,s,p))
  self.assertTrue(a.binding_valid(c));self.assertEqual(p.execution_evidence.completed_segments,c.job.segments())
  self.assertEqual(len(p.execution_evidence.feedback_samples_per_segment),7)
  # Exercise the read-only exact trajectory contract on actual cached MoveIt data.
  from weldx.engine import Evaluation
  from weldx.robustness import aggregate,Trial
  evaluation=Evaluation(c.digest(),a.version,'search',nominal,aggregate(c,'search',[]),0.)
  view=scene_evidence(a,c,evaluation)
  self.assertEqual(len(view['segments']),7);self.assertTrue(all(s['world_tcp_points_m'] for s in view['segments']))
 def test_live_pose_drift_invalidates_exact_binding(self):
  a=self.a;c=self.c;a.synchronize(c,self.cancel,time.monotonic()+60)
  a.scene.set('fixture',[c.fixture.x_m+.003,c.fixture.y_m,c.fixture.z_m],[0,0,0]);time.sleep(.5)
  try:self.assertFalse(a.binding_valid(c))
  finally:a.synchronize(c,self.cancel,time.monotonic()+60)
