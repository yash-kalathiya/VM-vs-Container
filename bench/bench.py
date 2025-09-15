import time, subprocess, statistics, json, os, yaml, requests, psutil, pathlib, threading

CFG = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "config.yaml")))
OUT_DIR = pathlib.Path("bench/out"); OUT_DIR.mkdir(parents=True, exist_ok=True)


def time_to_ready(url: str, max_wait=30.0):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < max_wait:
        try:
            if requests.get(url.replace("/health", "") + "/health", timeout=0.5).ok:
                return time.perf_counter() - t0
        except Exception:
            pass
        time.sleep(0.1)
    return None


def wait_health_since(url: str, start_t: float, max_wait: float = 300.0) -> float | None:
    t0 = start_t
    while time.perf_counter() - t0 < max_wait:
        try:
            if requests.get(url.replace("/health", "") + "/health", timeout=0.5).ok:
                return time.perf_counter() - t0
        except Exception:
            pass
        time.sleep(0.1)
    return None


def simple_load(url: str, nreq: int, conc: int, payload_n: int):
    # crude load: bursty concurrent requests
    import concurrent.futures

    latencies = []

    def one():
        t0 = time.perf_counter()
        r = requests.get(f"{url}/primecount", params={"n": payload_n}, timeout=120)
        r.raise_for_status()
        latencies.append(time.perf_counter() - t0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=conc) as ex:
        futs = [ex.submit(one) for _ in range(nreq)]
        for f in futs:
            f.result()
    return {
        "p50": statistics.median(latencies),
        "avg": sum(latencies) / len(latencies),
        "p95": sorted(latencies)[int(0.95 * len(latencies)) - 1],
        "count": len(latencies),
    }


def docker_stats_once(container="flask-bench"):
    try:
        out = subprocess.check_output(
            [
                "bash",
                "-lc",
                "docker stats --no-stream --format '{{json .}}' " + container,
            ],
            text=True,
        ).strip()
        if not out:
            return {}
        j = json.loads(out)
        # Parse % and MiB
        cpu = float(j["CPUPerc"].strip("%"))
        mem_used, mem_total = j["MemUsage"].split(" / ")

        def parse_mem(s):  # handles MiB/GiB
            s = s.strip().upper()
            if s.endswith("GIB"):
                return float(s[: -3]) * 1024
            if s.endswith("MIB"):
                return float(s[: -3])
            return float(s)

        return {"cpu_pct": cpu, "mem_mib": parse_mem(mem_used)}
    except Exception:
        return {}


def measure_docker_startup(url: str, image: str = "test/flask-bench:local", container: str = "flask-bench") -> float:
    subprocess.call(["bash", "-lc", f"docker rm -f {container} >/dev/null 2>&1 || true"])  # best-effort
    t0 = time.perf_counter()
    subprocess.check_call(["bash", "-lc", f"docker run -d --name {container} -p 8000:8000 {image}"])
    dt = wait_health_since(url + "/health", t0, max_wait=300.0)
    if dt is None:
        raise SystemExit("docker did not become healthy")
    return dt


def run_target(label, start_cmd, url, stats_fn=None):
    # assume target already started by scripts
    ready = time_to_ready(url + "/health")
    if ready is None:
        raise SystemExit(f"{label} not ready")

    trial_stats = []
    cpu_samples, mem_samples = [], []

    for t in range(CFG["trials"]):
        # sample resource periodically during load (best-effort)
        sampler_stop = None
        sampler_thread = None
        if stats_fn:
            import threading

            sampler_stop = threading.Event()

            def sampler():
                while not sampler_stop.is_set():
                    try:
                        s = stats_fn()
                        if isinstance(s, dict):
                            if "cpu_pct" in s:
                                cpu_samples.append(float(s["cpu_pct"]))
                            if "mem_mib" in s:
                                mem_samples.append(float(s["mem_mib"]))
                    except Exception:
                        pass
                    time.sleep(0.3)

            sampler_thread = threading.Thread(target=sampler, daemon=True)
            sampler_thread.start()

        m = simple_load(url, CFG["requests"], CFG["concurrency"], CFG["prime_n"])

        if sampler_stop is not None:
            sampler_stop.set()
        if sampler_thread is not None:
            sampler_thread.join(timeout=1.0)

        trial_stats.append(m)

    def agg(field):
        vals = [x[field] for x in trial_stats]
        return {"avg": sum(vals) / len(vals), "stdev": statistics.pstdev(vals)}

    result = {
        "label": label,
        "ready_seconds": ready,
        "latency_avg": agg("avg"),
        "latency_p50": agg("p50"),
        "latency_p95": agg("p95"),
        "throughput_rps_est": {
            "avg": CFG["requests"] / agg("avg")["avg"],
            "stdev": 0.0,
        },
        "cpu_samples": cpu_samples,
        "mem_samples_mib": mem_samples,
    }
    return result


