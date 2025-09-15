#!/usr/bin/env sh
set -e
docker build -t "${IMAGE:-test/flask-bench}:${TAG:-local}" -f docker/Dockerfile .
docker rm -f flask-bench 2>/dev/null || true
docker run -d --name flask-bench -p 8000:8000 "${IMAGE:-test/flask-bench}:${TAG:-local}"
# Wait for health
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/health >/dev/null; then exit 0; fi
  sleep 0.5
done
echo "Container failed to become healthy" >&2; exit 1

