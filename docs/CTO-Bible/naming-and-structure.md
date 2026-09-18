# Naming Convention & Folder Structure — OMI Platform

Chuẩn hoá đặt tên & cấu trúc (bổ sung cho `standards.md`).

## 1. Folder structure (repo)
```
omi-platform/
├── docs/
│   ├── PRD/            PRD-<nnn>.md
│   ├── TechSpec/       <Module>.md
│   ├── Database/       <Module>-schema.md
│   ├── API/            <Module>-api.md
│   ├── Architecture/   <Module>-flows.md (sequence/data-flow)
│   ├── Operations/     <Module>-runbook.md
│   ├── QA/             <Module>-checklist.md, QA-<nnn>.md
│   ├── CTO-Bible/      standards, capability-map, naming-and-structure, adr/
│   ├── Product/ Research/ Roadmap/ SOP/ Security/ Deployment/
├── apps/<module>/      src/, tests/, run.py, requirements.txt, README.md
├── workflows/<WFnnn>/  workflow.json, README.md
└── workflows/tests/    validator
```

## 2. Naming
| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| PRD | `PRD-<nnn>.md` | PRD-003.md |
| TechSpec/DB/API | `<Module>[-schema|-api].md` | Auth-RBAC-api.md |
| App/service | `apps/<kebab>/` | apps/auth-rbac |
| Python module | snake_case | jwt_util.py |
| Test | `test_<chủ_đề>.py` | test_rbac.py |
| n8n workflow | `WF<nnn>` + `workflow.json` | WF001/workflow.json |
| n8n node | Tiếng Anh, Title Case, động từ | "Create Contact" |
| Env var | UPPER_SNAKE | CRM_BASE, N8N_BASE_URL |
| Biến JSON expression | `{{$env.<VAR>}}` | {{$env.CRM_BASE}} |

## 3. Commit (nhắc lại — luật #5)
`<type>(<module>): <mô tả>` — 1 module/commit. type ∈ feat/fix/docs/test/refactor/chore.

## 4. Workflow ID node
`id` = `<wf><số>-<slug>` (vd `wf001-create-contact`) — ổn định để diff/rollback.

## 5. Nguyên tắc secret
Không literal secret trong repo. Runtime: `{{$env.*}}` + credential n8n. Node cần
secret → `disabled` cho tới khi gắn.
