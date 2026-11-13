# ADR-0004 — Hybrid Revenue Architecture (Option C)

- **Status:** Accepted (Design) — **KHÔNG phải Build authorization.** Mỗi work package cần CEO Build approval riêng.
- **Date:** 2026-11-12
- **Authority:** CEO (decisions locked) · Coordinator: CTO · Builder: Claude
- **Supersedes/relates:** ADR-0001 (crm-core), ADR-0002 (n8n), ADR-0003 (deployment) — additive, không thay thế.

## Context

Repo có hai mặt phẳng song song cho doanh thu (xem reconciliation Phase 1–4.3):
- **Platform Plane** — `apps/` (auth-rbac, crm-core, content-factory, runtime-health, dashboard), `libs/`,
  `orchestrator/runtime` (queue/worker), `zalo-ai-company/ceo-console`. Được quản trị bởi PRD-001..012,
  `capability-map.md`, `naming-and-structure.md`, `affos.manifest.json`.
- **AFFOS Revenue Plane** — `AFFOS/` (core/, runtime/, connectors/): revenue API + approval + provenance +
  cost-ledger + durable store. Chín về vận hành nhưng trước ADR này **không** có trong tài liệu quản trị.

Quyết định kiến trúc: **Hybrid Option C** — giữ AFFOS làm revenue-domain service; Platform Plane sở hữu
Auth-RBAC, CEO Console, Hub/Queue, Worker, Runtime Health. Hợp thức hoá AFFOS qua ADR + manifest metadata
(additive), **không** di dời code (PA A), **không** nhân bản runtime hiện có.

## Decisions (D1–D8, CEO-locked)

| # | Decision | Trạng thái code |
|---|---|---|
| **D1** | Revenue delivery = **Outbox table trên AFFOS Postgres**; at-least-once + Idempotency-Key dedup. | **[P]** chưa có bảng/dispatcher |
| **D2** | Worker = **service principal chỉ `revenue:ingest`** (không read/approve/revoke). | **[P]** role chưa tồn tại |
| **D3** | Approval binding: `approval_id` gắn với `execution_id`; lease/fencing/version; re-check revocation **ngay trước provider authorization gate**. KHÔNG giữ DB lock qua provider network call. | **[P]** hiện `is_approved` boolean (`AFFOS/runtime/revenue_api.py` `is_approved`) |
| **D4** | **Distributed rate-limit bắt buộc trước LIVE** (hiện process-local). | **[P]** (`revenue_api.py` `_rate_limited`) |
| **D5** | **Reconciliation bảo vệ external side-effect** — read-only, manual-first, không auto-sửa. | **[V]** chỉ read-only/manual (`AFFOS/runtime/revenue_report.py` `reconcile`); AMBIGUOUS + xử lý outcome bất định = **[P]** |
| **D6** | **Separate HS256 service signing key** (`AFFOS_SERVICE_JWT_SECRET`), độc lập user `AUTH_SECRET`. | **[P]** hiện 1 key |
| **D7** | **Dispatcher chạy trong `affos-runtime`**, module riêng + DB permission riêng (`affos_service`, RLS). | **[P]** module chưa có; RLS affos_service **[V]** `AFFOS/core/schema/0005_ingest_store_policies.sql` |
| **D8** | **Manual-first reconciliation** — người xác nhận trước khi bất kỳ hành động tự động. | **[V]** reconcile hiện manual/read-only |

### D3 — Approval semantics (clarification, CTO review C1)

Thiết kế [P] phải bảo toàn, và KHÔNG được phát biểu quá mức:
- `approval_id` **bound to `execution_id`** (mỗi lần thực thi gắn đúng một approval).
- **Lease / fencing / version** semantics để chống thực thi cũ/đồng thời.
- **KHÔNG giữ database lock qua provider network call** (lock chỉ trong tx cục bộ, nhả trước khi gọi mạng).
- **Re-check revocation ngay trước provider authorization gate** (điểm quyết định cuối trước side-effect).
- Một khi external side-effect đã bắt đầu, **KHÔNG đảm bảo huỷ (cancellation) được**.
- **Không tuyên bố** atomic cancellation của external side-effect; an toàn dựa trên dedup (Idempotency-Key)
  + reconciliation, không phải rollback mạng.

### D5 — Reconciliation maturity (clarification, CTO review C2)

- **Verified [V]** chỉ trong phạm vi code hiện có: reconciliation **read-only, manual-first** không mutate
  source records (`revenue_report.py` `reconcile`; bucket qua `money_status`).
- **Planned [P]:** trạng thái **AMBIGUOUS** và xử lý an toàn các provider-outcome bất định — chưa triển khai,
  chưa verify độc lập.
- **Manual-first** được giữ nguyên (D8): người xác nhận trước mọi hành động tự động.
- **Không tuyên bố exactly-once external delivery.** Outbox (D1) chỉ cung cấp at-least-once; dedup là
  Idempotency-Key; reconciliation là lớp phát hiện lệch, không phải bảo đảm giao nhận.

## Classification of the Revenue Plane

- **Implemented [V]** (có code + test): `revenue_api.py` (POST ingest/approve/approve-revoke, GET
  report/reconcile), durable approval+idempotency (`revenue_store.py`), cost-ledger (`cost_ledger.py`),
  provenance/proof/attribution (`core/`), awin+impact connectors (`connectors/`). JWT verify reuse
  `apps/auth-rbac`.
- **Proposed [P]** (ADR-approved, chưa triển khai): Outbox+dispatcher (D1/D7), RevenueIngestService role
  (D2), Dedicated Service Issuer + separate key (D2/D6), approval_id claim/lease (D3), distributed
  rate-limit (D4), reconciliation AMBIGUOUS state (D5/D8).
- **Blocked [B]** (cần CEO/operator, live-action): áp migration 0004/0005 trên host; cấp secrets
  (`AFFOS_SERVICE_JWT_SECRET`, prod `AFFOS_JWT_ISS/AUD`); cơ chế cấp quyền gọi Dedicated Service Issuer +
  secret-store integration; staging-host validation; đưa affos-runtime vào prod compose (EVALUATE).

## Consequences

- Governance được đồng bộ: `affos.manifest.json` + `company.manifest.json` thêm metadata top-level
  `revenue_plane` (chỉ metadata, **không** đọc bởi Command Center/runtime; **không** đổi 26 modules /
  9 departments); `capability-map.md` tách Implemented vs Planned; `naming-and-structure.md` công nhận
  `AFFOS/` top-level (PA A).
- Không tạo kiến trúc thứ hai: tái dùng `affos-runtime`/`revenue_api`/`revenue_store` hiện có.
- Mỗi hạng mục [P]/[B] triển khai qua PR nhỏ, 4-Gate QA, CEO Build approval riêng. Không LIVE trong ADR này.

## Constraints giữ nguyên (locked)

Reuse > Additive > No-Fork; không đổi PRD/ADR/Capability-Map/naming đã khoá ngoài phạm vi additive này;
secret env-only; 4-Gate QA; production an toàn. CRM = HOLD. Blueprint v1.1 = BLOCKED (không suy diễn).
Prod compose = EVALUATE ONLY.
