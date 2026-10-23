"""Explicit uncertainty frames, shared by screening and actual experiments.
Translations: world axes. Base yaw: world Z. Fixture error: rigid assembly error
about the nominal fixture origin. Calibration mismatch: nominal TCP local axes.
"""
from scipy.spatial.transform import Rotation
import numpy as np

def perturb(c,scenario):
 b,f=scenario.base,scenario.fixture
 base=c.base.model_copy(update={'x_m':c.base.x_m+b[0],'y_m':c.base.y_m+b[1],'yaw_rad':c.base.yaw_rad+b[3]})
 fixture=c.fixture.model_copy(update={'x_m':c.fixture.x_m+f[0],'y_m':c.fixture.y_m+f[1],'z_m':c.fixture.z_m+f[2],'yaw_rad':c.fixture.yaw_rad+f[3]})
 origin=np.array([c.fixture.x_m,c.fixture.y_m,c.fixture.z_m]);rw=Rotation.from_euler('xyz',[c.workpiece.roll_rad,c.workpiece.pitch_rad,c.workpiece.yaw_rad])
 delta=Rotation.from_euler('z',f[3]);xyz=origin+np.array(f[:3])+delta.apply(np.array([c.workpiece.x_m,c.workpiece.y_m,c.workpiece.z_m])-origin)
 rotation=delta*rw;rpy=rotation.as_euler('xyz')
 workpiece=c.workpiece.model_copy(update={**dict(zip(['x_m','y_m','z_m'],map(float,xyz))),**dict(zip(['roll_rad','pitch_rad','yaw_rad'],map(float,rpy)))})
 return c.model_copy(update={'base':base,'fixture':fixture,'workpiece':workpiece})
