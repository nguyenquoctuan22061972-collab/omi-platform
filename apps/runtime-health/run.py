#!/usr/bin/env python3
"""Chạy Runtime Health service (PRD-008 A). Cổng 8082."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from health.api import create_server  # noqa: E402


def main():
    host = os.environ.get("HEALTH_HOST", "0.0.0.0")
    port = int(os.environ.get("HEALTH_PORT", "8082"))
    server = create_server(host=host, port=port)
    print(f"Runtime Health on http://{host}:{port} (/health,/health/live,/health/ready,/version,/build-info)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
