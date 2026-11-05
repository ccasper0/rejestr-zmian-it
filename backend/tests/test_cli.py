import pytest

from app.cli import build_parser


def test_seed_command_parses() -> None:
    args = build_parser().parse_args(["seed"])
    assert args.command == "seed"


def test_verify_audit_company_or_global() -> None:
    args = build_parser().parse_args(["verify-audit", "--company", "ALFA"])
    assert args.command == "verify-audit"
    assert args.company == "ALFA"
    assert args.global_chain is False

    args = build_parser().parse_args(["verify-audit", "--global"])
    assert args.company is None
    assert args.global_chain is True


def test_verify_audit_company_and_global_are_exclusive() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["verify-audit", "--company", "ALFA", "--global"])


def test_verify_audit_without_target_fails() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["verify-audit"])


def test_no_command_fails() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_verify_audit_is_implemented() -> None:
    """The Etap 1 stub (exit code 2) is gone; behaviour is tested in test_audit_verify.py."""
    import app.cli as cli

    assert not hasattr(cli, "EXIT_NOT_IMPLEMENTED")
    assert callable(cli.verify_audit)
