"""Dumps the real response of creating a correction (ADR 0021) as a contract fixture.

Requires the stack in dev mode with the seed. Writes to the local database: creates
one correction draft of a verified ALFA change (body as built by the frontend's
``ChangeCorrection.draftFields``) and cancels it.

    python -X utf8 tool/dump_correction_fixture.py [http://localhost:8000/api/v1]
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"
OUT = pathlib.Path(__file__).resolve().parent.parent / "test" / "fixtures" / "api"


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


editor = call("POST", "/auth/dev/token", body={"external_id": "dev-editor"})[1]["access_token"]
me = call("GET", "/me", editor)[1]
cid = next(m for m in me["memberships"] if m["company_prefix"] == "ALFA")["company_id"]
C = f"/companies/{cid}"
summary = call("GET", f"{C}/changes?status=verified&limit=1", editor)[1]["items"][0]
original = call("GET", f"{C}/changes/{summary['id']}", editor)[1]


def ref_id(value):
    return value["id"] if value else None


body = {
    "supersedes_change_id": original["id"],
    "title": "Korekta: " + (original["title"] or original["number"]),
    "category_id": ref_id(original["category"]),
    "subcategory_id": ref_id(original["subcategory"]),
    "change_type": original["change_type"],
    "risk": original["risk"],
    "description": original["description"],
    "implementation_plan": original["implementation_plan"],
    "rollback_plan": original["rollback_plan"],
    "impact": original["impact"],
    "requirement_ref": original["requirement_ref"],
    "ticket_ref": original["ticket_ref"],
    "assignee_id": ref_id(original["assignee"]),
    "approver_id": ref_id(original["approver"]),
    "verifier_id": ref_id(original["verifier"]),
    "ci_ids": [ci["id"] for ci in original["ci"]],
}
body = {k: v for k, v in body.items() if v not in (None, "", [])}
status, created = call("POST", f"{C}/changes", editor, body)
assert status == 201, (status, created)
assert created["supersedes_change_id"] == original["id"]
save("change_correction", created)
# re-read: the original now lists the correction in superseded_by
save("change_correction_original", call("GET", f"{C}/changes/{original['id']}", editor)[1])
call("POST", f"{C}/changes/{created['id']}/actions/cancel", editor,
     {"version": created["version"], "comment": "Korekta utworzona do fikstur testów."})
