#!/usr/bin/env python3
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

import uvicorn
from backend.main import app

if __name__ == "__main__":
    print("Starting test server on port 8001...")
    print("Log level: debug")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="debug"
    )