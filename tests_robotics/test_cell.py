import json,unittest
from pathlib import Path
from copy import deepcopy
import rclpy
from geometry_msgs.msg import Pose
from weldx.model import Configuration
from robotics.cell import Cell,RoboticsError
from robotics.scene import SceneTransport

class ActualCellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init();cls.cell=Cell();cls.cell.ready();cls.config=Configuration.model_validate_json(Path('examples/commissioning_two_seam.json').read_text())
    @classmethod
    def tearDownClass(cls):cls.cell.sync_planning(cls.config);cls.cell.close();rclpy.shutdown()
    def setUp(self):self.cell.sync_planning(self.config)
    def test_joint_feedback_and_controllers(self):
        self.assertEqual(self.cell.ready()['joint_trajectory_controller'],'active');self.assertEqual(len(self.cell.values()),6)
    def test_independent_model_fk(self):
        result=self.cell.verify_fk();self.assertLess(result['position_error_m'],1e-8)
    def test_deliberate_collision_detected(self):
        # Fixture deliberately placed over the current TCP; useful FCL failure evidence.
        xyz=self.cell.fk(self.cell.values())[:3,3]
        pose=self.config.fixture.model_copy(update=dict(zip(['x_m','y_m','z_m'],map(float,xyz))))
        collision_config=self.config.model_copy(update={'fixture':pose})
        self.cell.sync_planning(collision_config)
        valid,contacts=self.cell.validity(self.cell.values())
        self.assertFalse(valid);self.assertTrue(contacts)
        Path('evidence/phase2/deliberate-collision.json').write_text(json.dumps({'valid':valid,'contacts':contacts},indent=2))
    def test_unreachable_target_rejected(self):
        p=Pose();p.position.x=5.;p.position.z=5.;p.orientation.w=1.
        with self.assertRaises(RoboticsError) as e:self.cell.ik(self.config,p,self.cell.values())
        self.assertEqual(e.exception.constraint,'ik')
    def test_tcp_timing_enforced(self):
        c=self.config;seam=c.job.seams[0]
        # Reuse actual collision-aware Cartesian service near the current reachable pose.
        current=self.cell.values();m=self.cell.fk(current);p=Pose();p.position.x,p.position.y,p.position.z=map(float,m[:3,3]);p.position.z+=.005
        from scipy.spatial.transform import Rotation
        p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w=map(float,Rotation.from_matrix(m[:3,:3]).as_quat())
        trajectory=self.cell.cartesian(c,current,[p],.005)
        self.assertLessEqual(self.cell.tcp_speed(trajectory),.00500001)
    def test_scene_readback_matches_nominal(self):
        c=self.config;expected={'weldx_robot':([c.base.x_m,c.base.y_m,c.base_height_m],[0,0,c.base.yaw_rad])}
        for name,p in [('fixture',c.fixture),('workpiece',c.workpiece)]:expected[name]=([p.x_m,p.y_m,p.z_m],[p.roll_rad,p.pitch_rad,p.yaw_rad])
        self.assertEqual(len(SceneTransport().verify(expected)),3)

if __name__=='__main__':unittest.main()
