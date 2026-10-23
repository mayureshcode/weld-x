"""Explicit, bounded Gazebo transport operations. No dashboard shell endpoint."""
import subprocess,time,threading
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
from gz.transport13 import Node
from gz.msgs10.pose_v_pb2 import Pose_V
import numpy as np
from scipy.spatial.transform import Rotation
from google.protobuf import text_format
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.scene_pb2 import Scene
from gz.msgs10.boolean_pb2 import Boolean
from .cell import RoboticsError

class SceneTransport:
    def __init__(self):
        self.node=Node();self.lock=threading.Lock();self.observed={};self.last=0.
        self.node.subscribe(Pose_V,'/world/weldx_cell/pose/info',self._observe)
    def _observe(self,message):
        with self.lock:
            for p in message.pose:self.observed[p.name]=deepcopy(p)
            self.last=time.monotonic()
    def service(self,name,request,response,request_type,response_type):
        # Native request_raw blocks while holding the GIL in transport13; using it
        # beside a Python pose subscriber caused real timeouts despite server action.
        # Separate process isolates that binding issue. A bounded ack is still not readback.
        r=subprocess.run(['gz','service','-s',name,'--reqtype',request_type,'--reptype',response_type,
            '--timeout','5000','--req',text_format.MessageToString(request)],capture_output=True,text=True,timeout=7)
        if r.returncode or not r.stdout.strip():raise RoboticsError('controller','Gazebo service unavailable: '+name+' '+r.stderr)
        return text_format.Parse(r.stdout,response)
    def poses(self):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            with self.lock:
                if self.observed and time.monotonic()-self.last<.5:return deepcopy(self.observed)
            time.sleep(.02)
        raise RoboticsError('controller','Gazebo live pose feedback unavailable')
    def set(self,name,xyz,rpy):
        p=Pose();p.name=name;p.position.x,p.position.y,p.position.z=map(float,xyz)
        q=Rotation.from_euler('xyz',rpy).as_quat();p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w=map(float,q)
        reply=self.service('/world/weldx_cell/set_pose',p,Boolean(),'gz.msgs.Pose','gz.msgs.Boolean')
        if not reply.data:raise RoboticsError('controller','Gazebo rejected pose for '+name)
    def verify(self,expected):
        poses=self.poses();out={}
        for name,(xyz,rpy) in expected.items():
            if name not in poses:raise RoboticsError('controller','Gazebo entity absent: '+name)
            p=poses[name];actual=np.array([p.position.x,p.position.y,p.position.z]);q=p.orientation
            e=float(np.linalg.norm(actual-xyz));angle=float((Rotation.from_euler('xyz',rpy).inv()*Rotation.from_quat([q.x,q.y,q.z,q.w])).magnitude())
            if e>1e-5 or angle>1e-5:raise RoboticsError('controller',f'Gazebo pose readback mismatch {name}: {e}m/{angle}rad')
            out[name]={'position_error_m':e,'orientation_error_rad':angle}
        return out
    def synchronize(self,c,allow_respawn=False):
        expected={'weldx_robot':([0,0,0],[0,0,0]),'base_link':([c.base.x_m,c.base.y_m,c.base_height_m],[0,0,c.base.yaw_rad])}
        for name,pose in [('fixture',c.fixture),('workpiece',c.workpiece)]:expected[name]=([pose.x_m,pose.y_m,pose.z_m],[pose.roll_rad,pose.pitch_rad,pose.yaw_rad])
        # A world-anchored model must be respawned with the exact mounting transform.
        robot={name:expected[name] for name in ['weldx_robot','base_link']}
        try:self.verify(robot)
        except RoboticsError:
            if not allow_respawn:raise
            from .relocate import respawn
            respawn(self,c)
        for name in ['fixture','workpiece']:self.set(name,*expected[name])
        time.sleep(.3);first=self.verify(expected);time.sleep(.3);second=self.verify(expected)
        return {'immediate':first,'persistent':second}
