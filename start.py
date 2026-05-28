"""Start both backend and frontend dev servers."""
import subprocess
import sys
import time
import json
from pathlib import Path

ROOT = Path(__file__).parent
STATE_FILE = ROOT / ".server_state.json"


def start():
    procs = {}

    # Backend
    print("[start] launching backend (FastAPI + uvicorn)...")
    backend_log = open(ROOT / "logs" / "backend.log", "w", encoding="utf-8")
    backend_log.write("backend starting...\n")
    backend_log.flush()
    procs["backend"] = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(ROOT / "agent"),
        stdout=backend_log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # Frontend
    print("[start] launching frontend (Vite dev server)...")
    frontend_log = open(ROOT / "logs" / "frontend.log", "w", encoding="utf-8")
    frontend_log.write("frontend starting...\n")
    frontend_log.flush()
    procs["frontend"] = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(ROOT / "ai-chatbox-vue"),
        stdout=frontend_log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # Write state
    state = {name: p.pid for name, p in procs.items()}
    STATE_FILE.write_text(json.dumps(state, indent=2))
    print(f"[start] PID file written to {STATE_FILE}")
    print("[start] backend  →  http://localhost:8000  (logs/logs/backend.log)")
    print("[start] frontend →  http://localhost:5173  (logs/logs/frontend.log)")
    print("[start] use 'python stop.py' to stop both servers.")

    # Wait briefly then check both are alive
    time.sleep(3)
    for name, p in procs.items():
        if p.poll() is not None:
            print(f"[start] WARNING: {name} exited immediately (code {p.returncode}), check logs/")


if __name__ == "__main__":
    (ROOT / "logs").mkdir(exist_ok=True)
    start()
