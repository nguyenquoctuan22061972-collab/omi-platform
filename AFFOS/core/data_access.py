"""AFFOS Data Access (PRD-017). Repository over the 21-table model.

Offline store = SQLite (parity cột với AFFOS/core/schema — production = Supabase/Postgres qua
migrate pattern PR-003). Generic insert/query, chuỗi attribution tables. Reuse pattern apps/crm-core/db.
Thuần stdlib, không network.
"""
from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional

# Subset cho chuỗi doanh thu (parity với schema Postgres; đủ để tính profit).
DDL = """
CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, merchant_id TEXT, sku TEXT, title TEXT, price REAL, currency TEXT DEFAULT 'VND');
CREATE TABLE IF NOT EXISTS offers (id TEXT PRIMARY KEY, product_id TEXT, merchant_id TEXT, commission_rate REAL, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, offer_id TEXT, channel_id TEXT, name TEXT, status TEXT DEFAULT 'active', budget REAL);
CREATE TABLE IF NOT EXISTS tracking_links (id TEXT PRIMARY KEY, campaign_id TEXT, offer_id TEXT, slug TEXT, target_url TEXT);
CREATE TABLE IF NOT EXISTS click_events (id TEXT PRIMARY KEY, tracking_link_id TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS conversion_events (id TEXT PRIMARY KEY, click_event_id TEXT, offer_id TEXT, order_value REAL, currency TEXT DEFAULT 'VND', status TEXT DEFAULT 'confirmed', ts TEXT);
CREATE TABLE IF NOT EXISTS commissions (id TEXT PRIMARY KEY, conversion_event_id TEXT, amount REAL, currency TEXT DEFAULT 'VND', status TEXT DEFAULT 'confirmed');
CREATE TABLE IF NOT EXISTS expenses (id TEXT PRIMARY KEY, campaign_id TEXT, category TEXT, amount REAL, currency TEXT DEFAULT 'VND');
"""
CHAIN_TABLES = ["products", "offers", "campaigns", "tracking_links",
                "click_events", "conversion_events", "commissions", "expenses"]


class Repo:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(DDL)
        self.conn.commit()

    def insert(self, table: str, row: Dict) -> None:
        if table not in CHAIN_TABLES:
            raise ValueError(f"table không hợp lệ: {table}")
        cols = ",".join(row.keys())
        ph = ",".join("?" for _ in row)
        self.conn.execute(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({ph})", tuple(row.values()))
        self.conn.commit()

    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
