#!/usr/bin/env python3
"""Review evidence and manage an external single-use Gate A-left permit.

No command in this program contacts or controls a printer. Path-only consume
is intentionally unavailable because it cannot preserve the verified open
payload through a later GUI send.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from . import control_contract as control
except ImportError:  # pragma: no cover - direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import control_contract as control  # type: ignore[no-redef]


def _print(value: object) -> None:
    print(json.dumps(value, allow_nan=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    review = commands.add_parser("review", help="validate exact external attempt evidence")
    review.add_argument("--attempt", type=Path, required=True)

    issue = commands.add_parser("issue", help="issue one external ephemeral permit")
    issue.add_argument("--attempt", type=Path, required=True)
    issue.add_argument("--permission", type=Path, required=True)

    evaluate = commands.add_parser("evaluate", help="check whether an external permit is effective")
    evaluate.add_argument("--attempt", type=Path, required=True)
    evaluate.add_argument("--permit", type=Path, required=True)

    prepare = commands.add_parser(
        "prepare-evidence",
        help=(
            "derive exact G-code/config and approved profile evidence into a "
            "fresh external directory"
        ),
    )
    prepare.add_argument("--sliced-plate", type=Path, required=True)
    prepare.add_argument("--output-directory", type=Path, required=True)

    commands.add_parser(
        "init-ledger",
        help="explicitly initialize the identity-bound canonical ledger once",
    )

    args = parser.parse_args()
    if args.command == "review":
        _print(control.review_attempt(args.attempt))
        return 0
    if args.command == "issue":
        permit = control.issue_permit(args.attempt, args.permission)
        _print(
            {
                "permit_path": str(permit),
                "canonical_ledger_root": str(control.canonical_ledger_root()),
                "state": control.evaluate_permit(permit, args.attempt),
                "warning": (
                    "Permit is external and single-use. Consume immediately before one "
                    "Send/Print attempt; a failed/cancelled/rejected/ambiguous attempt "
                    "still consumes it."
                ),
            }
        )
        return 0
    if args.command == "evaluate":
        _print(control.evaluate_permit(args.permit, args.attempt))
        return 0
    if args.command == "prepare-evidence":
        _print(
            control.prepare_external_evidence_payloads(
                args.sliced_plate, args.output_directory
            )
        )
        return 0
    if args.command == "init-ledger":
        root = control.initialize_canonical_ledger()
        _print({"canonical_ledger_root": str(root), "initialized": True})
        return 0
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (control.ContractError, FileExistsError) as error:
        raise SystemExit(f"BLOCKED: {error}") from error
