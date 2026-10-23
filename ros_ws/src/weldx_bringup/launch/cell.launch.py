"""Real Jazzy / Harmonic / MoveIt bringup, not a dashboard simulator."""
from pathlib import Path
import os
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, SetEnvironmentVariable
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    desc=Path(get_package_share_directory('weldx_description'))
    bringup=Path(get_package_share_directory('weldx_bringup'))
    generated=Path('/workspace/.runtime/generated');generated.mkdir(parents=True,exist_ok=True)
    urdf=(desc/'urdf/weldx.urdf.in').read_text().replace('@ASSET_DIR@',str(desc)).replace('@CONFIG_DIR@',str(bringup/'config'))
    (generated/'weldx.urdf').write_text(urdf)
    sim=ET.fromstring(urdf)
    ET.SubElement(sim,'link',name='world')
    anchor=ET.SubElement(sim,'joint',name='world_anchor',type='fixed')
    ET.SubElement(anchor,'parent',link='world');ET.SubElement(anchor,'child',link='base_link')
    ET.ElementTree(sim).write(generated/'weldx-sim.urdf',encoding='unicode',xml_declaration=True)
    config=(MoveItConfigsBuilder('weldx',package_name='weldx_bringup')
        .robot_description(file_path=str(generated/'weldx.urdf'))
        .robot_description_semantic(file_path='config/weldx.srdf')
        .robot_description_kinematics(file_path='config/kinematics.yaml')
        .joint_limits(file_path='config/joint_limits.yaml')
        .trajectory_execution(file_path='config/moveit_controllers.yaml')
        .planning_pipelines(default_planning_pipeline='ompl',pipelines=['ompl'])
        .to_moveit_configs())
    gazebo=ExecuteProcess(cmd=['gz','sim','-r','-s','-v','3',str(desc/'worlds/cell.sdf')],output='screen')
    rsp=Node(package='robot_state_publisher',executable='robot_state_publisher',parameters=[{'robot_description':urdf,'use_sim_time':True}],output='screen')
    bridge=Node(package='ros_gz_bridge',executable='parameter_bridge',arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],output='screen')
    spawn=Node(package='ros_gz_sim',executable='create',arguments=['-world','weldx_cell','-name','weldx_robot','-file',str(generated/'weldx-sim.urdf')],output='screen')
    js=Node(package='controller_manager',executable='spawner',arguments=['joint_state_broadcaster','--controller-manager-timeout','120'],output='screen')
    controller=Node(package='controller_manager',executable='spawner',arguments=['joint_trajectory_controller','--controller-manager-timeout','120'],output='screen')
    move_group=Node(package='moveit_ros_move_group',executable='move_group',parameters=[config.to_dict(),{'use_sim_time':True,'publish_robot_description_semantic':True,'publish_planning_scene':True,'publish_geometry_updates':True,'publish_state_updates':True,'publish_transforms_updates':True}],output='screen')
    return LaunchDescription([
        SetEnvironmentVariable('GZ_PARTITION','weldx_virtual'),
        gazebo,rsp,bridge,spawn,
        RegisterEventHandler(OnProcessExit(target_action=spawn,on_exit=[js])),
        RegisterEventHandler(OnProcessExit(target_action=js,on_exit=[controller])),
        RegisterEventHandler(OnProcessExit(target_action=controller,on_exit=[move_group])),
    ])
