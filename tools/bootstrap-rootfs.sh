#!/usr/bin/env bash
# Explicit opt-in project-local Ubuntu fallback. Never modifies host apt sources.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD/.runtime/ubuntu-rootfs";mkdir -p .runtime/downloads
if [ -e "$root/etc/os-release" ]; then echo 'Existing rootfs preserved; use tools/in-ubuntu.';exit 0;fi
command -v unshare >/dev/null;sudo -n true
name=ubuntu-base-24.04.3-base-amd64.tar.gz
url=https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release
curl -fL --retry 2 "$url/$name" -o ".runtime/downloads/$name"
printf '6bc2cde3930ad088b3bb46fa45279e96d25bc3810f209850ecbe4722711874f9  %s\n' ".runtime/downloads/$name" | sha256sum -c -
mkdir -p "$root";sudo tar --numeric-owner -xpf ".runtime/downloads/$name" -C "$root"
sudo touch "$root/.weldx-project-rootfs"
sudo cp /etc/resolv.conf "$root/etc/resolv.conf"
sudo mkdir -p "$root/workspace" "$root/proc" "$root/dev"
echo 'Rootfs ready. Next: tools/in-ubuntu bash /workspace/tools/bootstrap-robotics.sh'
