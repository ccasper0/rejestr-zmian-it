"""Consistency of the deployment configuration (ADR 0019): nginx templates, the web
image, docker-compose.yml, .env.example and the backup scripts. Static checks - the
behaviour (headers, 429/413 problem+json) is exercised by the docker-compose job in
CI; the age-encrypted backup/restore round trip was verified manually (ADR 0019 §10)."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "deploy" / "nginx" / "templates"
WEB_DOCKERFILE = ROOT / "frontend" / "Dockerfile"
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"
SCRIPTS = ROOT / "scripts"
BACKUP_SH = SCRIPTS / "backup.sh"
BACKUP_PS1 = SCRIPTS / "backup.ps1"
RESTORE_SH = SCRIPTS / "restore.sh"
RESTORE_PS1 = SCRIPTS / "restore.ps1"
BACKUP_LOOP = ROOT / "deploy" / "backup" / "backup-loop.sh"
BACKUP_DOCKERFILE = ROOT / "deploy" / "backup" / "Dockerfile"
BACKUP_HEALTHCHECK = ROOT / "deploy" / "backup" / "healthcheck.sh"

pytestmark = pytest.mark.skipif(
    not TEMPLATES.is_dir(), reason="repository layout not available (e.g. inside an image)"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _templates() -> dict[str, str]:
    return {p.relative_to(TEMPLATES).as_posix(): _read(p) for p in TEMPLATES.rglob("*.template")}


def _template_variables() -> set[str]:
    found: set[str] = set()
    for text in _templates().values():
        found |= set(re.findall(r"\$\{(NGINX_[A-Z0-9_]+)\}", text))
    return found


def test_every_template_variable_has_a_default_in_the_image_and_compose() -> None:
    variables = _template_variables()
    assert variables  # sanity
    dockerfile = _read(WEB_DOCKERFILE)
    compose = _read(COMPOSE)
    env_example = _read(ENV_EXAMPLE)
    for name in variables:
        # Unset variables are NOT substituted by the nginx entrypoint (envsubst filter):
        # a missing default would leave "${NAME}" in the config and nginx would not start.
        assert re.search(rf"\b{name}=", dockerfile), f"{name}: no ENV default in the web image"
        assert f"{name}:" in compose, f"{name}: not passed to the web service"
        if name != "NGINX_CSP_CONNECT_EXTRA":  # derived from WEB_API_URL
            assert re.search(rf"^{name}=", env_example, re.M), f"{name}: not in .env.example"


def test_envsubst_is_restricted_to_nginx_variables() -> None:
    # nginx's own $variables ($request_id, $remote_addr, ...) must never be substituted.
    assert 'NGINX_ENVSUBST_FILTER="^NGINX_"' in _read(WEB_DOCKERFILE)


def test_locations_with_add_header_include_the_security_headers() -> None:
    """add_header in a location drops ALL inherited add_header directives."""
    conf = _templates()["default.conf.template"]
    blocks = re.findall(r"location\s+[^{]+\{(.*?)\n    \}", conf, re.S)
    assert blocks
    for body in blocks:
        if "add_header" in body or "api-proxy.inc" in body:
            assert "security-headers.inc" in body or "api-proxy.inc" in body, body
    proxy = _templates()["snippets/api-proxy.inc.template"]
    assert "security-headers.inc" in proxy


def test_api_locations_keep_problem_json_error_pages() -> None:
    """error_page is not inherited into a location that declares its own."""
    proxy = _templates()["snippets/api-proxy.inc.template"]
    for directive in (
        "error_page 429 @rate_limited;",
        "error_page 413 @too_large;",
        "@api_unavailable;",
    ):
        assert directive in proxy


def test_rate_limited_response_is_problem_json() -> None:
    conf = _templates()["default.conf.template"]
    block = conf[conf.index("location @rate_limited") :]
    block = block[: block.index("\n    }")]
    assert "application/problem+json" in block
    assert '"code":"request.rate_limited"' in block
    assert "return 429" in block
    assert "limit_req_status 429;" in conf


def test_client_supplied_forwarded_for_is_replaced_not_appended() -> None:
    proxy = _templates()["snippets/api-proxy.inc.template"]
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in proxy
    assert "$proxy_add_x_forwarded_for" not in proxy.split("#")[0]
    assert "0.0.0.0/0" not in _read(COMPOSE)


def test_forwarded_proto_is_taken_only_from_a_trusted_proxy() -> None:
    """ADR 0019 §11: behind a TLS proxy the API must see https, but a direct client
    must not be able to claim it with its own X-Forwarded-Proto."""
    conf = _templates()["default.conf.template"]
    proxy = _templates()["snippets/api-proxy.inc.template"]
    assert "proxy_set_header X-Forwarded-Proto $forwarded_proto;" in proxy
    assert "X-Forwarded-Proto $scheme" not in proxy
    assert "$http_x_forwarded_proto" not in _code(proxy)  # never passed through as is

    # Trust is decided on the TCP peer BEFORE realip rewrote $remote_addr, using the
    # same list as realip.
    geo = re.search(r"geo \$realip_remote_addr \$from_trusted_proxy \{(.*?)\n\}", conf, re.S)
    assert geo, "geo block on $realip_remote_addr missing"
    entries = [line.split() for line in _code(geo.group(1)).splitlines() if line.strip()]
    assert ["default", "0;"] in entries
    assert ["${NGINX_TRUSTED_PROXIES}", "1;"] in entries
    assert len(entries) == 2

    proto = re.search(
        r'map "\$from_trusted_proxy:\$http_x_forwarded_proto" \$forwarded_proto \{(.*?)\n\}',
        conf,
        re.S,
    )
    assert proto, "map $forwarded_proto missing"
    rules = {
        parts[0].strip('"'): parts[1].rstrip(";")
        for parts in (line.split() for line in _code(proto.group(1)).splitlines())
        if parts
    }
    # Only the trusted flag "1:" may select the forwarded value; everything else
    # (untrusted peer, missing or odd header) falls back to the connection scheme.
    assert rules == {"1:https": "https", "1:http": "http", "default": "$scheme"}


def test_hsts_is_sent_only_over_https() -> None:
    """RFC 6797 §7.2: no Strict-Transport-Security on plain-HTTP responses."""
    conf = _templates()["default.conf.template"]
    headers = _templates()["snippets/security-headers.inc.template"]
    assert "add_header Strict-Transport-Security $hsts_header always;" in headers
    assert "NGINX_HSTS" not in _code(headers)
    hsts = re.search(r"map \$forwarded_proto \$hsts_header \{(.*?)\n\}", conf, re.S)
    assert hsts, "map $hsts_header missing"
    body = _code(hsts.group(1))
    assert 'https   "${NGINX_HSTS}";' in body
    assert 'default "";' in body


def test_csp_has_no_external_sources_and_no_unsafe_eval() -> None:
    csp = _templates()["snippets/csp-web.inc.template"]
    policy = next(line for line in csp.splitlines() if line.startswith("add_header"))
    assert "https:" not in policy
    assert "gstatic" not in policy
    assert "'unsafe-eval'" not in policy
    assert "'wasm-unsafe-eval'" in policy
    assert "script-src 'self' 'wasm-unsafe-eval';" in policy  # no inline scripts
    assert "frame-ancestors 'none'" in policy


def test_web_build_serves_canvaskit_locally() -> None:
    dockerfile = _read(WEB_DOCKERFILE)
    assert "--no-web-resources-cdn" in dockerfile
    assert "--csp" in dockerfile
    assert '"useLocalCanvasKit":true' in dockerfile  # build-time guard


def test_body_limit_covers_the_attachment_limit() -> None:
    compose = _read(COMPOSE)
    max_bytes = int(re.search(r"ATTACHMENT_MAX_BYTES:-(\d+)", compose).group(1))  # type: ignore[union-attr]
    size = re.search(r"NGINX_CLIENT_MAX_BODY_SIZE:-(\d+)([km]?)", compose)
    assert size is not None
    factor = {"": 1, "k": 1024, "m": 1024 * 1024}[size.group(2)]
    assert int(size.group(1)) * factor >= max_bytes + 64 * 1024  # multipart envelope


# --- Backups encrypted with age (ADR 0019 §10) ---------------------------------


def _code(text: str) -> str:
    """Script text without comment lines (comments may mention "->", "> " etc.)."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith(("#", "<#"))
    )


