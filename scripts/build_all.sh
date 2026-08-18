#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if [[ "${SKIP_BAMBU:-0}" == "1" && "${REQUIRE_BAMBU:-0}" == "1" ]]; then
  echo "SKIP_BAMBU=1 and REQUIRE_BAMBU=1 are mutually exclusive." >&2
  exit 2
fi

"$PYTHON_BIN" "$PROJECT_DIR/scripts/generate_shelf_parts.py"

VALIDATOR_ARGS=()
if [[ "${SKIP_BAMBU:-0}" == "1" ]]; then
  VALIDATOR_ARGS+=("--skip-bambu")
elif [[ "${REQUIRE_BAMBU:-0}" == "1" ]]; then
  VALIDATOR_ARGS+=("--require-bambu")
fi

"$PYTHON_BIN" -m unittest discover -s "$PROJECT_DIR/tests" -p "test_*.py"
"$PYTHON_BIN" "$PROJECT_DIR/scripts/validate_model_3mf.py" "${VALIDATOR_ARGS[@]}"
"$PYTHON_BIN" "$PROJECT_DIR/scripts/check_repository.py"

echo "Generated validated model-only 3MFs. No embedded G-code was created."
echo "Confirm printer, nozzle, build plate, and PETG before adding any slicer profile or G-code."
