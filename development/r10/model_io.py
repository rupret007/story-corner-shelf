"""R10-neutral mesh writer loaded from the frozen R9 implementation.

The R9 source is verified *before* it is compiled or executed.  R9 in turn
verifies its frozen R8 serialization engine before use.  R10 only specializes
human-readable metadata; the audited float32 triangle, binary STL, and
model-only 3MF contracts remain unchanged.

This module cannot emit a slicer profile, toolpath, or G-code.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import types


R10_ROOT = Path(__file__).resolve().parent
R9_MODEL_IO = R10_ROOT.parent / "r9" / "model_io.py"
EXPECTED_R9_MODEL_IO_SHA256 = (
    "74f0451d66d8e72316d8d17405bd10860485783cd16f7033a0e56dbf88df55f5"
)

_R9_MODEL_IO_BYTES = R9_MODEL_IO.read_bytes()
if hashlib.sha256(_R9_MODEL_IO_BYTES).hexdigest() != EXPECTED_R9_MODEL_IO_SHA256:
    raise RuntimeError("Frozen R9 neutral model writer changed before R10 import")

_MODULE_NAME = "_story_corner_r10_frozen_r9_model_io"
_BASE = types.ModuleType(_MODULE_NAME)
_BASE.__file__ = str(R9_MODEL_IO)
sys.modules[_MODULE_NAME] = _BASE
exec(
    compile(_R9_MODEL_IO_BYTES, str(R9_MODEL_IO), "exec"),
    _BASE.__dict__,
)

_BASE.APPLICATION_NAME = "Story Corner R10 deterministic neutral model writer"
_BASE.MATERIAL_NAME = "SUNLU standard black PETG R10 qualification candidate"
_BASE.STL_HEADER = b"Story Corner R10 deterministic qualification STL"

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
    "EXPECTED_R9_MODEL_IO_SHA256",
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
