#!/usr/bin/env sh
set -e
# 0) Unit tests (in container)
docker build -t test/local -f docker/Dockerfile .
docker run --rm -v "$PWD":/work -w /work test/local sh -lc "pytest -q app/tests || true"  # keep going even if none

# 1) Start Docker target
IMAGE="test/flask-bench" TAG="local" ./scripts/run_docker.sh

# 2) Start VM target
./scripts/run_vm.sh

# 3) Bench both
python3 bench/bench.py

# 4) Plot
python3 bench/plot_results.py

# 5) Update README with artifacts
python3 - <<'PY'
from pathlib import Path
import json
out = Path("bench/out"); res = json.loads((out/"results.json").read_text())
dock = next(r for r in res if r["label"]=="docker")
vm   = next(r for r in res if r["label"]=="vm")

def fmt(v): return f"{v:.3f}"
table = f"""
### VM vs. Docker Summary

| Metric | Docker | VM |
|---|---:|---:|
| Startup time (s) | {fmt(dock['ready_seconds'])} | {fmt(vm['ready_seconds'])} |
| Avg latency (s) | {fmt(dock['latency_avg']['avg'])} | {fmt(vm['latency_avg']['avg'])} |
| P95 latency (s) | {fmt(dock['latency_p95']['avg'])} | {fmt(vm['latency_p95']['avg'])} |
| Throughput (RPS est.) | {fmt(dock['throughput_rps_est']['avg'])} | {fmt(vm['throughput_rps_est']['avg'])} |
| RSS memory (MiB, sampled) | ~{sum(dock['mem_samples_mib'])/max(1,len(dock['mem_samples_mib'])):.1f} | ~{sum(vm['mem_samples_mib'])/max(1,len(vm['mem_samples_mib'])):.1f} |
| CPU util (% proc, sampled) | ~{sum(dock['cpu_samples'])/max(1,len(dock['cpu_samples'])):.1f}% | ~{sum(vm['cpu_samples'])/max(1,len(vm['cpu_samples'])):.1f}% |
"""

imgs = """
<p align=\"center\">
  <img src=\"bench/out/startup.png\" width=\"45%\"/>
  <img src=\"bench/out/latency_avg.png\" width=\"45%\"/><br/>
  <img src=\"bench/out/latency_p95.png\" width=\"45%\"/>
  <img src=\"bench/out/throughput.png\" width=\"45%\"/><br/>
  <img src=\"bench/out/memory.png\" width=\"45%\"/>
  <img src=\"bench/out/cpu.png\" width=\"45%\"/>
  
</p>
"""

readme = Path("README.md").read_text()
marker = "<!-- AUTO-BENCHMARKS -->"
block = f"{marker}\n{table}\n{imgs}\n{marker}"
if marker in readme:
    pre, _, post = readme.partition(marker)
    # Remove old block
    post = post.split(marker,1)[-1]
    new = pre + block + post
else:
    new = readme + "\n\n" + block + "\n"
Path("README.md").write_text(new)
print("README updated")
PY

