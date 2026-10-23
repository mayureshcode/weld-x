"""Simulation-only anchored robot relocation via verified respawn.
Direct set_pose cannot reliably relocate a robot fixed to world; never trust its ack.
"""
from pathlib import Path
import subprocess,time,xml.etree.ElementTree as ET
from gz.msgs10.entity_pb2 import Entity
from gz.msgs10.boolean_pb2 import Boolean
from .cell import RoboticsError

def respawn(scene,c):
    if 'weldx_robot' in scene.poses():
        entity=Entity();entity.name='weldx_robot';entity.type=Entity.MODEL
        response=scene.service('/world/weldx_cell/remove',entity,Boolean(),'gz.msgs.Entity','gz.msgs.Boolean')
        if not response.data:raise RoboticsError('controller','robot removal rejected')
        time.sleep(1)
    root=ET.parse('/workspace/.runtime/generated/weldx.urdf').getroot()
    ET.SubElement(root,'link',name='world');joint=ET.SubElement(root,'joint',name='world_anchor',type='fixed')
    ET.SubElement(joint,'parent',link='world');ET.SubElement(joint,'child',link='base_link')
    ET.SubElement(joint,'origin',xyz=f'{c.base.x_m} {c.base.y_m} {c.base_height_m}',rpy=f'0 0 {c.base.yaw_rad}')
    path=Path('/workspace/.runtime/generated/weldx-relocated.urdf');ET.ElementTree(root).write(path,encoding='unicode',xml_declaration=True)
    commands=[['ros2','run','ros_gz_sim','create','-world','weldx_cell','-name','weldx_robot','-file',str(path)],
        ['ros2','run','controller_manager','spawner','joint_state_broadcaster','--controller-manager-timeout','45'],
        ['ros2','run','controller_manager','spawner','joint_trajectory_controller','--controller-manager-timeout','45']]
    records=[]
    for cmd in commands:
        run=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
        records.append({'command':cmd,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
        if run.returncode:raise RoboticsError('controller','robot respawn/controller initialization failed: '+str(records))
    return records
