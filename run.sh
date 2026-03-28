#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.

echo "🚀 Starting OpenEnv API on port 8000..."
uvicorn api.app:app --host 0.0.0.0 --port 8000 > api_logs.txt 2>&1 &

echo "⏳ Waiting for API to be ready..."
for i in {1..10}; do
  if curl -s http://127.0.0.1:8000/tasks > /dev/null; then
    echo "✅ API is up and running!"
    break
  fi
  echo "...waiting..."
  sleep 2
done

echo "🎨 Starting Gradio Dashboard on port 7860..."
python demo/app.py
