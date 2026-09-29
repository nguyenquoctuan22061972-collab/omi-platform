# AFFOS Constitution

Luật bất biến cho mọi thay đổi trong AFFOS.

1. **Reuse > Additive > No-Fork.** Mọi module bind vào code đã có (xem `affos.manifest.json`); không sao chép/nhánh hoá.
2. **Không đổi PRD/ADR/Capability Map/naming đã khoá.**
3. **Secret env-only.** Không commit token/key; adapter dry-run tới khi có credential.
4. **4-Gate QA** mỗi thay đổi: Architecture · Regression · Security · Production Safety.
5. **Trượt Gate → tự rollback → tự sửa → test lại.** Ghi QA History + Rollback Log.
6. **Production an toàn:** không sửa `apps/`, `deploy/`, workflow production khi chưa qua QA.
7. **Permission Request** chỉ khi thiếu credential ngoài (API key, token, OAuth, domain, account).
