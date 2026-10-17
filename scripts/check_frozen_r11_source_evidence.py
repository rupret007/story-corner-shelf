#!/usr/bin/env python3
"""Verify immutable R11 v1 source evidence against the live repository tree."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V2_ROOT = ROOT / "development" / "r11_print_v2"
if str(V2_ROOT) not in sys.path:
    sys.path.insert(0, str(V2_ROOT))

import control_contract as control  # noqa: E402


def main() -> None:
    evidence = control.verify_frozen_v1()
    if evidence.get("verified") is not True:
        raise SystemExit("Frozen R11 v1 source evidence verification failed")
    print(
        "Frozen R11 v1 source evidence verified: "
        f"source_tree_sha256={evidence['source_tree']['source_tree_sha256']}"
    )


if __name__ == "__main__":
    main()
