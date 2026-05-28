"""Stop all servers started by start.py."""
import json
import os
import signal
from pathlib import Path

ROOT = Path(__file__).parent
STATE_FILE = ROOT / ".server_state.json"


def stop():
    if not STATE_FILE.exists():
        print("[stop] no .server_state.json found — nothing to stop.")
        return

    state = json.loads(STATE_FILE.read_text())
    for name, pid in state.items():
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"[stop] {name} (PID {pid}) terminated.")
        except OSError:
            print(f"[stop] {name} (PID {pid}) already gone.")
        except Exception as e:
            print(f"[stop] {name} (PID {pid}) error: {e}")

    STATE_FILE.unlink()
    print("[stop] all servers stopped.")


if __name__ == "__main__":
    stop()
