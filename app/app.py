from flask import Flask, request, jsonify
import time

app = Flask(__name__)

@app.post("/deploy")
def deploy():
    payload = request.get_json(force=True)
    print("Received deploy webhook:", payload)
    # You could trigger a local script, pull new image, restart service, etc.
    return jsonify(status="received", at=time.time())

@app.get("/health")
def health():
    return jsonify(status="ok")


def count_primes(n: int) -> int:
    # Sieve of Eratosthenes (CPU-heavy for big n)
    sieve = bytearray(b"\x01") * (n + 1)
    sieve[0:2] = b"\x00\x00"
    lim = int(n ** 0.5)
    for p in range(2, lim + 1):
        if sieve[p]:
            step = p
            start = p * p
            sieve[start : n + 1 : step] = b"\x00" * (((n - start) // step) + 1)
    return sum(sieve)


@app.get("/primecount")
def primecount():
    n = int(request.args.get("n", "300000"))
    t0 = time.perf_counter()
    c = count_primes(n)
    dt = time.perf_counter() - t0
    return jsonify(n=n, primes=c, seconds=round(dt, 4))


@app.get("/")
def index():
    return jsonify(msg="OK, try /health or /primecount?n=300000")

