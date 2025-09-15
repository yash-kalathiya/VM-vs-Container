import json, psutil, time, os, sys


def find_gunicorn_pid():
    candidates = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
            if "gunicorn" in cmd and "wsgi:application" in cmd:
                # prefer worker (typically larger RSS)
                rss = psutil.Process(p.info["pid"]).memory_info().rss
                candidates.append((rss, p.info["pid"]))
        except Exception:
            pass
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


pid = find_gunicorn_pid()

if len(sys.argv) > 1 and sys.argv[1] == "--once":
    out = {"pid": pid, "cpu_pct": 0.0, "mem_mib": 0.0}
    if pid:
        p = psutil.Process(pid)
        out["cpu_pct"] = p.cpu_percent(interval=0.2)
        out["mem_mib"] = p.memory_info().rss / (1024 * 1024)
    print(json.dumps(out))
    sys.exit(0)

cpu_samples = []
rss_samples = []
if pid:
    proc = psutil.Process(pid)
    for _ in range(5):
        cpu_samples.append(proc.cpu_percent(interval=0.5))  # %
        rss_samples.append(proc.memory_info().rss / (1024 * 1024))  # MiB
info = {
    "pid": pid,
    "cpu_pct_samples": cpu_samples,
    "rss_mib_samples": rss_samples,
}
print(json.dumps(info))
