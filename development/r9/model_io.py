"""R9-neutral mesh writer built from the frozen R8 serialization engine.

R8's deterministic STL/3MF implementation is loaded as an immutable source
dependency under a private module name.  Only human-readable writer metadata
is specialized for R9; the canonical float32 triangle format deliberately
remains compatible with the audited R8 geometry digest contract.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import types


R9_ROOT = Path(__file__).resolve().parent
R8_MODEL_IO = R9_ROOT.parent / "r8" / "model_io.py"
EXPECTED_R8_MODEL_IO_SHA256 = (
    "28c26fb7b73d6993c77d19eb8555ad65d78d327d658a86d6f3b37fd74882475b"
)
_R8_MODEL_IO_BYTES = R8_MODEL_IO.read_bytes()
if hashlib.sha256(_R8_MODEL_IO_BYTES).hexdigest() != EXPECTED_R8_MODEL_IO_SHA256:
    raise RuntimeError("Frozen R8 neutral model writer changed before R9 import")
_MODULE_NAME = "_story_corner_r9_frozen_r8_model_io"
_BASE = types.ModuleType(_MODULE_NAME)
_BASE.__file__ = str(R8_MODEL_IO)
sys.modules[_MODULE_NAME] = _BASE
exec(
    compile(_R8_MODEL_IO_BYTES, str(R8_MODEL_IO), "exec"),
    _BASE.__dict__,
)

_BASE.APPLICATION_NAME = "Story Corner R9 deterministic neutral model writer"
_BASE.MATERIAL_NAME = "Black PETG R9 qualification candidate"
_BASE.STL_HEADER = b"Story Corner R9 deterministic qualification STL"

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
    "EXPECTED_R8_MODEL_IO_SHA256",
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
