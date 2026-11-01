#!/usr/bin/env python3
"""Serve the static Kindred hero on the Webdev runtime port."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
import os

ROOT = Path(__file__).parent / "public"
PORT = int(os.environ.get("PORT", "3000"))
handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
print(f"Serving {ROOT} at http://0.0.0.0:{PORT}")
ThreadingHTTPServer(("0.0.0.0", PORT), handler).serve_forever()
