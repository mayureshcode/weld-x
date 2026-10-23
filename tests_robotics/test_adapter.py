import json,time,threading,unittest
from pathlib import Path
import rclpy
from weldx.model import Configuration
from weldx.validation import Result
from weldx.robustness import NOMINAL,Scenario
from robotics.adapter import RosAdapter

class ActualAdapterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  rclpy.init();cls.a=RosAdapter();cls.c=Configuration.model_validate_json(Path('examples/commissioning_two_seam.json').read_text());cls.cancel=threading.Event();cls.a.cell.ready()
 @classmethod
 def tearDownClass(cls):cls.a.cell.active_cancel=None;cls.a.cell.active_deadline=None;cls.a.close();rclpy.shutdown()
 def test_01_exact_nominal_contract(self):
  self.assertEqual(self.a.synchronize(self.c,self.cancel,time.monotonic()+30),self.c.digest())
  plan=self.a.validate(self.c,NOMINAL,self.cancel,time.monotonic()+60)
  Path('evidence/phase3').mkdir(parents=True,exist_ok=True)
  Path('evidence/phase3/actual-adapter-nominal.json').write_text(json.dumps({'outcome':plan.outcome(self.c,self.a.version).value,'checks':[c.__dict__ for c in plan.checks]},indent=2))
  self.assertEqual(plan.outcome(self.c,self.a.version),Result.PASS)
 def test_02_open_loop_failure_is_confirmed(self):
  scenario=Scenario('integration:base:error','base','boundary',1701,base=(.002,0,0,0))
  plan=self.a.validate(self.c,scenario,self.cancel,time.monotonic()+30)
  self.assertEqual(plan.outcome(self.c,self.a.version),Result.FAIL)
 def test_03_unexecuted_scenario_is_unknown_not_pass(self):
  plan=self.a.validate(self.c,Scenario('integration:zero','combined','mc',1701),self.cancel,time.monotonic()+30)
  self.assertEqual(plan.outcome(self.c,self.a.version),Result.UNKNOWN)
 def test_04_telemetry_comes_from_feedback(self):
  data=self.a.telemetry();self.assertTrue(data['live']);self.assertEqual(len(data['joint_positions']),6)
 def test_05_expired_budget_unknown(self):
  plan=self.a.validate(self.c,NOMINAL,self.cancel,time.monotonic()-1)
  self.assertEqual(plan.outcome(self.c,self.a.version),Result.UNKNOWN)

if __name__=='__main__':unittest.main()