def _sh_encrypted_branches(text: str) -> list[str]:
    return [
        _code(body)
        for body in re.findall(r'if \[ "\$ENCRYPT" = 1 \]; then\n(.*?)\n\s*else\n', text, re.S)
    ]


def _ps_encrypted_branches(text: str) -> list[str]:
    bodies = re.findall(r"if \(\$encrypt\) \{\n(.*?)\n\s*\} else \{", text, re.S)
    return [_code(body) for body in bodies if "Write-Encrypted" in body]


def test_backup_scripts_take_age_recipients_from_the_environment() -> None:
    sh, ps, loop = _read(BACKUP_SH), _read(BACKUP_PS1), _read(BACKUP_LOOP)
    assert '"${BACKUP_AGE_RECIPIENT:-}"' in sh
    assert '"${BACKUP_AGE_RECIPIENTS:-}"' in sh
    assert "AGE_ARGS+=(-r " in sh  # single key(s): age -r
    assert "AGE_ARGS+=(-R " in sh  # recipients file: age -R
    assert "$AgeRecipient = $env:BACKUP_AGE_RECIPIENT" in ps
    assert "$AgeRecipientsFile = $env:BACKUP_AGE_RECIPIENTS" in ps
    assert "@('-r', " in ps
    assert "@('-R', " in ps
    assert '"${BACKUP_AGE_RECIPIENT:-}"' in loop
    assert 'age -R "$AGE_RECIPIENTS_FILE"' in loop


