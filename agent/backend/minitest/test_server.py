#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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