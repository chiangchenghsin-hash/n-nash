#!/bin/bash
# NASH CLI wrapper — run from project root
# Usage: ./scripts/nash_cli/nash.sh run --preset hawk_dove --rounds 200

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"
python -m scripts.nash_cli.main "$@"
