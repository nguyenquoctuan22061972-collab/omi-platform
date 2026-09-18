#!/usr/bin/env python3
"""Chạy Auth & RBAC server dev (PRD-002 / TechSpec Auth-RBAC).

    AUTH_SECRET=... python3 apps/auth-rbac/run.py     # cổng 8081
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from api import create_server  # noqa: E402


def main():
    host = os.environ.get("AUTH_HOST", "0.0.0.0")
    port = int(os.environ.get("AUTH_PORT", "8081"))
    server = create_server(host=host, port=port)
    print(f"Auth & RBAC listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
