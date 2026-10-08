#!/usr/bin/env bash
set -euo pipefail

sizes_path="${1:-config/stage1-payload-sizes.txt}"
output_path="${2:-data/raw/rpc-roundtrip.jsonl}"
iterations="${QF_ITERATIONS:-1000}"
warmup="${QF_WARMUP:-100}"
sample_failures=0

while IFS= read -r payload_size; do
  if [[ -z "$payload_size" || "$payload_size" == \#* ]]; then
    continue
  fi

  set +e
  qf-stage1 run roundtrip \
    --payload-size "$payload_size" \
    --iterations "$iterations" \
    --warmup "$warmup" \
    --output "$output_path"
  exit_code=$?
  set -e

  case "$exit_code" in
    0) ;;
    2) sample_failures=1 ;;
    *) exit "$exit_code" ;;
  esac
done <"$sizes_path"

if ((sample_failures)); then
  exit 2
fi
