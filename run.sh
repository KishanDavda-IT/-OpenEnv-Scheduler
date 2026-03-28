#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.

echo "🚀 Starting OpenEnv API on port 8000..."
uvicorn api.app:app --host 0.0.0.0 --port 8000 &

echo "⏳ Waiting for API to be ready..."
python3 -c "
import requests, time, sys
for i in range(15):
    try:
        if requests.get('http://127.0.0.1:8000/tasks').status_code == 200:
            print('✅ API is up and running!')
            sys.exit(0)
    except Exception:
        pass
    print(f'...waiting ({i+1})...')
    time.sleep(2)
sys.exit(1)
" || (echo "❌ API failed to start in time!"; exit 1)

echo "🎨 Starting Gradio Dashboard on port 7860..."
python demo/app.py
