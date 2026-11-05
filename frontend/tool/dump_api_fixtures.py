"""Dumps real responses of the local API as fixtures of test/contract/api_contract_test.dart.

Requires the stack in dev mode with the seed and one run of e2e_api_scenario.py
(a verified change "E2E: ..." with comments). Writes to the local database:
uploads one attachment to that change and creates + cancels one draft.

    python -X utf8 tool/dump_api_fixtures.py [http://localhost:8000/api/v1]
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"
OUT = pathlib.Path(__file__).resolve().parent.parent / "test" / "fixtures" / "api"
OUT.mkdir(parents=True, exist_ok=True)


def call(method, path, token=None, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", ctype)
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


editor, approver = token("dev-editor"), token("dev-approver")
save("dev_users", call("GET", "/auth/dev/users")[1])
_, me = call("GET", "/me", editor)
save("me", me)
cid = next(m for m in me["memberships"] if m["company_prefix"] == "ALFA")["company_id"]
C = f"/companies/{cid}"
save("changes_page", call("GET", f"{C}/changes?limit=10", editor)[1])
save("stats", call("GET", f"{C}/stats", editor)[1])
save("audit_status", call("GET", f"{C}/audit/status", editor)[1])
save("members", call("GET", f"{C}/members", editor)[1])
save("company_categories", call("GET", f"{C}/categories", editor)[1])
top = call("GET", "/categories?top_level=true&limit=500", editor)[1]
save("categories_top", top)
srv = next(c for c in top["items"] if c["code"] == "SRV")
save("categories_sub", call("GET", f"/categories?parent_id={srv['id']}&active=true", editor)[1])
save("ci_page", call("GET", f"{C}/ci?limit=5&active=true", editor)[1])
save("ci_types", call("GET", "/ci-types?active=true", editor)[1])

verified_number = next(
    c["number"]
    for c in call("GET", f"{C}/changes?status=verified&sort=-number&limit=50", editor)[1]["items"]
    if (c["title"] or "").startswith("E2E:")
)
verified = call("GET", f"{C}/changes/by-number/{verified_number}", editor)[1]
# one attachment as evidence, so the list fixture is not empty
boundary = uuid.uuid4().hex
raw = (
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"protokol.txt\"\r\n"
    f"Content-Type: text/plain\r\n\r\nProtokół testu: zażółć gęślą jaźń\r\n--{boundary}--\r\n"
).encode("utf-8")
call("POST", f"{C}/changes/{verified['id']}/attachments", editor, raw=raw,
     ctype=f"multipart/form-data; boundary={boundary}")
save("change_verified", call("GET", f"{C}/changes/by-number/{verified_number}", editor)[1])
save("attachments", call("GET", f"{C}/changes/{verified['id']}/attachments", editor)[1])
save("audit_trail", call("GET", f"{C}/changes/{verified['id']}/audit", editor)[1])

draft_number = next(
    c["number"]
    for c in call("GET", f"{C}/changes?status=draft&limit=50", editor)[1]["items"]
    if c["title"]
)
draft = call("GET", f"{C}/changes/by-number/{draft_number}", editor)[1]
save("change_draft", draft)
save("readiness", call("GET", f"{C}/changes/{draft['id']}/readiness", editor)[1])
save("problem_version_conflict", call(
    "PATCH", f"{C}/changes/{draft['id']}", editor, {"version": 999, "impact": "x"})[1])
save("problem_not_ready", call(
    "POST", f"{C}/changes/{draft['id']}/actions/submit", editor, {"version": draft["version"]})[1])

status, created = call("POST", f"{C}/changes", editor, {})
save("change_created", created)
save("action_result", call(
    "POST", f"{C}/changes/{created['id']}/actions/cancel", editor,
    {"version": created["version"], "comment": "Szkic utworzony do fikstur testów."})[1])
