# Stage 1: UNO Q hardware and timing characterization

Stage 1 deliberately chooses no timing contract. Its output is the dataset used to select defensible thresholds later.

## Responsibility split

Codex maintains the benchmark, analysis, tests, and documentation. The developer runs package installation, flashing, load generation, and hardware measurements on the connected UNO Q.

## Workstation installation and checks

Install ADB on Debian/Ubuntu:

```bash
sudo apt update
sudo apt install adb
adb version
```

If `adb devices -l` shows a permissions error on Linux, install the standard Android udev rules package for your distribution or run the command once with appropriate device permissions; do not make the device globally writable.

Check the existing toolchain:

```bash
arduino-cli version
cmake --version
gcc --version
python3 --version
gh auth status
```

Connect the UNO Q and confirm that ADB can see it:

```bash
adb devices -l
arduino-cli board list
```

If the ADB device is unauthorized, accept the debugging prompt on the board and run `adb devices -l` again.

## Python environment

After the initial QFabric commit has been pushed, enter the UNO Q Linux environment and clone the repository there. The benchmark must run on the board because the default Router socket is local to its Linux domain:

```bash
adb shell
git clone https://github.com/Circuit-Overtime/QFabric.git
cd QFabric
```

Create the environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
qf-stage1 --help
```

The harness uses Arduino's official `arduino-router-bridge` Python package and defaults to `unix:///var/run/arduino-router.sock`.

## Arduino core and library checks

```bash
arduino-cli config add board_manager.additional_urls \
  https://downloads.arduino.cc/packages/package_zephyr_index.json
arduino-cli core update-index
arduino-cli core list
arduino-cli lib list
arduino-cli board details --fqbn arduino:zephyr:unoq
```

Install missing components only if the checks show they are absent:

```bash
arduino-cli core install arduino:zephyr
```

`Arduino_LED_Matrix` is supplied through the UNO Q Zephyr platform. `Arduino_RouterBridge`
is a separate official Arduino library. The benchmark's default `sketch.yaml` profile pins
the core, RouterBridge, and its dependency chain and downloads them into Arduino CLI's isolated
profile cache during compilation. A global Library Manager installation is useful for examples
but is not required or used by the isolated profile build. Do not substitute similarly named
third-party Bridge or matrix libraries.

## Compile and flash the MCU probe

Compile first:

```bash
arduino-cli compile \
  --fqbn arduino:zephyr:unoq \
  benchmarks/stage1/mcu/stage1_probe
```

The exact upload path depends on the connected UNO Q mode. Confirm it with `arduino-cli board list`, then upload using the detected port:

```bash
arduino-cli upload \
  --fqbn arduino:zephyr:unoq \
  --port DETECTED_PORT \
  benchmarks/stage1/mcu/stage1_probe
```

Do not open `/dev/ttyHS1` directly. It is reserved by `arduino-router`.

## Router checks on the UNO Q

```bash
systemctl status arduino-router --no-pager
systemctl show arduino-router --property=ExecStart --no-pager
stat /var/run/arduino-router.sock
```

Capture the environment before each firmware/software change:

```bash
bash scripts/capture-stage1-environment.sh
```

## Smoke tests

Run the complete smoke suite from the UNO Q Linux environment. The script verifies the Router
socket, captures the environment, and writes each run to a new timestamped directory:

```bash
bash scripts/run-stage1-smoke.sh
```

An optional run label makes a result directory easier to identify:

```bash
bash scripts/run-stage1-smoke.sh first-hardware-run
```

The equivalent individual commands are:

```bash
qf-stage1 run roundtrip \
  --payload-size 8 \
  --iterations 20 \
  --warmup 5 \
  --output data/raw/smoke.jsonl

qf-stage1 run clock \
  --iterations 20 \
  --warmup 5 \
  --output data/raw/smoke-clock.jsonl

qf-stage1 run matrix \
  --iterations 20 \
  --warmup 5 \
  --output data/raw/smoke-matrix.jsonl
```

## Full payload sweep

Run a complete three-repetition idle campaign from the UNO Q. This includes every configured
payload size plus clock and matrix experiments, with separate raw and processed files for each
repetition:

```bash
QF_REPETITIONS=3 QF_ITERATIONS=1000 QF_WARMUP=100 \
  bash scripts/run-stage1-campaign.sh idle initial-idle
```

The lower-level payload-only command remains available for focused experiments:

```bash
QF_ITERATIONS=1000 QF_WARMUP=100 \
  bash scripts/run-stage1-payload-sweep.sh
```

The campaign runner exits with status 2 if RPC samples fail, but retains and analyzes those
samples because payload-limit failures are useful saturation evidence. It stops immediately for
an infrastructure error. Never concatenate measurements from different firmware or system
configurations without matching environment metadata.

## Controlled Linux contention

Install the load generator on the UNO Q:

```bash
sudo apt update
sudo apt install stress-ng
stress-ng --version
```

Start with CPU contention only:

```bash
stress-ng --cpu 4 --cpu-method all --metrics-brief --timeout 10m
```

Run the QFabric sweep from a second session while the load is active. Later runs may add memory and I/O contention, but each load profile must be recorded separately.

## Analysis

```bash
qf-stage1 analyze \
  --input data/raw/rpc-roundtrip.jsonl \
  --json data/processed/rpc-roundtrip-summary.json \
  --csv data/processed/rpc-roundtrip-summary.csv
```

The analyzer reports total and successful sample counts, failure rate, minimum, p50, p95, p99, maximum, mean, population standard deviation, and the achieved sequential call rate grouped by experiment and payload size.
It keeps distinct `run_id` values separate so repeated runs cannot be silently pooled. For the
matrix experiment it also reports the MCU-returned `mcu_execution_us` distribution. That local
value measures the duration of the `Arduino_LED_Matrix.draw()` call; it does not claim to measure
the panel's complete optical refresh time.

## Clock rule

Linux `perf_counter_ns()` measures end-to-end call duration. MCU `micros()` is stored only as a local clock sample or local execution diagnostic. Do not subtract the two clocks. A one-way timing model requires a separate offset/drift method and uncertainty bound.

## Stage completion gate

Stage 1 is complete only when issue #2 contains:

- exact hardware and software versions;
- raw data and reproduction commands;
- at least three clean repetitions per configuration;
- idle and loaded results;
- payload and RPC-rate saturation behavior;
- clock limitations;
- MCU resource/headroom measurements;
- LED update overhead; and
- reviewed recommendations for later contract thresholds.

## Official references

- [UNO Q user manual](https://docs.arduino.cc/tutorials/uno-q/user-manual/)
- [Arduino Router Bridge Python client](https://github.com/arduino/arduino-router-bridge-py)
- [Arduino Router service](https://github.com/arduino/arduino-router)
- [Arduino CLI sketch project format](https://arduino.github.io/arduino-cli/latest/sketch-project-file/)
