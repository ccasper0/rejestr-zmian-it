"""Stage 6 acceptance scenario through the API (frontend/README.md):
the admin creates company DELTA, sets its categories and roles, the per-category approver;
the DELTA editor adds a CI; the auditor reads and verifies the DELTA chain.

    python -X utf8 tool/e2e_admin_scenario.py [http://localhost:8000/api/v1]

Needs the stack in dev mode (APP_ENV=dev, AUTH_MODE=dev) with the seed. Companies cannot
be deleted (only archived), so DELTA stays in the local database; a second run reuses it
and only repeats the checks.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def expect(result, status, code=None):
    got, body = result
    assert got == status, (got, body)
    if code is not None:
        assert body["code"] == code, body
    return body


def token(external_id):
    return expect(call("POST", "/auth/dev/token", body={"external_id": external_id}), 200)[
        "access_token"
    ]


def step(text):
    print(f"- {text}")


admin, editor = token("dev-admin"), token("dev-editor")
approver, auditor, viewer = token("dev-approver"), token("dev-auditor"), token("dev-viewer")
users = {
    u["email"]: u for u in expect(call("GET", "/users?limit=500", admin), 200)["items"]
}
ewa, jan, alicja = (users[f"{r}@example.com"] for r in ("editor", "approver", "auditor"))

# 1. company
companies = expect(call("GET", "/companies?limit=500", admin), 200)["items"]
delta = next((c for c in companies if c["prefix"] == "DELTA"), None)
if delta is None:
    expect(call("POST", "/companies", admin, {"name": "Delta", "prefix": "DE1"}), 422,
           "company.invalid_data")
    step("422 company.invalid_data dla prefiksu DE1")
    delta = expect(call("POST", "/companies", admin, {
        "name": "Delta sp. z o.o.",
        "prefix": "DELTA",
        "tax_id": "526-025-09-95",
        "is_ksc_entity": False,
        "default_approver_id": jan["id"],
    }), 201)
    step(f"utworzono DELTA ({delta['id']}), NIP znormalizowany: {delta['tax_id']}")
else:
    step("DELTA już istnieje — powtarzam tylko kontrole")
C = f"/companies/{delta['id']}"
expect(call("POST", "/companies", admin, {"name": "delta SP. Z O.O.", "prefix": "DELTB"}), 409,
       "company.name_taken")
step("409 company.name_taken (nazwa bez względu na wielkość liter)")
expect(call("PATCH", C, admin, {"prefix": "DELTB"}), 422, "company.prefix_immutable")
step("422 company.prefix_immutable")
expect(call("POST", "/companies", editor, {"name": "X", "prefix": "XX"}), 403, "auth.forbidden")
step("403 dla editora przy tworzeniu spółki")

# 2. categories (no override yet: DELTA has no approver)
top = {
    c["code"]: c
    for c in expect(call("GET", "/categories?top_level=true&limit=500", admin), 200)["items"]
}
wanted = ["ACC", "FW", "SRV"]
if not companies or delta not in companies:
    # Only for a fresh DELTA: once Jan is its approver this PUT would SUCCEED and
    # withdraw the other categories (a second run must not change the data).
    expect(call("PUT", f"{C}/categories", admin, {"categories": [
        {"category_id": top["FW"]["id"], "approver_override_id": jan["id"]},
    ]}), 422, "company_category.approver_not_eligible")
    step("422 company_category.approver_not_eligible — Jan nie ma jeszcze roli w DELTA")
expect(call("PUT", f"{C}/categories", admin, {"categories": [
    {"category_id": top[code]["id"]} for code in wanted
]}), 200)
step(f"kategorie DELTA: {', '.join(wanted)}")

# 3. roles (full sets)
for user, roles in ((ewa, ["editor"]), (jan, ["approver"]), (alicja, ["auditor"])):
    member = expect(call("PUT", f"{C}/members/{user['id']}", admin, {"roles": roles}), 200)
    step(f"role {user['display_name']}: {member['roles']}")
members = expect(call("GET", f"{C}/members", admin), 200)["items"]
assert {m["display_name"] for m in members} >= {"Ewa Edytorska", "Jan Zatwierdzający"}

# 4. per-category approver (now Jan is an approver of DELTA)
items = expect(call("PUT", f"{C}/categories", admin, {"categories": [
    {"category_id": top[code]["id"],
     "approver_override_id": jan["id"] if code == "FW" else None}
    for code in wanted
]}), 200)["items"]
assert next(i for i in items if i["code"] == "FW")["approver_override_id"] == jan["id"]
step("FW: zatwierdzający kategorii = Jan")

# 5. user detail
detail = expect(call("GET", f"/users/{ewa['id']}", admin), 200)
step("Ewa: " + "; ".join(f"{m['company_prefix']} {m['roles']}" for m in detail["memberships"]))

# 6. the DELTA editor adds a CI
types = {t["code"]: t for t in expect(call("GET", "/ci-types?active=true", editor), 200)["items"]}
existing = expect(call("GET", f"{C}/ci?q=FW-DELTA-01", editor), 200)["items"]
if not existing:
    ci = expect(call("POST", f"{C}/ci", editor, {
        "ci_type_id": types["firewall"]["id"],
        "identifier": "FW-DELTA-01",
        "name": "Zapora brzegowa Delta",
        "owner_user_id": jan["id"],
    }), 201)
    step(f"Ewa dodała CI {ci['identifier']} (właściciel: Jan)")
expect(call("POST", f"{C}/ci", editor, {
    "ci_type_id": types["firewall"]["id"], "identifier": "fw-delta-01", "name": "Duplikat",
}), 409, "ci.identifier_taken")
step("409 ci.identifier_taken (identyfikator bez względu na wielkość liter)")
expect(call("POST", f"{C}/ci", viewer, {
    "ci_type_id": types["firewall"]["id"], "identifier": "X-1", "name": "X",
}), 404, "company.not_found")
step("404 dla Piotra (brak roli w DELTA)")
expect(call("POST", f"{C}/ci", auditor, {
    "ci_type_id": types["firewall"]["id"], "identifier": "X-1", "name": "X",
}), 403, "auth.forbidden")
step("403 dla Alicji (audytor nie zarządza CI)")

# 7. counters
row = next(
    c for c in expect(call("GET", "/companies?limit=500", admin), 200)["items"]
    if c["prefix"] == "DELTA"
)
step(f"liczniki DELTA: {row['counts']}")
assert row["counts"]["active_ci"] >= 1 and row["counts"]["editors"] == 1

# 8. audit: the auditor reads and verifies the DELTA chain
log = expect(call("GET", f"/audit?company_id={delta['id']}&limit=100", auditor), 200)
actions = [f"{e['entity_type']}:{e['action']}" for e in reversed(log["items"])]
step(f"dziennik DELTA ({log['total']}): {', '.join(actions)}")
expect(call("GET", f"/audit?company_id={delta['id']}", editor), 403, "auth.forbidden")
step("403 dla Ewy przy przeglądzie całego dziennika")
verify = expect(call("POST", f"/audit/verify?company_id={delta['id']}", auditor), 200)
assert verify["ok"], verify
step(f"weryfikacja łańcucha DELTA: ok, sprawdzono {verify['checked']} wpisów")
created = expect(call("GET", "/audit?entity_type=company&action=create&limit=500", admin), 200)
assert any(e["entity_id"] == delta["id"] for e in created["items"])
step("łańcuch globalny: wpis company:create dla DELTA")
matrix = expect(call("GET", "/permissions/matrix", viewer), 200)
step(f"macierz uprawnień: {len(matrix['actions'])} akcji")
print("OK")
