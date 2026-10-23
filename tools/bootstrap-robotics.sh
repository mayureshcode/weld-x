#!/usr/bin/env bash
# Run ONLY through tools/in-ubuntu. Packages modify the project-local rootfs.
set -euo pipefail
[[ -f /.weldx-project-rootfs ]] || { echo 'Refusing: run only inside the project-local Ubuntu rootfs.' >&2; exit 2; }
. /etc/os-release
[[ "$ID:$VERSION_ID" == ubuntu:24.04 ]]
mkdir -p /usr/sbin
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod +x /usr/sbin/policy-rc.d
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg locales python3 python3-venv python3-pip git build-essential cmake pkg-config xvfb x11-apps libgl1-mesa-dri mesa-utils dbus-x11
curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
# Official signed apt transport; HTTPS endpoint currently fails hostname verification.
# apt validates the repository Release signature with the ROS key; no trusted=yes.
printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main\n' > /etc/apt/sources.list.d/ros2.list
apt-get update
apt-get install -y --no-install-recommends ros-jazzy-ros-base ros-jazzy-moveit ros-jazzy-ros-gz ros-jazzy-gz-ros2-control ros-jazzy-ros2-controllers ros-jazzy-xacro ros-jazzy-joint-state-publisher python3-colcon-common-extensions python3-numpy python3-scipy
python3 -m venv --system-site-packages /opt/weldx-venv
/opt/weldx-venv/bin/pip install 'pydantic>=2.12,<3'
