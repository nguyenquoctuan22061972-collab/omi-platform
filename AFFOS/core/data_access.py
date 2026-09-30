"""AFFOS Data Access (PRD-017 / CTO review). SQLite = TEST/DRY_RUN adapter ONLY.

Production LIVE dùng Postgres/Supabase qua repository.PostgresRepository (interface chung).
Mọi record tài chính/sự kiện mang provenance: source, source_record_id, data_state,
currency, fetched_at, is_verified. Không network.
"""
from __future__ import annotations

import sqlite3
from typing import Dict, List

# Provenance columns có mặt trên các bảng tài chính/sự kiện.
_PROV = ("source TEXT, source_record_id TEXT, data_state TEXT, currency TEXT DEFAULT 'VND', "
         "fetched_at TEXT, is_verified INTEGER DEFAULT 0")

DDL = f"""
CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, merchant_id TEXT, sku TEXT, title TEXT, price REAL, currency TEXT DEFAULT 'VND');
CREATE TABLE IF NOT EXISTS offers (id TEXT PRIMARY KEY, product_id TEXT, merchant_id TEXT, commission_rate REAL, active INTEGER DEFAULT 1, {_PROV});
CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, offer_id TEXT, channel_id TEXT, name TEXT, status TEXT DEFAULT 'active', budget REAL);
CREATE TABLE IF NOT EXISTS tracking_links (id TEXT PRIMARY KEY, campaign_id TEXT, offer_id TEXT, slug TEXT, target_url TEXT);
CREATE TABLE IF NOT EXISTS click_events (id TEXT PRIMARY KEY, tracking_link_id TEXT, ts TEXT, event_subtype TEXT, {_PROV});
CREATE TABLE IF NOT EXISTS conversion_events (id TEXT PRIMARY KEY, click_event_id TEXT, offer_id TEXT, order_value REAL, status TEXT DEFAULT 'confirmed', ts TEXT, event_subtype TEXT, {_PROV});
CREATE TABLE IF NOT EXISTS commissions (id TEXT PRIMARY KEY, conversion_event_id TEXT, amount REAL, status TEXT DEFAULT 'confirmed', {_PROV});
CREATE TABLE IF NOT EXISTS expenses (id TEXT PRIMARY KEY, campaign_id TEXT, category TEXT, amount REAL, {_PROV});
CREATE TABLE IF NOT EXISTS revenue (id TEXT PRIMARY KEY, source_ref TEXT, amount REAL, revenue_label TEXT, {_PROV});
"""
CHAIN_TABLES = ["products", "offers", "campaigns", "tracking_links",
                "click_events", "conversion_events", "commissions", "expenses", "revenue"]
# Bảng có cột provenance (bắt buộc data_state khi insert).
PROV_TABLES = {"offers", "click_events", "conversion_events", "commissions", "expenses", "revenue"}
_SQLITE_STATES = {"TEST", "DRY_RUN", "SEEDED"}


class Repo:
    """SQLite adapter — CHỈ TEST/DRY_RUN/SEEDED. LIVE phải dùng PostgresRepository."""

    def __init__(self, path: str = ":memory:", data_state: str = "DRY_RUN"):
        if data_state not in _SQLITE_STATES:
            raise ValueError(f"SQLite chỉ cho {_SQLITE_STATES}, không {data_state}")
        self.data_state = data_state
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(DDL)
        self.conn.commit()

    def insert(self, table: str, row: Dict) -> None:
        if table not in CHAIN_TABLES:
            raise ValueError(f"table không hợp lệ: {table}")
        if table in PROV_TABLES:
            ds = row.get("data_state")
            if ds is None:
                raise ValueError(f"{table}: thiếu provenance.data_state (CTO rule)")
            if ds not in _SQLITE_STATES:
                raise ValueError(f"SQLite adapter từ chối data_state={ds} (LIVE phải dùng Postgres)")
        cols = ",".join(row.keys())
        ph = ",".join("?" for _ in row)
        self.conn.execute(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({ph})", tuple(row.values()))
        self.conn.commit()

    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def count(self, table: str) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
