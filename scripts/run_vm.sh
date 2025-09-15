#!/usr/bin/env sh
set -e
cd vagrant
vagrant up
# Wait for forwarded port to respond
for i in $(seq 1 60); do
  if curl -sf http://localhost:8001/health >/dev/null; then exit 0; fi
  sleep 0.5
done
echo "VM app failed to become healthy" >&2; exit 1

