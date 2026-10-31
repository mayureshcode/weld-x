"""Read-only ROS 2 topic telemetry → atomic local JSON snapshot.

This deliberately DOES NOT synchronize the planning scene, authorize execution,
or articulate a generic GLB. Joint/TF sample timestamps are receipt time.
Run only in an environment where rclpy and sensor_msgs/tf2_msgs are installed.
"""
import argparse
import json
import math
import os
from pathlib import Path
import time

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default=".runtime/ros_telemetry.json")
    parser.add_argument("--joint-topic",default="/joint_states")
    args=parser.parse_args()
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState
    from tf2_msgs.msg import TFMessage

    class Snapshot(Node):
        def __init__(self):
            super().__init__("weldx_telemetry_monitor")
            self.output=Path(args.output)
            self.output.parent.mkdir(parents=True,exist_ok=True)
            self.joints={}
            self.frames=set()
            self.received=False
            self.last_receipt=0
            self.create_subscription(JointState,args.joint_topic,self.joints_cb,10)
            self.create_subscription(TFMessage,"/tf",self.tf_cb,10)
            self.create_subscription(TFMessage,"/tf_static",self.tf_cb,10)
            self.create_timer(0.25,self.flush)
        def joints_cb(self,msg):
            self.received=True;self.last_receipt=time.time()
            for name,value in zip(msg.name,msg.position):
                if name and math.isfinite(value):
                    self.joints[name]=float(value)
        def tf_cb(self,msg):
            self.received=True;self.last_receipt=time.time()
            for tr in msg.transforms:
                if tr.header.frame_id and tr.child_frame_id:
                    self.frames.add((tr.header.frame_id,tr.child_frame_id))
        def flush(self):
            # A recent ROS topic receipt is required, not merely a running bridge.
            fresh=self.received and time.time()-self.last_receipt<3
            payload={"received":fresh,"joints":[{"name":n,"position":v} for n,v in sorted(self.joints.items())][:32] if fresh else [],
                     "tf_count":len(self.frames) if fresh else 0,"receipt_unix_s":self.last_receipt}
            tmp=self.output.with_suffix(self.output.suffix+".tmp")
            tmp.write_text(json.dumps(payload,separators=(",",":")))
            os.replace(tmp,self.output)
    rclpy.init()
    node=Snapshot()
    try:rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
if __name__=="__main__":
    main()
