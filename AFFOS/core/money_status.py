"""AFFOS canonical commission/conversion status (MONEY-01 integrity).

Networks + the seed pipeline use different spellings/cases:
  - AWIN/Impact normalize to UPPER: APPROVED / PENDING / DECLINED / CANCELLED / REFUNDED.
  - the seed pipeline / SQLite default uses lowercase 'confirmed'.
This module defines ONE canonical vocabulary and the rules for what counts as recognized
revenue vs a reversal, so revenue aggregation never silently drops production rows.

Rules (P0-1 / P0-2):
  - CONFIRMED (recognized revenue): APPROVED, CONFIRMED.
  - REFUND (reversal of recognized revenue): REFUNDED, REVERSED.
  - NOT recognized revenue, never summed: PENDING, DECLINED, CANCELLED, REJECTED, DELETED.
  net recognized revenue = Σ confirmed − Σ refund (a refund reverses a prior recognition;
  it is NOT also subtracted a second time as a cost — that was the double-count bug).
"""
from __future__ import annotations

CONFIRMED = {"APPROVED", "CONFIRMED"}
REFUND = {"REFUNDED", "REVERSED"}
NOT_RECOGNIZED = {"PENDING", "DECLINED", "CANCELLED", "CANCELED", "REJECTED", "DELETED"}

# SQL fragment (works in SQLite + Postgres) for a case-insensitive confirmed/refund match.
SQL_CONFIRMED = "UPPER(COALESCE(status,'')) IN ('APPROVED','CONFIRMED')"
SQL_REFUND = "UPPER(COALESCE(status,'')) IN ('REFUNDED','REVERSED')"


def canonical(status: str) -> str:
    return (status or "").strip().upper()


def is_confirmed(status: str) -> bool:
    return canonical(status) in CONFIRMED


def is_refund(status: str) -> bool:
    return canonical(status) in REFUND


def is_recognized_revenue(status: str) -> bool:
    """True only for confirmed revenue — pending/declined/cancelled are never revenue."""
    return canonical(status) in CONFIRMED
