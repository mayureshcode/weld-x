import math,unittest
from pathlib import Path
from weldx.model import Configuration
from weldx.robustness import Scenario
from robotics.perturbation import perturb
from robotics.uncertain_execution import error,exceeds
from robotics.cell import Cell
import rclpy

class FrameTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  rclpy.init();cls.cell=Cell();cls.cell.ready();cls.c=Configuration.model_validate_json(Path('examples/commissioning_two_seam.json').read_text())
 @classmethod
 def tearDownClass(cls):cls.cell.close();rclpy.shutdown()
 def check_error(self,s,expected):
  q=self.cell.values();self.assertAlmostEqual(error(self.cell,self.c,perturb(self.c,s),s.model,q,q)['tcp_error_m'],expected,places=9)
 def test_numerical_boundary_guard(self):
  self.assertFalse(exceeds(.0010000000000001,.001));self.assertTrue(exceeds(.001000001,.001))
 def test_base_world_translation(self):self.check_error(Scenario('test','base','boundary',0,base=(.0005,0,0,0)),.0005)
 def test_fixture_world_translation(self):self.check_error(Scenario('test','fixture','boundary',0,fixture=(0,0,.0005,0)),.0005)
 def test_equal_world_errors_cancel_relative_translation(self):self.check_error(Scenario('test','combined','boundary',0,base=(.0005,0,0,0),fixture=(.0005,0,0,0)),0)
 def test_opposed_independent_errors_do_not_cancel(self):self.check_error(Scenario('test','combined','boundary',0,base=(.0005,.0005,0,0),fixture=(-.0005,-.0005,.0005,0)),.0015)
 def test_calibration_offset_is_tcp_local(self):self.check_error(Scenario('test','model','boundary',0,model=(.0003,.0004,0,0)),.0005)
 def test_fixture_rotation_moves_attached_workpiece_about_fixture(self):
  c=self.c.model_copy(update={'workpiece':self.c.workpiece.model_copy(update={'x_m':.5})})
  p=perturb(c,Scenario('test','fixture','boundary',0,fixture=(0,0,0,math.pi/2)))
  self.assertAlmostEqual(p.workpiece.x_m,.4);self.assertAlmostEqual(p.workpiece.y_m,.1)

if __name__=='__main__':unittest.main()
