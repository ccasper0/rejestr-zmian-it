"""Stage 5 acceptance scenario through the API (frontend/README.md):
draft -> PATCH (stale version = 409) -> submit without rollback plan (422)
-> submit -> four eyes (403) -> approve -> implement -> verify -> audit trail.

    python -X utf8 tool/e2e_api_scenario.py [http://localhost:8000/api/v1]

Needs the stack in dev mode (APP_ENV=dev, AUTH_MODE=dev) with the seed.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"


def call(method, path, token=None, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def token(external_id):
    status, body = call("POST", "/auth/dev/token", body={"external_id": external_id})
    assert status == 200, body
    return body["access_token"]


editor, approver = token("dev-editor"), token("dev-approver")
_, me = call("GET", "/me", editor)
alfa = next(m for m in me["memberships"] if m["company_prefix"] == "ALFA")
cid = alfa["company_id"]
_, me_approver = call("GET", "/me", approver)

# 1. draft (number right away)
status, draft = call("POST", f"/companies/{cid}/changes", editor, {})
print("1. draft", status, draft["number"], draft["status"], "v", draft["version"])
_, cats = call("GET", f"/companies/{cid}/categories", editor)
fw = next(c for c in cats["items"] if c["code"] == "FW")
_, cis = call("GET", f"/companies/{cid}/ci?limit=5&active=true", editor)
ci = cis["items"][0]

# 2. fill in (PATCH with version), high risk
start = datetime.now(UTC) + timedelta(days=2)
status, change = call(
    "PATCH",
    f"/companies/{cid}/changes/{draft['id']}",
    editor,
    {
        "version": draft["version"],
        "title": "E2E: reguła zapory dla serwera WWW",
        "category_id": fw["category_id"],
        "change_type": "normal",
        "risk": "high",
        "description": "Otwarcie portu 443 — test scenariusza E2E.",
        "implementation_plan": "1. Kopia konfiguracji. 2. Reguła. 3. Test.",
        "assignee_id": me["id"],
        "approver_id": me_approver["id"],
        "verifier_id": me_approver["id"],
        "requirement_ref": "ISO/IEC 27001:2022 A.8.32",
        "ticket_ref": "SD-E2E",
        "ci_ids": [ci["id"]],
        "window_start": start.isoformat(),
        "window_end": (start + timedelta(hours=2)).isoformat(),
    },
)
print("2. patch", status, "v", change.get("version"))
_, ready = call("GET", f"/companies/{cid}/changes/{draft['id']}/readiness", editor)
print("   readiness ok =", ready["ok"], [c["code"] for c in ready["checks"] if not c["ok"]])

# stale version -> 409
status, problem = call(
    "PATCH", f"/companies/{cid}/changes/{draft['id']}", editor, {"version": 1, "impact": "x"}
)
print("   stale PATCH ->", status, problem.get("code"), "current", problem.get("current_version"))

# rollback plan missing at high risk -> submit 422
status, problem = call(
    "POST", f"/companies/{cid}/changes/{draft['id']}/actions/submit", editor,
    {"version": change["version"]},
)
print("3a. submit without rollback plan ->", status, problem.get("code"))
status, change = call(
    "PATCH", f"/companies/{cid}/changes/{draft['id']}", editor,
    {"version": change["version"], "rollback_plan": "Przywrócenie kopii konfiguracji."},
)
status, result = call(
    "POST", f"/companies/{cid}/changes/{draft['id']}/actions/submit", editor,
    {"version": change["version"]},
)
print("3. submit", status, result.get("from_status"), "->", result.get("to_status"))
change = result["change"]

# four eyes: editor cannot approve
status, problem = call(
    "POST", f"/companies/{cid}/changes/{draft['id']}/actions/approve", editor,
    {"version": change["version"]},
)
print("   editor approve ->", status, problem.get("code"))

_, card = call("GET", f"/companies/{cid}/changes/by-number/{change['number']}", approver)
print("   approver allowed_actions:", card["allowed_actions"])
status, result = call(
    "POST", f"/companies/{cid}/changes/{draft['id']}/actions/approve", approver,
    {"version": card["version"], "comment": "Zatwierdzam."},
)
print("4. approve", status, result.get("to_status"), "approved_by", result["change"]["approved_by"])
change = result["change"]

_, card = call("GET", f"/companies/{cid}/changes/by-number/{change['number']}", editor)
print("   editor allowed_actions:", card["allowed_actions"])
status, result = call(
    "POST", f"/companies/{cid}/changes/{draft['id']}/actions/implement", editor,
    {"version": card["version"]},
)
print("5. implement", status, result.get("to_status"), "warnings", [w["code"] for w in result["warnings"]])

_, card = call("GET", f"/companies/{cid}/changes/by-number/{change['number']}", approver)
status, result = call(
    "POST", f"/companies/{cid}/changes/{draft['id']}/actions/verify", approver,
    {"version": card["version"]},
)
print("6. verify", status, result.get("to_status"))

_, audit = call("GET", f"/companies/{cid}/changes/{draft['id']}/audit", editor)
print("7. audit entries:", audit["total"], [
    (e["action"], e["context"].get("action"), e["hash_valid"]) for e in audit["items"]
])
print("   number:", change["number"])
