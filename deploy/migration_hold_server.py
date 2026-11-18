"""Minimal health endpoint used while the Render disk is being restored."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/health":
            status = 200
            payload = {"status": "migration_hold", "database_ready": False}
        else:
            status = 503
            payload = {"detail": "Staging database restore in progress"}

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("migration-hold:", fmt % args, flush=True)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8006"))
    print(f"Migration hold server listening on 0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
