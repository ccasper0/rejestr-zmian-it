# Contributing

Thanks for your interest! This is a personal project provided **"as is"**,
maintained in spare time. Issues and pull requests are welcome, but there is
no commitment to review, merge, release or support them on any schedule.

## Before you start

- The specification and working rules live in [CLAUDE.md](CLAUDE.md)
  (Polish). It wins over the code; if a change alters the specification,
  update CLAUDE.md in the same pull request.
- Architectural decisions are recorded as ADRs in `docs/decisions/`. A change
  of a recorded decision needs a new or updated ADR.
- The audit log (hash chain, protective triggers), row-level security and the
  permission matrix (`backend/app/permissions.py`) are security-critical.
  Changes there need tests, and must not be simplified "for later".
- Never commit secrets. All configuration goes through environment variables
  described in `.env.example`.

## Development

See [README.md](README.md) for running the stack and the commands. Before
opening a pull request, run:

```bash
cd backend && ruff check . && ruff format --check . && mypy app && pytest -q
cd frontend && flutter analyze && flutter test
```

- Every data-modifying endpoint writes an audit entry (tested).
- Every endpoint with a `company_id` has an isolation test (company A gets
  404 for a resource of company B).
- User-facing texts are in Polish; code, API, database names and comments
  are in English.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Security issues

Do not open public issues for vulnerabilities — see [SECURITY.md](SECURITY.md).

## License

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), the license of this project (section 5).
