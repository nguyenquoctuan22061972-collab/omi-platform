# CEO Live Dashboard — Spec (PRD-008 H)

> Mở rộng spec (không sửa Dashboard KPI PRD-004, không sửa CEO-Command-Center). Đây là
> thiết kế cho màn "live" tương lai, nguồn dữ liệu từ observability (libs/metrics + health).

## Widget
| Widget | Nguồn | Trạng thái |
|---|---|---|
| **Revenue** (placeholder) | pipeline `won` × giá trị (mock) | placeholder — chờ dữ liệu doanh thu thật |
| **Workflow health** | `workflows/runtime/validate.py` + metrics `workflow_count` | mock/dry-run |
| **Inbox health** | inbox adapters `configured` + queue_size | mock |
| **Pipeline health** | pipeline deals theo stage | mock |
| **Deployment timeline** | Operations `deploys` + `deploy/.last_good_tag` | mock |
| **Health summary** | `apps/runtime-health` `/health` | live khi service chạy |

## Executive KPI mapping
| KPI điều hành | Nguồn kỹ thuật |
|---|---|
| Doanh thu (ước) | pipeline won × ARPU (placeholder) |
| Tăng trưởng lead | CRM `total_contacts` (CR-001 `/dashboard/kpi`) |
| Hiệu suất bán | `win_rate` |
| Độ ổn định hệ thống | runtime-health `/health` + metrics `health_summary` |
| Tự động hoá | workflow activation report (bao nhiêu WF đang bật) |

## Nguyên tắc
- Chỉ **spec + nguồn dữ liệu**; không sửa KPI dashboard hiện có.
- Live data lấy qua observability layer (metrics/health) — không hardcode, không secret.
- Revenue là **placeholder** tới khi có nguồn doanh thu chính thức.

## Layout đề xuất (desktop)
```
[ Revenue* ] [ Lead growth ] [ Win rate ] [ Health summary ]
[ Workflow health ....... ] [ Inbox health ] [ Pipeline health ]
[ Deployment timeline ................................. ]
```
(* placeholder)
