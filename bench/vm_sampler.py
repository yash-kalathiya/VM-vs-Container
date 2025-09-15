import argparse, json, time, psutil


def find_gunicorn_pid():
    candidates = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
            if "gunicorn" in cmd and "wsgi:application" in cmd:
                rss = psutil.Process(p.info["pid"]).memory_info().rss
                candidates.append((rss, p.info["pid"]))
        except Exception:
            pass
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=0.2)
    ap.add_argument("--duration", type=float, default=5.0)
    args = ap.parse_args()

    t_end = time.time() + args.duration
    pid = find_gunicorn_pid()
    proc = psutil.Process(pid) if pid else None
    with open(args.out, "a") as f:
        while time.time() < t_end:
            if proc is None:
                time.sleep(args.interval)
                continue
            cpu = proc.cpu_percent(interval=args.interval)
            mem = proc.memory_info().rss / (1024 * 1024)
            f.write(json.dumps({"cpu_pct": cpu, "mem_mib": mem, "ts": time.time()}) + "\n")


if __name__ == "__main__":
    main()
