"""Dumps real responses of the admin, CI and audit-log endpoints (stage 6) as fixtures of
test/contract/api_contract_test.dart.

Requires the stack in dev mode with the seed. Writes to the local database only one audit
entry: the chain verification of ALFA (POST /audit/verify, an audited operation).
The 409 of a duplicate company name is rejected before anything is written.

    python -X utf8 tool/dump_admin_fixtures.py [http://localhost:8000/api/v1]
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


def ok(result, expected=200):
    status, payload = result
    if status != expected:
        raise SystemExit(f"unexpected {status}: {payload}")
    return payload


def save(name, payload):
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    (OUT / f"{name}.json").write_text(text, encoding="utf-8", newline="\n")
    print("saved", name)


def token(ext):
    return ok(call("POST", "/auth/dev/token", body={"external_id": ext}))["access_token"]


admin, auditor = token("dev-admin"), token("dev-auditor")
companies = ok(call("GET", "/companies?limit=500", admin))
save("companies_admin", {**companies, "items": companies["items"][:5]})
alfa = next(c for c in companies["items"] if c["prefix"] == "ALFA")

users = ok(call("GET", "/users?limit=5", admin))
save("users_page", users)
editor = ok(call("GET", "/users?q=editor@example.com", admin))["items"][0]
save("user_detail", ok(call("GET", f"/users/{editor['id']}", admin)))
save("permission_matrix", ok(call("GET", "/permissions/matrix", admin)))
save("categories_all", ok(call("GET", "/categories?limit=500", admin)))

save("audit_page", ok(call("GET", f"/audit?company_id={alfa['id']}&limit=10", auditor)))
save("audit_global_page", ok(call("GET", "/audit?limit=10", admin)))
save("verify_result", ok(call("POST", f"/audit/verify?company_id={alfa['id']}", auditor)))

status, problem = call("POST", "/companies", admin, {"name": alfa["name"], "prefix": "ZZZZZZZZ"})
assert status == 409, (status, problem)
save("problem_company_name_taken", problem)
