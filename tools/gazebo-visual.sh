#!/usr/bin/env bash
# Run inside isolated Ubuntu through ros-env; software rendering, own X server.
set -euo pipefail
export DISPLAY=:77 LIBGL_ALWAYS_SOFTWARE=1 QT_X11_NO_MITSHM=1
Xvfb :77 -screen 0 1440x900x24 -ac -nolisten tcp > /workspace/evidence/phase2/xvfb.log 2>&1 &
xpid=$!
trap 'kill "$xpid" 2>/dev/null || true' EXIT
sleep 1
glxinfo -B > /workspace/evidence/phase2/software-renderer.log 2>&1
gz sim -g -v 3
