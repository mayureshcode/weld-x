#!/usr/bin/env bash
# Public one-command entrypoint; delegates lifecycle to the native launcher.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/scripts/start_weldx.sh" "$@"
