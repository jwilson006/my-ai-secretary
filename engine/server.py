import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from engine import scheduler, world_clock, agent

DASHBOARD_PATH = Path(__file__).parent.parent / "dashboard" / "index.html"
WORLD_DIR = Path(__file__).parent.parent / "world"
PORT = 3000


class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Silence default request logging

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, content):
        body = content.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            with open(DASHBOARD_PATH) as f:
                self.send_html(f.read())

        elif path == "/api/world":
            clock = world_clock.load_clock()
            with open(WORLD_DIR / "config" / "world.json") as f:
                world = json.load(f)
            self.send_json({
                "world": world,
                "clock": clock,
                "time_label": world_clock.get_time_label(),
                "running": scheduler.is_running()
            })

        elif path == "/api/agents":
            agents_data = {}
            for aid in agent.AGENT_IDS:
                profile = agent.load_profile(aid)
                state = agent.load_state(aid)
                agents_data[aid] = {**profile, **state}
            self.send_json(agents_data)

        elif path == "/api/feed":
            log_path = WORLD_DIR / "logs" / "activity_feed.json"
            try:
                with open(log_path) as f:
                    feed = json.load(f)
            except Exception:
                feed = []
            self.send_json(feed[:50])

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path == "/api/start":
            scheduler.start()
            self.send_json({"status": "started"})

        elif path == "/api/stop":
            scheduler.stop()
            self.send_json({"status": "stopped"})

        elif path == "/api/task":
            agent_id = body.get("agent_id")
            task = body.get("task")
            if agent_id and task and agent_id in agent.AGENT_IDS:
                agent.assign_task(agent_id, task)
                self.send_json({"status": "assigned", "agent": agent_id, "task": task})
            else:
                self.send_json({"error": "invalid agent_id or task"}, 400)

        elif path == "/api/reset":
            world_clock.reset()
            self.send_json({"status": "reset"})

        else:
            self.send_response(404)
            self.end_headers()


def run():
    httpd = HTTPServer(("localhost", PORT), Handler)
    print(f"[Server] Cedarbrook running at http://localhost:{PORT}")
    httpd.serve_forever()
