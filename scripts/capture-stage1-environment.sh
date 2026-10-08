#!/usr/bin/env bash
set -euo pipefail

output_path="${1:-data/raw/environment.txt}"
mkdir -p "$(dirname "$output_path")"

{
  echo "captured_utc=$(date --utc --iso-8601=seconds)"
  echo
  echo "[uname]"
  uname -a
  echo
  echo "[os-release]"
  sed -n '1,120p' /etc/os-release
  echo
  echo "[python]"
  python3 --version
  echo
  echo "[arduino-cli]"
  arduino-cli version
  echo
  echo "[router-status]"
  systemctl --no-pager --full status arduino-router || true
  echo
  echo "[router-command]"
  systemctl show arduino-router --property=ExecStart --no-pager || true
  echo
  echo "[router-socket]"
  stat /var/run/arduino-router.sock || true
  echo
  echo "[cpu]"
  lscpu
  echo
  echo "[memory]"
  free -h
} >"$output_path" 2>&1

echo "wrote $output_path"

