#!/usr/bin/env bash

source .venv/bin/activate
pip install -r requirements.txt
python main.py 2>&1 | tee -i "logger.log"
