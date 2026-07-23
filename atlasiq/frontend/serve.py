"""Simple HTTP server for AtlasIQ frontend.

Run this to serve the static HTML frontend on http://localhost:8501
"""

from __future__ import annotations

import http.server
import os
import socketserver
from pathlib import Path
from typing import Any

PORT = 8502
DIRECTORY = Path(__file__).parent / "static"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self) -> None:
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == "__main__":
    os.chdir(DIRECTORY)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"[+] AtlasIQ Frontend serving at http://localhost:{PORT}")
        print(f"[+] Serving files from {DIRECTORY}")
        print("[+] Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[+] Server stopped")
