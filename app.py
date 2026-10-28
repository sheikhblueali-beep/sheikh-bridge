import asyncio
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))
os.chdir(os.path.join(os.path.dirname(__file__), 'bot'))

from main import main as bot_main

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_bot():
    asyncio.run(bot_main())

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"Web server running on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    run_web()
