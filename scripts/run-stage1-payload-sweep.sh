#!/usr/bin/env bash
set -euo pipefail

sizes_path="${1:-config/stage1-payload-sizes.txt}"
output_path="${2:-data/raw/rpc-roundtrip.jsonl}"
iterations="${QF_ITERATIONS:-1000}"
warmup="${QF_WARMUP:-100}"
timeout="${QF_TIMEOUT:-5}"
preflight_timeout="${QF_PREFLIGHT_TIMEOUT:-0.25}"
failure_iterations="${QF_FAILURE_ITERATIONS:-20}"
sample_failures=0
preflight_output="$(mktemp)"
trap 'rm -f "$preflight_output"' EXIT

while IFS= read -r payload_size; do
  if [[ -z "$payload_size" || "$payload_size" == \#* ]]; then
    continue
  fi

  : >"$preflight_output"
  set +e
  qf-stage1 run roundtrip \
    --payload-size "$payload_size" \
    --iterations 1 \
    --warmup 0 \
    --timeout "$preflight_timeout" \
    --output "$preflight_output" >/dev/null
  preflight_exit_code=$?
  set -e

  case "$preflight_exit_code" in
    0) ;;
    2)
      echo "payload $payload_size failed preflight; recording a bounded failure sample" >&2
      set +e
      qf-stage1 run roundtrip \
        --payload-size "$payload_size" \
        --iterations "$failure_iterations" \
        --warmup 0 \
        --timeout "$preflight_timeout" \
        --output "$output_path"
      failure_exit_code=$?
      set -e

      case "$failure_exit_code" in
        0 | 2) sample_failures=1 ;;
        *) exit "$failure_exit_code" ;;
      esac
      continue
      ;;
    *) exit "$preflight_exit_code" ;;
  esac

  set +e
  qf-stage1 run roundtrip \
    --payload-size "$payload_size" \
    --iterations "$iterations" \
    --warmup "$warmup" \
    --timeout "$timeout" \
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
