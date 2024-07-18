#!/usr/bin/env bash

source .venv/bin/activate
pip install -r requirements.txt
python main.py | tee -i "logger.log"