def main():
    results = []
    # Docker target assumed running via scripts/run_docker.sh
    results.append(
        run_target(
            "docker",
            None,
            CFG["docker_url"],
            stats_fn=docker_stats_once,
        )
    )
    # VM target: sample metrics inside guest using background sampler
    def run_target_vm(url: str):
        # Ensure it's halted first (synchronously), then measure cold start up to health
        subprocess.call(["bash", "-lc", "vagrant halt -f"], cwd="vagrant")

        def vm_up():
            subprocess.check_call(["bash", "-lc", "vagrant up --provision"], cwd="vagrant")

        t0 = time.perf_counter()
        th = threading.Thread(target=vm_up, daemon=True)
        th.start()
        ready = wait_health_since(url + "/health", t0, max_wait=1200.0)
        if ready is None:
            raise SystemExit("vm not ready")
        th.join(timeout=5.0)

        trial_stats = []
        cpu_samples, mem_samples = [], []

        def vm_ssh(cmd: str):
            # Ensure command runs via bash -lc inside guest to support nohup and redirects
            wrapped = f"vagrant ssh -c \"bash -lc '{cmd}'\""
            return subprocess.check_output(["bash", "-lc", wrapped], cwd="vagrant", text=True)

        for t in range(CFG["trials"]):
            out_path = f"/tmp/vmstats_{t}.jsonl"
            duration = 5.0
            # start sampler in background
            vm_ssh(
                f"rm -f {out_path}; nohup /home/vagrant/appenv/bin/python /project/bench/vm_sampler.py --out {out_path} --interval 0.2 --duration {duration} >/dev/null 2>&1 &"
            )
            # run load
            m = simple_load(url, CFG["requests"], CFG["concurrency"], CFG["prime_n"])
            trial_stats.append(m)
            # brief pause to overlap with remaining sampler time
            time.sleep(0.3)

        # allow last sampler to finish then collect all samples
        time.sleep(5.5)
        try:
            txt = vm_ssh("cat /tmp/vmstats_*.jsonl 2>/dev/null || true")
            for line in txt.splitlines():
                try:
                    j = json.loads(line)
                    if "cpu_pct" in j:
                        cpu_samples.append(float(j["cpu_pct"]))
                    if "mem_mib" in j:
                        mem_samples.append(float(j["mem_mib"]))
                except Exception:
                    pass
        except Exception:
            pass

        def agg(field):
            vals = [x[field] for x in trial_stats]
            return {"avg": sum(vals) / len(vals), "stdev": statistics.pstdev(vals)}

        return {
            "label": "vm",
            "ready_seconds": ready,
            "latency_avg": agg("avg"),
            "latency_p50": agg("p50"),
            "latency_p95": agg("p95"),
            "throughput_rps_est": {"avg": CFG["requests"] / agg("avg")["avg"], "stdev": 0.0},
            "cpu_samples": cpu_samples,
            "mem_samples_mib": mem_samples,
        }

    # Start Docker fresh and measure startup
    try:
        docker_start = measure_docker_startup(CFG["docker_url"], image="test/flask-bench:local", container="flask-bench")
    except Exception:
        # fall back to assuming it's already running
        docker_start = time_to_ready(CFG["docker_url"] + "/health") or 0.0

    # Re-run docker target to include the measured startup time in result
    r_d = results.pop(0)
    r_d["ready_seconds"] = docker_start
    results.insert(0, r_d)

    # Run VM target (this also measures VM startup time internally)
    results.append(run_target_vm(CFG["vm_url"]))

    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Wrote", OUT_DIR / "results.json")


if __name__ == "__main__":
    main()
