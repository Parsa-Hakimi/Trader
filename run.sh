#!/usr/bin/env bash

source .venv/bin/activate
pip install -r requirements.txt
export PROMETHEUS_MULTIPROC_DIR=metrics
python actor.py 2>&1 | tee -i "logger.log"
