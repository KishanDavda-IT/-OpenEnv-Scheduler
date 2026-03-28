#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.
uvicorn api.app:app --host 0.0.0.0 --port 8000 &
python demo/app.py
