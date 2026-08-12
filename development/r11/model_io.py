"""R11 neutral mesh writer loaded from the frozen R10 implementation.

The complete R10 ``model_io.py`` source is SHA-256 verified *before* it is
compiled or executed.  R10 performs the same check on its R9 predecessor, so
R11 inherits the audited float32 triangle, deterministic binary STL,
model-only 3MF, exclusive-write, and atomic-publication contracts without
copying or weakening them.

This module cannot emit a slicer profile, toolpath, printer command, or
G-code.  It only specializes human-readable neutral-model metadata.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import types


R11_ROOT = Path(__file__).resolve().parent
R10_MODEL_IO = R11_ROOT.parent / "r10" / "model_io.py"
EXPECTED_R10_MODEL_IO_SHA256 = (
    "13dbdb4914f089908aa9b9267c0eb99aea615ddc852e39ce7e7ad73f323392f8"
)

_R10_MODEL_IO_BYTES = R10_MODEL_IO.read_bytes()
if hashlib.sha256(_R10_MODEL_IO_BYTES).hexdigest() != EXPECTED_R10_MODEL_IO_SHA256:
    raise RuntimeError("Frozen R10 neutral model writer changed before R11 import")

_MODULE_NAME = "_story_corner_r11_frozen_r10_model_io"
_BASE = types.ModuleType(_MODULE_NAME)
_BASE.__file__ = str(R10_MODEL_IO)
sys.modules[_MODULE_NAME] = _BASE
exec(
    compile(_R10_MODEL_IO_BYTES, str(R10_MODEL_IO), "exec"),
    _BASE.__dict__,
)

_BASE.APPLICATION_NAME = "Story Corner R11 deterministic neutral model writer"
_BASE.MATERIAL_NAME = "SUNLU standard black PETG R11 qualification candidate"
_BASE.STL_HEADER = b"Story Corner R11 deterministic qualification STL"

SerializedMesh = _BASE.SerializedMesh
ModelObject = _BASE.ModelObject
ThreeMFInspection = _BASE.ThreeMFInspection
sha256_bytes = _BASE.sha256_bytes
sha256_file = _BASE.sha256_file
write_bytes_exclusive = _BASE.write_bytes_exclusive
canonicalize_mesh = _BASE.canonicalize_mesh
canonical_triangle_digest = _BASE.canonical_triangle_digest
serialized_mesh_evidence = _BASE.serialized_mesh_evidence
binary_stl_bytes = _BASE.binary_stl_bytes
write_binary_stl = _BASE.write_binary_stl
read_binary_stl = _BASE.read_binary_stl
model_only_3mf_bytes = _BASE.model_only_3mf_bytes
write_model_only_3mf = _BASE.write_model_only_3mf
inspect_model_only_3mf = _BASE.inspect_model_only_3mf
atomic_publish_directory = _BASE.atomic_publish_directory


__all__ = (
    "EXPECTED_R10_MODEL_IO_SHA256",
    "ModelObject",
    "SerializedMesh",
    "ThreeMFInspection",
    "atomic_publish_directory",
    "binary_stl_bytes",
    "canonical_triangle_digest",
    "canonicalize_mesh",
    "inspect_model_only_3mf",
    "model_only_3mf_bytes",
    "read_binary_stl",
    "serialized_mesh_evidence",
    "sha256_bytes",
    "sha256_file",
    "write_binary_stl",
    "write_bytes_exclusive",
    "write_model_only_3mf",
)
