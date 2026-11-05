# Security policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report vulnerabilities privately through GitHub:
**Security → Report a vulnerability** (private vulnerability reporting) in this
repository. Include the affected version or commit, steps to reproduce and the
impact you expect.

This is a personal project maintained in spare time and provided **"as is"**
(see [LICENSE](LICENSE), sections 7 and 8). There is no guaranteed response
time, no bug bounty and no security support contract. Reports are read and,
when confirmed, fixed on a best-effort basis; a fix is announced in the
release notes / commit history after it is available.

## Scope

In scope: the application code in this repository (backend API, frontend,
database migrations and roles, nginx templates, backup scripts).

Particularly interesting:

- tampering with the audit log or its SHA-256 hash chain without detection,
- reading or changing data of a company the user has no role in
  (row-level security, RBAC),
- authentication and session handling (local accounts, JWT, refresh tokens),
- bypassing attachment type/size checks, injection in PDF/CSV exports.

Out of scope: your own deployment and its configuration (TLS proxy, secrets in
`.env`, firewall, host hardening), denial of service by volume, and findings
in third-party components that should be reported upstream.

## Supported versions

Only the latest commit on `main` is supported.

## Deployment hardening

See [docs/deployment.md](docs/deployment.md) (Polish) for the production
checklist: secrets, TLS and HSTS, trusted proxies, rate limits, encrypted
backups and their monitoring.
