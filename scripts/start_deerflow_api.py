"""
Launcher script for ViVy Deerflow API.
Starts a uvicorn server serving the OpenAI-compatible endpoints.
"""

import os
import sys
import uvicorn
import logging

# Ensure src is in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ViVy-Deerflow")

def start_server(host: str = "0.0.0.0", port: int = 8000):
    logger.info(f"Starting ViVy 70B MoE (Auxiliary) for Deerflow on http://{host}:{port}")
    logger.info("Endpoints:")
    logger.info(f" - POST http://{host}:{port}/v1/chat/completions (OpenAI compatible)")
    logger.info(f" - GET  http://{host}:{port}/health")
    
    # We use import string to point uvicorn to the app object
    uvicorn.run("vivy.api.deerflow_server:app", host=host, port=port, reload=True, reload_dirs=[os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))])

if __name__ == "__main__":
    start_server()
