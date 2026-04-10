#!/usr/bin/env python3
"""Start the FontDock server."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9998,
        reload=True,
        reload_dirs=["app"],
    )
