#!/usr/bin/env python3
"""Stage, generate, and verify an r6 tree without publishing it."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


EXCLUDED_NAMES = frozenset({"generated", "__pycache__", ".pytest_cache", ".DS_Store"})


def _copy_source(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(*EXCLUDED_NAMES, "*.pyc", "*.pyo"),
        dirs_exist_ok=True,
    )


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def build_checked_tree(source: Path, staging_parent: Path, python: Path) -> Path:
    staging_parent.mkdir(parents=True, exist_ok=True)
    staged_root = Path(tempfile.mkdtemp(prefix=".r6-release-stage-", dir=staging_parent))
    try:
        _copy_source(source, staged_root)
        _run([str(python), "release_check.py", "--source-only"], staged_root)
        _run([str(python), "generate_all_petg_r6.py"], staged_root)
        _run([str(python), "release_check.py"], staged_root)
        return staged_root
    except BaseException:
        shutil.rmtree(staged_root, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--python", type=Path, default=Path(sys.executable), help="project Python interpreter")
    parser.add_argument("--source-only", action="store_true", help="run only the pre-generation repository checks")
    args = parser.parse_args(argv)
    source = args.source.resolve()
    # Do not resolve a virtual-environment interpreter symlink: invoking the
    # symlink is what activates that environment's site-packages.
    python = args.python.absolute()
    if args.source_only:
        _run([str(python), "release_check.py", "--source-only"], source)
        return 0

    checked = build_checked_tree(source, source.parent, python)
    try:
        print("Checked staged build passed; no publication was performed")
        print("Use publish_root.py for exclusive no-replace repository publication")
    finally:
        shutil.rmtree(checked, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
