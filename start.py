# start.py - Python startup script (avoids CRLF issues on Windows)
import subprocess
import sys
import os

def main():
    os.environ.setdefault("PYTHONPATH", ".")
    os.environ.setdefault("API_URL", "http://127.0.0.1:7860")

    print("Starting OpenEnv Compliant Server on port 7860...")
    print("Dashboard will be available at: /")

    # Run FastAPI with mounted Gradio on port 7860
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "server.app:app",
        "--host", "0.0.0.0",
        "--port", "7860"
    ])

if __name__ == "__main__":
    main()