def test_encrypted_backup_streams_without_a_plain_intermediate_file() -> None:
    sh = _read(BACKUP_SH)
    branches = _sh_encrypted_branches(sh)
    assert len(branches) == 2  # database dump + storage archive
    for body in branches:
        assert "| encrypt_to" in body
        assert "--file=" not in body  # pg_dump writes to stdout, not to a file
        assert "compose cp" not in body
        # no redirection of plaintext into a file ("==>" in messages is not one)
        assert not re.search(r'[^=\-]>\s*"?\$', body)
        assert 'mv "$partial"' in body  # *.part renamed only after the pipeline succeeded
    assert 'encrypt_to() { age "${AGE_ARGS[@]}" -o ' in sh
    assert "set -euo pipefail" in sh  # a failed pg_dump fails the pipeline

    ps = _read(BACKUP_PS1)
    ps_branches = _ps_encrypted_branches(ps)
    assert len(ps_branches) == 2
    for body in ps_branches:
        assert "--file=" not in body
        assert "'cp'" not in body
        assert "$tmpInContainer" not in body
    writer = ps[ps.index("function Write-Encrypted") :]
    writer = writer[: writer.index("\n}\n")]
    assert "Invoke-NativePipe $From $FromArgs age ($ageArgs + @('-o', $partial))" in writer
    assert "Move-Item -LiteralPath $partial" in writer

    loop = _code(_read(BACKUP_LOOP))
    assert "--file=" not in loop
    assert "set -o pipefail" in loop
    assert re.search(r"pg_dump [^\n]*\\\n\s*\| write_out ", loop)
    assert '| write_out "$partial"' in loop
    assert re.search(r"write_out\(\) \{\n\s*if \[ -n \"\$SUFFIX\" \]; then age -R ", loop)


def test_missing_age_is_an_error_not_a_plain_backup() -> None:
    sh = _read(BACKUP_SH)
    check = re.search(r"if ! command -v age >/dev/null 2>&1; then\n(.*?)\n    fi", sh, re.S)
    assert check is not None
    assert "exit 1" in check.group(1)
    assert sh.index("command -v age") < sh.index("ENCRYPT=1")
    # A malformed key fails before anything is dumped.
    assert sh.index('age "${AGE_ARGS[@]}" </dev/null') < sh.index("compose exec -T db pg_dump")

    ps = _read(BACKUP_PS1)
    assert re.search(r"if \(-not \(Get-Command age [^\n]*\)\) \{\s*throw", ps)
    assert ps.index("Get-Command age") < ps.index("$suffix = '.age'")

    loop = _read(BACKUP_LOOP)
    check = re.search(r"if ! command -v age >/dev/null 2>&1; then\n(.*?)\n    fi", loop, re.S)
    assert check is not None
    assert "exit 1" in check.group(1)


