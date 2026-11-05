"""Dumps real report responses (Etap 7, ADR 0017) as fixtures of test/contract.

Requires the stack in dev mode with the seed (backend with /reports). Writes to the
local database: one register report (auditor, ALFA, October 2026) and one change card
(editor) - both are numbered and audited like every export.

    python -X utf8 tool/dump_report_fixtures.py [http://localhost:8000/api/v1]

Not dumped (cannot be produced on the seed data without changing the API settings):
``report_pending.json`` (needs more than REPORT_ASYNC_THRESHOLD = 200 changes) and
``problem_report_too_large.json`` (needs more than REPORT_MAX_CHANGES = 5000) - those
fixtures are written by hand after backend/app/schemas/reports.py and app/errors.py.
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"
OUT = pathlib.Path(__file__).resolve().parent.parent / "test" / "fixtures" / "api"
OUT.mkdir(parents=True, exist_ok=True)


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def save(name, payload):
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    (OUT / f"{name}.json").write_text(text, encoding="utf-8", newline="\n")
    print("saved", name)


def token(ext):
    return call("POST", "/auth/dev/token", body={"external_id": ext})[1]["access_token"]


auditor, editor = token("dev-auditor"), token("dev-editor")
_, me = call("GET", "/me", auditor)
cid = next(m for m in me["memberships"] if m["company_prefix"] == "ALFA")["company_id"]

status, report = call("POST", "/reports", auditor, {
    "kind": "register",
    "company_id": cid,
    "period_from": "2026-09-30T22:00:00Z",
    "period_to": "2026-11-01T23:00:00Z",
    "filters": {"period_by": "created", "status": [], "type": []},
    "include_audit_trail": True,
})
assert status in (201, 202), (status, report)
save("report_done", report)

change = call("GET", f"/companies/{cid}/changes?limit=1", editor)[1]["items"][0]
status, card = call("POST", "/reports", editor, {
    "kind": "change_card", "company_id": cid, "change_id": change["id"],
})
assert status in (201, 202), (status, card)

save("reports_page", call("GET", f"/reports?company_id={cid}&limit=20", auditor)[1])
