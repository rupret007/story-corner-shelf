#!/usr/bin/env python3
"""Build and exclusively publish a checked r6 repository tree.

The input is a *staged* r6 tree whose generated artifacts already exist.  This
tool does not generate or modify models.  It runs the staged source and full
release checks before creating any output, copies an explicit publication map
to a temporary sibling, validates every copied byte, reruns both checks and the
complete tests from that isolated tree, fsyncs it, and finally performs an
atomic no-replace rename.

No live repository, existing destination, generated source artifact, or
``.git`` directory is deleted or replaced.  Cleanup is limited to a uniquely
named unpublished temporary tree created by this invocation.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence


PUBLICATION_MANIFEST = "PUBLICATION_MANIFEST.json"
EXACT_HERO = "artist_rendering_all_petg_two_level_exact_6_plus_3.png"
PRESERVED_RENDERING = "artist_rendering_all_petg_two_level.png"
PRESERVED_RENDERING_SHA256 = (
    "236ccc9c9f6d77818c3885518417ad898164c5ffa7ea53a253c95c5e35ce903c"
)
HERO_PROMPT = "artist_rendering_all_petg_two_level.prompt.md"

ROOT_DOCUMENT_MAP: tuple[tuple[str, str], ...] = (
    ("README.md", "README.md"),
    ("PRINT_ME_FIRST.md", "PRINT_ME_FIRST.md"),
    ("SAFETY.md", "SAFETY.md"),
    ("ENGINEERING_DESIGN.md", "ENGINEERING_DESIGN.md"),
    ("ASSEMBLY.md", "ASSEMBLY.md"),
    ("MEASUREMENT_WORKSHEET.md", "MEASUREMENT_WORKSHEET.md"),
    ("TEST_PROTOCOL.md", "TEST_PROTOCOL.md"),
    ("CONTRIBUTING.md", "CONTRIBUTING.md"),
    ("CHANGELOG_ENTRY.md", "CHANGELOG.md"),
)

REPOSITORY_METADATA_FILES: tuple[str, ...] = (
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    ".python-version",
    "requirements.txt",
)

REFERENCE_DOCUMENTS: tuple[str, ...] = (
    "PROGRESS.md",
    "REFERENCE_RESEARCH.md",
    "REFERENCE_3MF_AUDIT.md",
)

STAGED_TREE_MAP: tuple[tuple[str, str], ...] = (
    ("generated", "generated"),
    ("tests", "tests"),
)

REQUIRED_ROOT_MODULES: frozenset[str] = frozenset(
    {
        "build_release.py",
        "generate_all_petg_r6.py",
        "generate_drawings.py",
        "publish_root.py",
        "release_check.py",
    }
)

PUBLICATION_TEMPLATE_FILES: tuple[str, ...] = (
    ".github/workflows/validate.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/measurement-update.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/dependabot.yml",
)

FORBIDDEN_COMPONENTS: frozenset[str] = frozenset(
    {
        ".aws",
        ".DS_Store",
        ".env",
        ".git",
        ".netrc",
        ".npmrc",
        ".pytest_cache",
        ".pypirc",
        ".ssh",
        ".venv",
        ".visual_check",
        "__pycache__",
        "credentials",
        "credentials.json",
        "id_ed25519",
        "id_rsa",
        "secrets",
        "secrets.json",
    }
)
FORBIDDEN_SUFFIXES: frozenset[str] = frozenset(
    {
        ".bak",
        ".gcode",
        ".kdbx",
        ".key",
        ".log",
        ".p12",
        ".pem",
        ".pfx",
        ".pyc",
        ".pyo",
        ".tmp",
    }
)
_HOST_PATH_RE = re.compile(
    rb"(?<![A-Za-z0-9])/(?:Users|home)/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"
)
_CREDENTIAL_DATA_FILENAME_RE = re.compile(
    r"^(?:credentials?|secrets?|tokens?)(?:[._-][a-z0-9_-]+)*\."
    r"(?:cfg|env|ini|json|toml|ya?ml)$",
    re.IGNORECASE,
)
_CREDENTIAL_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "private key",
        re.compile(
            rb"-----BEGIN "
            + rb"(?:RSA |EC |OPENSSH |DSA )?"
            + rb"PRIVATE KEY-----"
        ),
    ),
    (
        "GitHub token",
        re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ),
    ("AWS access-key ID", re.compile(rb"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    ("Google API key", re.compile(rb"AIza[0-9A-Za-z_-]{30,}")),
    ("Slack token", re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe live key", re.compile(rb"(?:sk|rk)_live_[A-Za-z0-9]{16,}")),
    ("OpenAI API key", re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("Anthropic API key", re.compile(rb"sk-ant-[A-Za-z0-9_-]{32,}")),
    ("GitLab token", re.compile(rb"glpat-[A-Za-z0-9_-]{20,}")),
    ("npm token", re.compile(rb"npm_[A-Za-z0-9]{32,}")),
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PublicationError(RuntimeError):
    """A fail-closed publication precondition or verification failed."""


class DuplicateJsonKey(ValueError):
    """A JSON object contained a duplicate key."""


@dataclass(frozen=True)
class CopyRule:
    """One byte-preserving source-to-publication file mapping."""

    source_scope: str
    source_root: Path
    source_relative: str
    destination: str

    @property
    def source(self) -> Path:
        return self.source_root / self.source_relative


CheckRunner = Callable[[Path, Path, bool], dict[str, Any]]
TestRunner = Callable[[Path, Path], None]
Committer = Callable[[Path, Path], None]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise DuplicateJsonKey(f"duplicate JSON key {key!r}")
        value[key] = child
    return value


def _load_json_strict(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateJsonKey) as exc:
        raise PublicationError(f"invalid JSON {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _safe_relative(value: str, *, label: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise PublicationError(f"unsafe {label} path: {value!r}")
    if relative.as_posix() != value:
        raise PublicationError(f"noncanonical {label} path: {value!r}")
    return relative


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _require_regular_file(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise PublicationError(f"required publication source is unavailable: {path}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise PublicationError(f"symlink publication source is forbidden: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise PublicationError(f"non-regular publication source is forbidden: {path}")
    if stat.S_IMODE(info.st_mode) & 0o7000:
        raise PublicationError(f"special executable mode bits are forbidden: {path}")


def _tree_files(root: Path, relative: str, *, ignore_local: bool = False) -> list[Path]:
    base = root / relative
    try:
        info = base.lstat()
    except OSError as exc:
        raise PublicationError(f"required publication directory is unavailable: {base}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise PublicationError(f"publication directory must be a real directory: {base}")
    files: list[Path] = []
    for directory, names, filenames in os.walk(base, followlinks=False):
        directory_path = Path(directory)
        if ignore_local:
            names[:] = [name for name in names if name not in FORBIDDEN_COMPONENTS]
        for name in names:
            child = directory_path / name
            child_info = child.lstat()
            if stat.S_ISLNK(child_info.st_mode) or not stat.S_ISDIR(child_info.st_mode):
                raise PublicationError(f"linked/non-directory tree entry is forbidden: {child}")
        for name in filenames:
            child = directory_path / name
            if ignore_local and (
                name in FORBIDDEN_COMPONENTS
                or child.suffix.lower() in FORBIDDEN_SUFFIXES
            ):
                continue
            _require_regular_file(child)
            files.append(child)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def _add_rule(
    rules: list[CopyRule],
    *,
    scope: str,
    root: Path,
    source: str,
    destination: str,
) -> None:
    _safe_relative(source, label="source")
    _safe_relative(destination, label="destination")
    path = root / source
    _require_regular_file(path)
    rules.append(CopyRule(scope, root, source, destination))


def _add_tree(
    rules: list[CopyRule],
    *,
    scope: str,
    root: Path,
    source: str,
    destination: str,
) -> None:
    source_root = root / source
    for path in _tree_files(root, source, ignore_local=True):
        suffix = path.relative_to(source_root).as_posix()
        target = (PurePosixPath(destination) / suffix).as_posix()
        _add_rule(
            rules,
            scope=scope,
            root=root,
            source=path.relative_to(root).as_posix(),
            destination=target,
        )


def _validate_hybrid_reference(repository_root: Path) -> dict[str, Any]:
    hybrid = repository_root / "reference" / "hybrid_r5"
    manifest_path = hybrid / "SOURCE_MANIFEST.json"
    manifest = _load_json_strict(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise PublicationError("reference/hybrid_r5/SOURCE_MANIFEST.json has no file list")
    declared: dict[str, str] = {}
    for record in manifest["files"]:
        if not isinstance(record, dict):
            raise PublicationError("invalid hybrid r5 source-manifest record")
        relative = record.get("path")
        digest = record.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise PublicationError("invalid hybrid r5 source-manifest path/hash")
        _safe_relative(relative, label="hybrid r5 source")
        if relative in declared or not _SHA256_RE.fullmatch(digest):
            raise PublicationError("duplicate or invalid hybrid r5 source-manifest record")
        declared[relative] = digest
    actual = {
        path.relative_to(hybrid).as_posix()
        for path in _tree_files(repository_root, "reference/hybrid_r5")
    }
    expected = set(declared) | {"SOURCE_MANIFEST.json"}
    if actual != expected:
        raise PublicationError(
            "hybrid r5 source snapshot differs from its exact manifest: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    for relative, digest in declared.items():
        if _sha256(hybrid / relative) != digest:
            raise PublicationError(f"hybrid r5 source digest drift: {relative}")
    return manifest


def _validate_exact_hero(staged_release: Path) -> str:
    hero = staged_release / "assets" / EXACT_HERO
    preserved = staged_release / "assets" / PRESERVED_RENDERING
    prompt = staged_release / "assets" / HERO_PROMPT
    _require_regular_file(hero)
    _require_regular_file(preserved)
    _require_regular_file(prompt)
    digest = _sha256(hero)
    if _sha256(preserved) != PRESERVED_RENDERING_SHA256:
        raise PublicationError("preserved two-level rendering history digest drift")
    prompt_text = prompt.read_text(encoding="utf-8")
    if EXACT_HERO not in prompt_text or digest not in prompt_text:
        raise PublicationError("exact hero prompt does not identify the selected asset and digest")
    readme = (staged_release / "docs" / "README.md").read_text(encoding="utf-8")
    if f"assets/{EXACT_HERO}" not in readme:
        raise PublicationError("active r6 README does not link the exact 6 + 3 hero")
    return digest


def _publication_template_source(staged_release: Path, name: str) -> str:
    """Resolve one template before or after its intentional root relocation.

    Development keeps repository templates below ``publication/`` so they do
    not affect the live r5 checkout.  The assembled r6 repository installs the
    same files at their canonical root destinations.  Exactly one layout must
    be present; accepting both could silently select a stale template.
    """

    _safe_relative(name, label="publication template")
    candidates = (f"publication/{name}", name)
    present = [relative for relative in candidates if _lexists(staged_release / relative)]
    if len(present) != 1:
        raise PublicationError(
            "publication template must exist in exactly one source or assembled "
            f"location for {name}: present={present}"
        )
    return present[0]


def publication_copy_rules(
    staged_release: Path, repository_root: Path
) -> tuple[CopyRule, ...]:
    """Return the exact publication file map, rejecting missing/linked inputs."""

    staged_release = staged_release.resolve()
    repository_root = repository_root.resolve()
    _validate_hybrid_reference(repository_root)
    _validate_exact_hero(staged_release)
    rules: list[CopyRule] = []

    modules = sorted(staged_release.glob("*.py"), key=lambda path: path.name)
    module_names = {path.name for path in modules}
    if not REQUIRED_ROOT_MODULES <= module_names:
        raise PublicationError(
            f"staged r6 source modules are incomplete: {sorted(REQUIRED_ROOT_MODULES - module_names)}"
        )
    for path in modules:
        _add_rule(
            rules,
            scope="staged_r6",
            root=staged_release,
            source=path.name,
            destination=path.name,
        )
    _add_rule(
        rules,
        scope="staged_r6",
        root=staged_release,
        source="config.json",
        destination="config.json",
    )

    for source_name, root_name in ROOT_DOCUMENT_MAP:
        source = f"docs/{source_name}"
        _add_rule(
            rules,
            scope="staged_r6",
            root=staged_release,
            source=source,
            destination=source,
        )
        _add_rule(
            rules,
            scope="staged_r6",
            root=staged_release,
            source=source,
            destination=root_name,
        )

    for name in REFERENCE_DOCUMENTS:
        _add_rule(
            rules,
            scope="staged_r6",
            root=staged_release,
            source=name,
            destination=name,
        )
    for name in (EXACT_HERO, PRESERVED_RENDERING, HERO_PROMPT):
        _add_rule(
            rules,
            scope="staged_r6",
            root=staged_release,
            source=f"assets/{name}",
            destination=f"assets/{name}",
        )

    for source, destination in STAGED_TREE_MAP:
        _add_tree(
            rules,
            scope="staged_r6",
            root=staged_release,
            source=source,
            destination=destination,
        )
    for name in PUBLICATION_TEMPLATE_FILES:
        source = _publication_template_source(staged_release, name)
        _add_rule(
            rules,
            scope="staged_r6_publication_template",
            root=staged_release,
            source=source,
            destination=name,
        )

    for name in REPOSITORY_METADATA_FILES:
        _add_rule(
            rules,
            scope="repository_metadata",
            root=repository_root,
            source=name,
            destination=name,
        )

    license_candidates = [
        name
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")
        if _lexists(repository_root / name)
    ]
    if len(license_candidates) > 1:
        raise PublicationError("multiple root license files require an explicit owner decision")
    if license_candidates:
        name = license_candidates[0]
        _add_rule(
            rules,
            scope="owner_selected_license",
            root=repository_root,
            source=name,
            destination=name,
        )

    _add_tree(
        rules,
        scope="hybrid_r5_fallback",
        root=repository_root,
        source="reference/hybrid_r5",
        destination="reference/hybrid_r5",
    )

    by_destination: dict[str, CopyRule] = {}
    for rule in rules:
        if rule.destination == PUBLICATION_MANIFEST:
            raise PublicationError("publication sources may not pre-create the publication manifest")
        if rule.destination in by_destination:
            other = by_destination[rule.destination]
            raise PublicationError(
                f"duplicate publication destination {rule.destination}: "
                f"{other.source_relative}, {rule.source_relative}"
            )
        by_destination[rule.destination] = rule
    return tuple(sorted(rules, key=lambda rule: rule.destination))


def _clean_python_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _run_release_check(python: Path, root: Path, source_only: bool) -> dict[str, Any]:
    command = [
        os.fspath(python),
        "-B",
        os.fspath(root / "release_check.py"),
        "--root",
        os.fspath(root),
        "--json",
    ]
    if source_only:
        command.append("--source-only")
    result = subprocess.run(
        command,
        cwd=root,
        env=_clean_python_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PublicationError(
            f"release_check.py did not emit JSON ({'source-only' if source_only else 'full'}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        ) from exc
    expected_mode = "source-only" if source_only else "full-release"
    if (
        result.returncode != 0
        or not isinstance(report, dict)
        or report.get("passed") is not True
        or report.get("mode") != expected_mode
    ):
        raise PublicationError(
            f"staged {expected_mode} check failed: {report.get('issues') if isinstance(report, dict) else report}"
        )
    return report


def _run_complete_tests(python: Path, root: Path) -> None:
    result = subprocess.run(
        [
            os.fspath(python),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ],
        cwd=root,
        env=_clean_python_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise PublicationError(
            "assembled publication test suite failed: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def _walk_dicts(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _release_plan_and_report_maps(
    *documents: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    plans: dict[str, Mapping[str, Any]] = {}
    reports: dict[str, Mapping[str, Any]] = {}
    for document in documents:
        for item in _walk_dicts(document):
            candidates = item.get("plans")
            if isinstance(candidates, list):
                for plan in candidates:
                    if isinstance(plan, dict) and isinstance(plan.get("package_id"), str):
                        plans[str(plan["package_id"])] = plan
            if isinstance(item.get("package_id"), str) and "all_checks_pass" in item:
                reports[str(item["package_id"])] = item
    return plans, reports


def _derive_release_evidence(
    staged_release: Path, full_report: Mapping[str, Any]
) -> dict[str, Any]:
    if full_report.get("passed") is not True or full_report.get("mode") != "full-release":
        raise PublicationError("publication requires a passing full-release report")
    derived = full_report.get("derived")
    if not isinstance(derived, dict):
        raise PublicationError("full-release report omitted derived config/package evidence")
    config = _load_json_strict(staged_release / "config.json")
    manifest = _load_json_strict(staged_release / "generated" / "manifest.json")
    validation = _load_json_strict(staged_release / "generated" / "validation.json")
    if not all(isinstance(value, dict) for value in (config, manifest, validation)):
        raise PublicationError("config, generated manifest, and validation must be JSON objects")

    project = config.get("project")
    protocol = config.get("test_protocol")
    if not isinstance(project, dict) or not isinstance(protocol, dict):
        raise PublicationError("config lacks project/test_protocol release gates")
    for key in ("name", "revision", "edition"):
        if not isinstance(project.get(key), str) or not str(project[key]).strip():
            raise PublicationError(f"config project.{key} must be nonempty")
    if project.get("production_release_allowed") is not False:
        raise PublicationError("config must keep production_release_allowed false")
    if project.get("embedded_gcode_allowed") is not False:
        raise PublicationError("config must keep embedded_gcode_allowed false")
    if protocol.get("tested_load_rating_exists") is not False:
        raise PublicationError("config must keep tested_load_rating_exists false")

    if validation.get("physical_installation_qualified") is not False:
        raise PublicationError("validation must explicitly set physical_installation_qualified false")
    if validation.get("production_release_eligible") is not False:
        raise PublicationError("validation must explicitly set production_release_eligible false")
    if validation.get("software_model_package_eligible") is not True:
        raise PublicationError("validation must explicitly affirm software_model_package_eligible")
    blockers = validation.get("physical_qualification_blockers")
    if not isinstance(blockers, list) or not blockers:
        raise PublicationError("validation must name nonempty physical_qualification_blockers")
    if validation.get("production_ready") is not False:
        raise PublicationError("validation must keep production_ready false")
    if validation.get("tested_load_rating_exists") is not False:
        raise PublicationError("validation must keep tested_load_rating_exists false")
    if validation.get("embedded_gcode_allowed") is not False:
        raise PublicationError("validation must prohibit embedded G-code")
    if manifest.get("production_ready") is not False:
        raise PublicationError("generated manifest must keep production_ready false")
    if manifest.get("tested_load_rating_exists") is not False:
        raise PublicationError("generated manifest must keep tested_load_rating_exists false")
    if manifest.get("physical_installation_qualified") is not False:
        raise PublicationError("generated manifest must explicitly set physical_installation_qualified false")
    if manifest.get("production_release_eligible") is not False:
        raise PublicationError("generated manifest must explicitly set production_release_eligible false")
    if manifest.get("software_model_package_eligible") is not True:
        raise PublicationError("generated manifest must explicitly affirm software_model_package_eligible")
    manifest_blockers = manifest.get("physical_qualification_blockers")
    if not isinstance(manifest_blockers, list) or not manifest_blockers:
        raise PublicationError("generated manifest must name nonempty physical_qualification_blockers")
    if manifest_blockers != blockers:
        raise PublicationError("generated manifest/validation physical blockers differ")

    package_filenames = derived.get("package_filenames")
    package_counts = derived.get("package_counts")
    if not isinstance(package_filenames, dict) or not package_filenames:
        raise PublicationError("full-release report omitted canonical package filenames")
    if not isinstance(package_counts, dict):
        raise PublicationError("full-release report omitted derived package counts")
    if not all(
        isinstance(package_id, str) and isinstance(filename, str)
        for package_id, filename in package_filenames.items()
    ):
        raise PublicationError("canonical package mapping is malformed")
    expected_filenames = list(package_filenames.values())
    if len(set(expected_filenames)) != len(expected_filenames):
        raise PublicationError("canonical package filenames are not unique")
    package_dir = staged_release / "generated" / "model_only_3mf"
    actual_filenames = sorted(path.name for path in package_dir.glob("*.3mf"))
    if set(actual_filenames) != set(expected_filenames) or len(actual_filenames) != len(
        expected_filenames
    ):
        raise PublicationError(
            "generated model-only package set is not exactly canonical: "
            f"expected={expected_filenames}, actual={actual_filenames}"
        )

    plans, reports = _release_plan_and_report_maps(manifest, validation)
    canonical_ids = list(package_filenames)
    if not set(canonical_ids) <= set(plans):
        raise PublicationError(
            f"canonical package plans are incomplete: {sorted(set(canonical_ids) - set(plans))}"
        )
    if not set(canonical_ids) <= set(reports):
        raise PublicationError(
            "canonical package validation reports are incomplete: "
            f"{sorted(set(canonical_ids) - set(reports))}"
        )
    package_records: list[dict[str, Any]] = []
    for package_id in canonical_ids:
        plan = plans[package_id]
        report = reports[package_id]
        if plan.get("filename") != package_filenames[package_id]:
            raise PublicationError(f"canonical package plan filename drift: {package_id}")
        if report.get("all_checks_pass") is not True:
            raise PublicationError(f"canonical package validation failed: {package_id}")
        expected_count = package_counts.get(package_id)
        if expected_count is not None and plan.get("physical_object_count") != expected_count:
            raise PublicationError(f"canonical package object-count drift: {package_id}")
        package_records.append(
            {
                "package_id": package_id,
                "filename": package_filenames[package_id],
                "physical_object_count": plan.get("physical_object_count"),
                "validation_passed": True,
            }
        )

    drawings = sorted(
        path.relative_to(staged_release / "generated").as_posix()
        for path in (staged_release / "generated" / "drawings").glob("*.svg")
    )
    if not drawings:
        raise PublicationError("checked staged release contains no governing SVG drawings")
    project_evidence = {key: project[key] for key in ("name", "revision", "edition")}
    for key, value in project_evidence.items():
        if derived.get({"name": "project_name"}.get(key, key)) != value:
            raise PublicationError(f"full-release derived project {key} differs from config")
    return {
        "project": project_evidence,
        "derived_inventory": {
            key: value
            for key, value in derived.items()
            if key.endswith("_count") or key.endswith("_counts")
        },
        "canonical_packages": package_records,
        "governing_drawings": drawings,
        "physical_qualification_blockers": blockers,
    }


def _contains_host_path(stream: Any) -> bool:
    tail = b""
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            return False
        candidate = tail + chunk
        if _HOST_PATH_RE.search(candidate):
            return True
        tail = candidate[-512:]


def _reject_host_paths(path: Path) -> None:
    with path.open("rb") as stream:
        if _contains_host_path(stream):
            raise PublicationError(f"personal absolute path found in publication file: {path}")
    if not zipfile.is_zipfile(path):
        return
    try:
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                with archive.open(member) as stream:
                    if _contains_host_path(stream):
                        raise PublicationError(
                            f"personal absolute path found in archive member {path}:{member.filename}"
                        )
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PublicationError(f"unable to inspect archive for host paths: {path}: {exc}") from exc


def _find_credential_signature(stream: Any) -> str | None:
    tail = b""
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            return None
        candidate = tail + chunk
        for label, pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(candidate):
                return label
        tail = candidate[-1024:]


def _reject_credentials(path: Path) -> None:
    """Reject high-confidence credentials without echoing sensitive content."""

    with path.open("rb") as stream:
        label = _find_credential_signature(stream)
    if label is not None:
        raise PublicationError(f"{label} signature found in publication file: {path}")
    if not zipfile.is_zipfile(path):
        return
    try:
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                with archive.open(member) as stream:
                    label = _find_credential_signature(stream)
                if label is not None:
                    raise PublicationError(
                        f"{label} signature found in archive member "
                        f"{path}:{member.filename}"
                    )
    except PublicationError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PublicationError(
            f"unable to inspect archive for credential signatures: {path}: {exc}"
        ) from exc


def _reject_forbidden_destination(relative: str) -> None:
    path = PurePosixPath(relative)
    if FORBIDDEN_COMPONENTS & set(path.parts) or any(
        part.startswith(".env.") or _CREDENTIAL_DATA_FILENAME_RE.fullmatch(part)
        for part in path.parts
    ):
        raise PublicationError(f"forbidden cache/local component in publication: {relative}")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise PublicationError(f"forbidden temporary/machine-code file in publication: {relative}")


def _copy_rules(rules: Sequence[CopyRule], destination: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for rule in rules:
        _reject_forbidden_destination(rule.destination)
        source = rule.source
        _require_regular_file(source)
        target = destination / rule.destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if _lexists(target):
            raise PublicationError(f"copy map attempted to overwrite {rule.destination}")
        shutil.copy2(source, target, follow_symlinks=False)
        source_hash = _sha256(source)
        if (
            _sha256(target) != source_hash
            or target.stat().st_size != source.stat().st_size
            or _file_mode(target) != _file_mode(source)
        ):
            raise PublicationError(f"byte, size, or executable-mode drift copying {rule.destination}")
        records.append(
            {
                "destination": rule.destination,
                "source_scope": rule.source_scope,
                "source": rule.source_relative,
                "bytes": source.stat().st_size,
                "sha256": source_hash,
                "mode": f"{_file_mode(source):04o}",
            }
        )
    return records


def _audit_copy_rule_sources(rules: Sequence[CopyRule]) -> None:
    """Reject forbidden destinations, host paths, and credentials before staging."""

    for rule in rules:
        _reject_forbidden_destination(rule.destination)
        _require_regular_file(rule.source)
        _reject_host_paths(rule.source)
        _reject_credentials(rule.source)


def _license_status(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    licenses = [
        str(record["destination"])
        for record in records
        if PurePosixPath(str(record["destination"])).name
        in {"LICENSE", "LICENSE.md", "LICENSE.txt"}
    ]
    if licenses:
        return {"status": "owner_selected_file_preserved", "file": licenses[0]}
    return {
        "status": "owner_decision_pending_no_license_file",
        "warning": "Public visibility grants no reuse rights; the owner has not selected a project license.",
    }


def _audit_license_marker(manifest: Mapping[str, Any]) -> None:
    records = manifest.get("files")
    if not isinstance(records, list):
        raise PublicationError("publication manifest has no files for license audit")
    expected = _license_status(records)
    if manifest.get("license") != expected:
        raise PublicationError(
            "publication license marker differs from the mapped owner-selected license state"
        )


def _publication_manifest_payload(
    records: Sequence[Mapping[str, Any]],
    evidence: Mapping[str, Any],
    hero_sha256: str,
    hybrid_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    total_bytes = sum(int(record["bytes"]) for record in records)
    return {
        "schema_version": 1,
        "publication_kind": "software-checked model-only experimental release",
        "software_model_publication_eligible": True,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "tested_load_rating_exists": False,
        "embedded_gcode_allowed": False,
        "project": evidence["project"],
        "derived_inventory": evidence["derived_inventory"],
        "canonical_packages": evidence["canonical_packages"],
        "governing_drawings": evidence["governing_drawings"],
        "physical_qualification_blockers": evidence[
            "physical_qualification_blockers"
        ],
        "exact_hero": {"path": f"assets/{EXACT_HERO}", "sha256": hero_sha256},
        "preserved_rendering_history": {
            "path": f"assets/{PRESERVED_RENDERING}",
            "sha256": PRESERVED_RENDERING_SHA256,
        },
        "hybrid_r5_fallback": {
            "path": "reference/hybrid_r5",
            "revision": hybrid_manifest.get("revision"),
            "status": hybrid_manifest.get("status"),
            "source_manifest": "reference/hybrid_r5/SOURCE_MANIFEST.json",
            "byte_verified": True,
        },
        "license": _license_status(records),
        "verification": {
            "staged_source_check_passed": True,
            "staged_full_release_check_passed": True,
            "assembled_source_check_passed": True,
            "assembled_full_release_check_passed": True,
            "assembled_complete_test_suite_passed": True,
            "clean_import_path_required": True,
        },
        "file_count_excluding_manifest": len(records),
        "total_bytes_excluding_manifest": total_bytes,
        "files": list(records),
    }


def _write_manifest(root: Path, payload: Mapping[str, Any]) -> None:
    path = root / PUBLICATION_MANIFEST
    if _lexists(path):
        raise PublicationError(f"publication manifest already exists in staging tree: {path}")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def _publication_files(root: Path) -> set[str]:
    files: set[str] = set()
    for directory, names, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        if directory_path == root and ".git" in names:
            names.remove(".git")
        for name in names:
            child = directory_path / name
            info = child.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise PublicationError(f"linked/non-directory publication entry: {child}")
        for name in filenames:
            child = directory_path / name
            _require_regular_file(child)
            files.add(child.relative_to(root).as_posix())
    return files


def _assert_docs_mirror(root: Path) -> None:
    for source_name, root_name in ROOT_DOCUMENT_MAP:
        if (root / "docs" / source_name).read_bytes() != (root / root_name).read_bytes():
            raise PublicationError(f"root document differs from canonical docs/{source_name}")


def _audit_manifest_file_set(root: Path, manifest: Mapping[str, Any]) -> None:
    """Verify exact file allow-list, bytes, modes, and portable content."""

    records = manifest.get("files")
    if not isinstance(records, list):
        raise PublicationError("publication manifest has no file records")
    if manifest.get("file_count_excluding_manifest") != len(records):
        raise PublicationError("publication manifest file count is stale")
    expected: set[str] = set()
    total_bytes = 0
    for record in records:
        if not isinstance(record, dict):
            raise PublicationError("publication manifest contains a non-object file record")
        relative = record.get("destination")
        if not isinstance(relative, str):
            raise PublicationError("publication manifest file record lacks destination")
        _safe_relative(relative, label="publication manifest destination")
        _reject_forbidden_destination(relative)
        if relative in expected or relative == PUBLICATION_MANIFEST:
            raise PublicationError(f"duplicate/reserved publication manifest destination: {relative}")
        expected.add(relative)
        path = root / relative
        _require_regular_file(path)
        digest = record.get("sha256")
        mode = record.get("mode")
        size = record.get("bytes")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise PublicationError(f"invalid publication digest record: {relative}")
        if _sha256(path) != digest or path.stat().st_size != size:
            raise PublicationError(f"publication byte/hash drift: {relative}")
        if mode != f"{_file_mode(path):04o}":
            raise PublicationError(f"publication executable-mode drift: {relative}")
        total_bytes += int(size)
        _reject_host_paths(path)
        _reject_credentials(path)
    actual = _publication_files(root)
    expected_with_manifest = expected | {PUBLICATION_MANIFEST}
    if actual != expected_with_manifest:
        raise PublicationError(
            "publication contains missing/unlisted files: "
            f"missing={sorted(expected_with_manifest - actual)}, "
            f"extra={sorted(actual - expected_with_manifest)}"
        )
    if manifest.get("total_bytes_excluding_manifest") != total_bytes:
        raise PublicationError("publication manifest byte count is stale")
    _reject_host_paths(root / PUBLICATION_MANIFEST)
    _reject_credentials(root / PUBLICATION_MANIFEST)


def audit_publication(root: Path) -> dict[str, Any]:
    """Audit an assembled/published tree without changing it."""

    root = root.resolve()
    manifest = _load_json_strict(root / PUBLICATION_MANIFEST)
    if not isinstance(manifest, dict):
        raise PublicationError("publication manifest must be a JSON object")
    _audit_manifest_file_set(root, manifest)
    _assert_docs_mirror(root)

    if manifest.get("software_model_publication_eligible") is not True:
        raise PublicationError("publication must affirm software-model eligibility")
    if manifest.get("physical_installation_qualified") is not False:
        raise PublicationError("publication must remain physically unqualified")
    if manifest.get("production_release_eligible") is not False:
        raise PublicationError("publication must remain ineligible for production installation")
    blockers = manifest.get("physical_qualification_blockers")
    if not isinstance(blockers, list) or not blockers:
        raise PublicationError("publication must retain nonempty physical blockers")
    if manifest.get("tested_load_rating_exists") is not False:
        raise PublicationError("publication may not claim a tested load rating")
    if manifest.get("embedded_gcode_allowed") is not False:
        raise PublicationError("publication may not allow embedded G-code")
    _audit_license_marker(manifest)

    config = _load_json_strict(root / "config.json")
    project = config.get("project") if isinstance(config, dict) else None
    if not isinstance(project, dict):
        raise PublicationError("published config lacks project metadata")
    for key in ("name", "revision", "edition"):
        if manifest.get("project", {}).get(key) != project.get(key):
            raise PublicationError(f"publication project {key} differs from config")

    packages = manifest.get("canonical_packages")
    if not isinstance(packages, list) or not packages:
        raise PublicationError("publication manifest has no canonical package records")
    filenames = [item.get("filename") for item in packages if isinstance(item, dict)]
    if len(filenames) != len(packages) or not all(isinstance(name, str) for name in filenames):
        raise PublicationError("publication canonical package records are malformed")
    actual_packages = sorted(
        path.name for path in (root / "generated" / "model_only_3mf").glob("*.3mf")
    )
    if set(actual_packages) != set(filenames) or len(actual_packages) != len(filenames):
        raise PublicationError("published model-only package set differs from manifest")

    generated_manifest = _load_json_strict(root / "generated" / "manifest.json")
    generated_validation = _load_json_strict(root / "generated" / "validation.json")
    if not isinstance(generated_manifest, dict) or not isinstance(generated_validation, dict):
        raise PublicationError("published generated manifest/validation must be objects")
    for label, document in (
        ("generated manifest", generated_manifest),
        ("generated validation", generated_validation),
    ):
        if document.get("software_model_package_eligible") is not True:
            raise PublicationError(f"{label} does not affirm software-model eligibility")
        if document.get("physical_installation_qualified") is not False:
            raise PublicationError(f"{label} does not preserve physical qualification false")
        if document.get("production_release_eligible") is not False:
            raise PublicationError(f"{label} does not preserve production eligibility false")
        document_blockers = document.get("physical_qualification_blockers")
        if not isinstance(document_blockers, list) or not document_blockers:
            raise PublicationError(f"{label} has no physical qualification blockers")
        if document_blockers != blockers:
            raise PublicationError(f"{label} physical blockers differ from publication marker")
    plans, reports = _release_plan_and_report_maps(
        generated_manifest, generated_validation
    )
    package_ids: list[str] = []
    for item in packages:
        package_id = item.get("package_id")
        if not isinstance(package_id, str) or package_id in package_ids:
            raise PublicationError("published canonical package IDs are malformed or duplicated")
        package_ids.append(package_id)
        plan = plans.get(package_id)
        report = reports.get(package_id)
        if not isinstance(plan, dict) or not isinstance(report, dict):
            raise PublicationError(f"published package lacks plan/report evidence: {package_id}")
        if (
            item.get("filename") != plan.get("filename")
            or item.get("physical_object_count") != plan.get("physical_object_count")
            or item.get("validation_passed") is not True
            or report.get("all_checks_pass") is not True
        ):
            raise PublicationError(f"published canonical package evidence drift: {package_id}")
    derived_inventory = manifest.get("derived_inventory")
    derived_package_counts = (
        derived_inventory.get("package_counts")
        if isinstance(derived_inventory, dict)
        else None
    )
    if not isinstance(derived_package_counts, dict):
        raise PublicationError("publication lacks package-module-derived counts")
    for package_id, expected_count in derived_package_counts.items():
        if package_id not in package_ids:
            raise PublicationError(f"derived count names a noncanonical package: {package_id}")
        if plans[package_id].get("physical_object_count") != expected_count:
            raise PublicationError(f"derived package count differs from plan: {package_id}")

    hero = manifest.get("exact_hero")
    if not isinstance(hero, dict) or hero.get("path") != f"assets/{EXACT_HERO}":
        raise PublicationError("publication manifest does not select the exact 6 + 3 hero")
    if _sha256(root / f"assets/{EXACT_HERO}") != hero.get("sha256"):
        raise PublicationError("published exact hero digest differs from manifest")
    preserved = manifest.get("preserved_rendering_history")
    if not isinstance(preserved, dict) or preserved.get("path") != (
        f"assets/{PRESERVED_RENDERING}"
    ):
        raise PublicationError("publication manifest does not preserve rendering history")
    if (
        preserved.get("sha256") != PRESERVED_RENDERING_SHA256
        or _sha256(root / f"assets/{PRESERVED_RENDERING}")
        != PRESERVED_RENDERING_SHA256
    ):
        raise PublicationError("published preserved rendering history digest drift")
    _validate_hybrid_reference(root)
    return manifest


def _fsync_tree(root: Path) -> None:
    files: list[Path] = []
    directories: list[Path] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        directories.append(directory_path)
        for name in names:
            child = directory_path / name
            if child.is_symlink():
                raise PublicationError(f"cannot fsync linked publication directory: {child}")
        files.extend(directory_path / name for name in filenames)
    for path in sorted(files):
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        descriptor = os.open(path, os.O_RDONLY | directory_flag)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _exclusive_atomic_rename(source: Path, destination: Path) -> None:
    """Atomically rename a sibling directory only if destination is absent."""

    if source.parent.resolve() != destination.parent.resolve():
        raise PublicationError("exclusive atomic rename requires a common parent")
    if _lexists(destination):
        raise FileExistsError(f"refusing existing publication destination: {destination}")
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    library = ctypes.CDLL(None, use_errno=True)

    if sys.platform == "darwin":
        function = library.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(source_bytes, destination_bytes, 0x00000004)
    elif sys.platform.startswith("linux") and hasattr(library, "renameat2"):
        function = library.renameat2
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(-100, source_bytes, -100, destination_bytes, 0x00000001)
    elif os.name == "nt":
        # Windows os.rename is exclusive when the destination already exists.
        os.rename(source, destination)
        return
    else:
        raise PublicationError(
            "this platform has no supported atomic no-replace directory rename; refusing unsafe fallback"
        )
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise FileExistsError(
                f"publication destination appeared during commit: {destination}"
            )
        raise OSError(error, os.strerror(error), os.fspath(destination))


def _remove_owned_unpublished_stage(stage: Path, parent: Path, prefix: str) -> None:
    """Remove only this invocation's unpublished sibling staging directory."""

    if (
        stage.parent.resolve() != parent.resolve()
        or not stage.name.startswith(prefix)
        or stage.name in {"", ".", ".."}
    ):
        raise PublicationError(f"refusing unsafe unpublished-stage cleanup: {stage}")
    if _lexists(stage):
        shutil.rmtree(stage)


