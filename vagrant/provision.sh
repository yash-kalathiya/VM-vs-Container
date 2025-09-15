#!/usr/bin/env bash
set -e
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv git
cd /project
VENV=/home/vagrant/appenv
python3 -m venv "$VENV"
. "$VENV"/bin/activate
pip install -r app/requirements.txt
# run app via gunicorn (systemd-free for simplicity)
pkill -f gunicorn || true
nohup "$VENV"/bin/gunicorn -w 1 -b 0.0.0.0:8000 app.wsgi:application >/project/vm_gunicorn.log 2>&1 &
echo "VM app started"
