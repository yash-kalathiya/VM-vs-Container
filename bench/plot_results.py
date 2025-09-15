import json, pathlib, matplotlib.pyplot as plt

OUT = pathlib.Path("bench/out")
data = json.loads((OUT / "results.json").read_text())


def barpair(ax_title, docker_val, vm_val, ylabel, fname):
    plt.figure()
    xs = ["Docker", "VM"]
    ys = [docker_val, vm_val]
    plt.title(ax_title)
    plt.ylabel(ylabel)
    plt.bar(xs, ys)
    plt.savefig(OUT / fname, bbox_inches="tight")


dock = next(x for x in data if x["label"] == "docker")
vm = next(x for x in data if x["label"] == "vm")

barpair("Startup time (s)", dock["ready_seconds"], vm["ready_seconds"], "seconds", "startup.png")
barpair(
    "Avg latency (s)",
    dock["latency_avg"]["avg"],
    vm["latency_avg"]["avg"],
    "seconds",
    "latency_avg.png",
)
barpair(
    "P95 latency (s)",
    dock["latency_p95"]["avg"],
    vm["latency_p95"]["avg"],
    "seconds",
    "latency_p95.png",
)
barpair(
    "Throughput (RPS est.)",
    dock["throughput_rps_est"]["avg"],
    vm["throughput_rps_est"]["avg"],
    "rps",
    "throughput.png",
)


def avg(v):
    return sum(v) / len(v) if v else 0.0


# Memory & CPU sample averages
barpair(
    "RSS memory (MiB, sampled)",
    avg(dock["mem_samples_mib"]),
    avg(vm["mem_samples_mib"]),
    "MiB",
    "memory.png",
)
barpair(
    "CPU util (% of proc, sampled)",
    avg(dock["cpu_samples"]),
    avg(vm["cpu_samples"]),
    "%",
    "cpu.png",
)
print("Wrote plots to", OUT)