def _validate_paths(
    staged_release: Path, repository_root: Path, destination: Path
) -> tuple[Path, Path, Path]:
    staged_release = staged_release.resolve(strict=True)
    repository_root = repository_root.resolve(strict=True)
    destination = destination.absolute()
    if not staged_release.is_dir() or not repository_root.is_dir():
        raise PublicationError("staged release and repository root must be directories")
    if _lexists(destination):
        raise FileExistsError(f"refusing existing publication destination: {destination}")
    parent = destination.parent.resolve(strict=True)
    destination = parent / destination.name
    if not destination.name or destination.name in {".", ".."}:
        raise PublicationError("publication destination must name a new child tree")
    if _is_within(destination, repository_root) or _is_within(repository_root, destination):
        raise PublicationError("publication destination must be separate from the live repository")
    if _is_within(destination, staged_release) or _is_within(staged_release, destination):
        raise PublicationError("publication destination must be separate from the staged release")
    return staged_release, repository_root, destination


def publish_checked_release(
    *,
    staged_release: Path,
    repository_root: Path,
    destination: Path,
    python: Path,
    check_runner: CheckRunner | None = None,
    test_runner: TestRunner | None = None,
    committer: Committer | None = None,
) -> dict[str, Any]:
    """Build and atomically install one new, fully verified publication tree."""

    staged_release, repository_root, destination = _validate_paths(
        staged_release, repository_root, destination
    )
    python = python.absolute()
    check = check_runner or _run_release_check
    tests = test_runner or _run_complete_tests
    commit = committer or _exclusive_atomic_rename

    # Both checks occur before the first destination-parent write.
    check(python, staged_release, True)
    full_report = check(python, staged_release, False)
    evidence = _derive_release_evidence(staged_release, full_report)
    rules = publication_copy_rules(staged_release, repository_root)
    _audit_copy_rule_sources(rules)
    hero_sha256 = _validate_exact_hero(staged_release)
    hybrid_manifest = _validate_hybrid_reference(repository_root)

    prefix = f".{destination.name}.unpublished-"
    unpublished = Path(tempfile.mkdtemp(prefix=prefix, dir=destination.parent))
    committed = False
    try:
        records = _copy_rules(rules, unpublished)
        payload = _publication_manifest_payload(
            records, evidence, hero_sha256, hybrid_manifest
        )
        _write_manifest(unpublished, payload)
        audit_publication(unpublished)

        assembled_source = check(python, unpublished, True)
        assembled_full = check(python, unpublished, False)
        for key in ("project_name", "revision", "edition", "package_filenames", "package_counts"):
            if assembled_full.get("derived", {}).get(key) != full_report.get("derived", {}).get(key):
                raise PublicationError(f"assembled full-release derived evidence drift: {key}")
        if assembled_source.get("passed") is not True:
            raise PublicationError("assembled source check did not pass")
        tests(python, unpublished)
        audit_publication(unpublished)
        _fsync_tree(unpublished)
        _fsync_directory(destination.parent)
        commit(unpublished, destination)
        committed = True
        _fsync_directory(destination.parent)
        return payload
    finally:
        if not committed and _lexists(unpublished):
            _remove_owned_unpublished_stage(unpublished, destination.parent, prefix)