def test_backup_service_refuses_a_host_path_recipients_file() -> None:
    loop = _read(BACKUP_LOOP)
    block = re.search(
        r'if \[ -n "\$\{BACKUP_AGE_RECIPIENTS:-\}" \]; then\n(.*?)\n    fi', loop, re.S
    )
    assert block is not None
    assert "exit 2" in block.group(1)
    # Each scheduled run is a separate process: "set -e" is ignored in a function
    # called from an "||" / "if" list.
    assert 'if sh "$0" --once; then' in loop


def test_retention_also_removes_encrypted_backups() -> None:
    sh, ps, loop = _read(BACKUP_SH), _read(BACKUP_PS1), _read(BACKUP_LOOP)
    assert "-name 'rejestr-*'" in sh
    assert "-name 'rejestr-*'" in loop
    assert "-Filter 'rejestr-*'" in ps
    # Encrypted files keep the rejestr-<stamp> prefix, so the pattern covers them.
    assert 'dump="${base}.dump${SUFFIX}"' in sh
    assert 'storage="${base}-storage.tar.gz${SUFFIX}"' in sh
    assert 'SUFFIX=".age"' in sh
    assert '$dump = "$base.dump$suffix"' in ps
    assert '$storage = "$base-storage.tar.gz$suffix"' in ps
    assert 'dump="${base}.dump${SUFFIX}"' in loop
    assert 'storage="${base}-storage.tar.gz${SUFFIX}"' in loop


def test_checksums_are_of_the_encrypted_files() -> None:
    sh = _read(BACKUP_SH)
    # files[] holds the names actually written (with .age) and is what sha256sum hashes.
    assert 'files=("$dump")' in sh
    assert 'files+=("$storage")' in sh
    assert 'sha256sum "${files[@]}" > "${base}.sha256"' in sh
    ps = _read(BACKUP_PS1)
    assert "$files = @($dump)" in ps
    assert "foreach ($f in $files)" in ps


def test_restore_checks_sums_then_decrypts_as_a_stream() -> None:
    sh = _read(RESTORE_SH)
    assert 'IDENTITY="${BACKUP_AGE_IDENTITY:-}"' in sh
    assert '--identity) IDENTITY="$2"' in sh
    decrypt = re.search(r"^decrypt\(\) \{(.*)\}$", sh, re.M)
    assert decrypt is not None
    assert "age -d -i " in decrypt.group(1)
    assert " -o " not in decrypt.group(1)  # plaintext only to stdout
    assert 'sums="${DUMP%.age}"' in sh
    # sums of the encrypted files -> trial decryption -> only then the database is dropped
    assert sh.index("sha256sum -c") < sh.index('decrypt "$f" >/dev/null')
    assert sh.index('decrypt "$f" >/dev/null') < sh.index("DROP DATABASE")
    assert 'decrypt "$DUMP" | compose exec -T db pg_restore' in sh
    assert 'decrypt "$STORAGE" | docker run --rm -i' in sh

    ps = _read(RESTORE_PS1)
    assert "$Identity = $env:BACKUP_AGE_IDENTITY" in ps
    assert "-replace '\\.dump(\\.age)?$', ''" in ps
    assert ps.index("Get-FileHash") < ps.index("sprawdzam odszyfrowanie")
    assert ps.index("sprawdzam odszyfrowanie") < ps.index("DROP DATABASE")
    assert "Invoke-NativePipe age @('-d', '-i', $Identity, $Dump) docker $pgRestore" in ps
    assert "Invoke-NativePipe age @('-d', '-i', $Identity, $Storage) docker" in ps
    assert "'-o'" not in _code(ps)


def test_powershell_scripts_copy_bytes_between_processes() -> None:
    """A PowerShell pipeline decodes native output as text; .NET Framework (5.1) also
    prepends the console input encoding preamble (UTF-8 BOM) to a redirected stdin."""
    for path in (BACKUP_PS1, RESTORE_PS1):
        ps = _read(path)
        assert ".StandardOutput.BaseStream.CopyTo(" in ps, path.name
        assert "[Console]::InputEncoding.GetPreamble().Length -gt 0" in ps, path.name
        assert "New-Object System.Text.UTF8Encoding($false)" in ps, path.name
        assert path.read_bytes().startswith(b"\xef\xbb\xbf"), f"{path.name}: BOM for PS 5.1"


