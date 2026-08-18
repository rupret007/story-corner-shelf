#!/usr/bin/env python3
"""Run a frozen R11-era test suite, excluding retired root-router tests.

The frozen trees under development/r11* are preserved unchanged, including
their tests. Three of those tests assert that the repository's root
README.md, PRINT_ME_FIRST.md, PROGRESS.md, docs/ mirrors, and
PUBLICATION_MANIFEST.json still route readers to R11 as the current
development focus. That root-doc contract was retired by the r5 Triadic
Palatine migration (see CHANGELOG.md); the root docs now point to the frozen
R11 trees instead of being governed by them. This runner executes every
remaining test in a given suite while skipping only those retired
assertions, so the frozen test files themselves stay byte-identical.
"""

from __future__ import annotations

import sys
import unittest

RETIRED_ROOT_ROUTER_TESTS = frozenset(
    {
        # development/r11/tests/test_docs.py
        "test_public_entrypoints_route_to_current_r11_without_releasing_it",
        # development/r11_physical/tests/test_physical_handoff.py
        "test_public_routers_are_mirrored_and_point_to_physical_handoff",
        "test_publication_manifest_identifies_current_router_sources_truthfully",
    }
)


def prune(suite: unittest.TestSuite) -> unittest.TestSuite:
    kept = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            kept.addTest(prune(item))
        elif item.id().rsplit(".", 1)[-1] not in RETIRED_ROOT_ROUTER_TESTS:
            kept.addTest(item)
    return kept


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <suite start directory>", file=sys.stderr)
        return 2
    start_dir = sys.argv[1]
    loader = unittest.TestLoader()
    suite = prune(loader.discover(start_dir, pattern="test_*.py"))
    if suite.countTestCases() == 0:
        print(f"no tests discovered under {start_dir}", file=sys.stderr)
        return 2
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