def _default_repository_root(script: Path) -> Path:
    if script.parent.name == "r6" and script.parent.parent.name == "development":
        return script.parents[2]
    return script.parent


def main(argv: list[str] | None = None) -> int:
    script = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument(
        "--publish-to",
        type=Path,
        help="exclusive new destination; never an existing tree or the live repository",
    )
    operation.add_argument(
        "--audit-publication",
        type=Path,
        metavar="ROOT",
        help="read-only audit of an already assembled publication tree",
    )
    parser.add_argument(
        "--staged-release", type=Path, default=script.parent, help="fully generated staged r6 tree"
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=_default_repository_root(script),
        help="live repository used only for metadata and preserved hybrid r5 source",
    )
    parser.add_argument(
        "--python", type=Path, default=Path(sys.executable), help="Python with pinned r6 dependencies"
    )
    args = parser.parse_args(argv)
    try:
        if args.audit_publication is not None:
            manifest = audit_publication(args.audit_publication)
            print(
                json.dumps(
                    {
                        "audit": "passed",
                        "revision": manifest["project"]["revision"],
                        "file_count": manifest["file_count_excluding_manifest"],
                        "physical_installation_qualified": False,
                        "production_release_eligible": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        payload = publish_checked_release(
            staged_release=args.staged_release,
            repository_root=args.repository_root,
            destination=args.publish_to,
            python=args.python,
        )
    except (OSError, PublicationError, ValueError) as exc:
        print(f"PUBLICATION REFUSED: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "publication": "created",
                "destination": str(args.publish_to.absolute()),
                "revision": payload["project"]["revision"],
                "file_count": payload["file_count_excluding_manifest"],
                "physical_installation_qualified": False,
                "production_release_eligible": False,
                "license_status": payload["license"]["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
