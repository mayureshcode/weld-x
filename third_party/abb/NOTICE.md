# ABB IRB 120 model provenance

Source: ros-industrial/abb, commit 45f4769d826cf3ac62a65495f2db67b78b0c81df.
Paths: abb_irb120_support/{urdf/irb120_3_58_macro.xacro,meshes/irb120_3_58,LICENSE}.
Upstream package authors: Mark Culleton, Kevin Kelly (Trinity College Dublin), Levi Armstrong (SwRI); ROS-Industrial community maintained. Package declares Apache-2.0; full license retained.

Meshes are copied without modification. Generated WELD-X URDF retains numerical joint origins, axes, position and velocity limits; it adds a dummy torch/TCP, ros2_control interfaces and Gazebo plugin. Effort capacity is explicitly a simulated ideal-position-drive parameter (1000 Nm), NOT an ABB torque rating or physical-fidelity claim. Original upstream effort values were zero. The model remains PROVISIONAL pending actual integration tests. No OEM support, affiliation or safety certification is claimed.
