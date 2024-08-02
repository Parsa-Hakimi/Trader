#!/usr/bin/env bash

source .venv/bin/activate
pip install -r requirements.txt
rm -rf metrics
mkdir metrics
export PROMETHEUS_MULTIPROC_DIR=metrics
mv logger.log "logs/$(date --rfc-3339 seconds).log" || true
python main.py 2>&1 | tee -i "logger.log"
