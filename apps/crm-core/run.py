#!/usr/bin/env python3
"""Chạy CRM Core server dev (PRD-001 / TechSpec-001).

Usage:
    python3 apps/crm-core/run.py            # cổng 8080, DB file crm_core.db
    CRM_DB_PATH=:memory: python3 run.py     # DB in-memory
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from crm.api import create_server  # noqa: E402


def main():
    host = os.environ.get("CRM_HOST", "0.0.0.0")
    port = int(os.environ.get("CRM_PORT", "8080"))
    server = create_server(host=host, port=port)
    print(f"CRM Core listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