def test_backup_service_has_age_and_gets_the_recipient() -> None:
    compose = _read(COMPOSE)
    service = compose[compose.index("\n  backup:") :]
    service = service[: service.index("\nnetworks:")]
    assert "build: ./deploy/backup" in service
    assert "BACKUP_AGE_RECIPIENT: ${BACKUP_AGE_RECIPIENT:-}" in service
    assert "BACKUP_AGE_RECIPIENTS: ${BACKUP_AGE_RECIPIENTS:-}" in service
    dockerfile = _read(BACKUP_DOCKERFILE)
    assert "FROM postgres:16-alpine" in dockerfile  # same pg_dump major as the db service
    assert re.search(r"apk add --no-cache age\b", dockerfile)


def _backup_service() -> str:
    compose = _read(COMPOSE)
    service = compose[compose.index("\n  backup:") :]
    return service[: service.index("\nnetworks:")]


def test_backup_service_has_a_healthcheck_on_the_last_successful_backup() -> None:
    """ADR 0019 §11 (ISO 27001 A.8.13): a failed or stale backup is visible as
    'unhealthy', not only as a line in the container log."""
    service = _backup_service()
    assert 'test: ["CMD", "sh", "/opt/backup/healthcheck.sh"]' in service
    assert "./deploy/backup:/opt/backup:ro" in service  # the script is mounted
    assert "BACKUP_MAX_AGE_HOURS: ${BACKUP_MAX_AGE_HOURS:-26}" in service
    assert re.search(r"^BACKUP_MAX_AGE_HOURS=26$", _read(ENV_EXAMPLE), re.M)

    check = _code(_read(BACKUP_HEALTHCHECK))
    assert 'MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-26}"' in check
    assert 'SUCCESS_MARKER="${OUT}/.backup-last-success"' in check
    assert 'FAILURE_MARKER="${OUT}/.backup-last-failure"' in check
    assert "OUT=/backups" in check
    assert check.rstrip().endswith("exit 1")  # no evidence of a backup = unhealthy


def test_backup_loop_writes_status_markers_without_breaking_once() -> None:
    loop = _code(_read(BACKUP_LOOP))
    assert 'SUCCESS_MARKER="${OUT}/.backup-last-success"' in loop
    assert 'FAILURE_MARKER="${OUT}/.backup-last-failure"' in loop
    once = loop[loop.index('if [ "${1:-}" = "--once" ]; then') :]
    once = once[: once.index("\nfi\n")]
    lines = [line.strip() for line in once.splitlines()]
    # backup_once runs as a plain command (set -e effective), the success marker
    # only after it returned, and --once still exits 0 on success.
    assert "backup_once" in lines
    assert lines.index("backup_once") < lines.index('write_marker "$SUCCESS_MARKER" "$LAST_BASE"')
    assert lines[-1] == "exit 0"
    assert not re.search(r"backup_once\s*(\|\||&&)", loop)
    assert not re.search(r"if\s+backup_once", loop)
    # The scheduled run records a failure for the healthcheck.
    loop_body = loop[loop.index("while true; do") :]
    assert 'if sh "$0" --once; then' in loop_body
    assert 'write_marker "$FAILURE_MARKER"' in loop_body
    # Markers are dotfiles: retention (rejestr-*) never deletes them.
    assert "-name 'rejestr-*'" in loop


def test_env_example_has_the_public_key_but_never_the_private_one() -> None:
    env = _read(ENV_EXAMPLE)
    assert re.search(r"^BACKUP_AGE_RECIPIENT=$", env, re.M)
    assert not re.search(r"^BACKUP_AGE_IDENTITY=", env, re.M)
    assert "AGE-SECRET-KEY-1" not in env


def _posix_shell(name: str) -> str | None:
    found = shutil.which(name)
    if found is None or (sys.platform == "win32" and "system32" in found.lower()):
        return None  # WSL launcher on Windows - not the shell the scripts are for
    return found


@pytest.mark.parametrize(
    ("shell", "script"),
    [("bash", BACKUP_SH), ("bash", RESTORE_SH), ("sh", BACKUP_LOOP), ("sh", BACKUP_HEALTHCHECK)],
    ids=["backup.sh", "restore.sh", "backup-loop.sh", "healthcheck.sh"],
)
def test_shell_scripts_parse(shell: str, script: Path) -> None:
    executable = _posix_shell(shell)
    if executable is None:
        pytest.skip(f"{shell} not available")
    result = subprocess.run(  # noqa: S603 - fixed arguments, repository files
        [executable, "-n", script.as_posix()], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
