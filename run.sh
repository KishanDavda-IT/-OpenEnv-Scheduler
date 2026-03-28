#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.
export API_URL="http://127.0.0.1:7860"

echo "🚀 Starting OpenEnv Compliant Server on port 7860..."
echo "📊 Dashboard will be available at: /dashboard"

# Run FastAPI (which now includes the mounted Gradio UI)
# We use 7860 because it's the default port for Hugging Face Spaces and the OpenEnv validator.
uvicorn server.app:app --host 0.0.0.0 --port 7860
