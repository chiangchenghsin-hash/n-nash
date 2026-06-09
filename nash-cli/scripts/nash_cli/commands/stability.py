#!/usr/bin/env python3
"""nash stability — Numerical stability validation for simulation results.

Usage:
  uv run nash stability --data multi_seed.json          # from --seeds output
  uv run nash stability --data results.json --preset social_trust_commons   # single seed + env info
  uv run nash stability --sweep sweep_results.json      # from sweep output
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.primitives import VariableDecl, PrimitiveLibrary
from src.stability_validator import StabilityValidator, StabilityResult


def cmd_stability(args) -> dict:
    """Run numerical stability validation.

    Three modes:
      1. --data points to a --seeds multi-seed JSON → perturbation sensitivity
      2. --data points to a single-seed JSON + --preset → boundary check
      3. --sweep points to a sweep JSON → cross-parameter stability

    Mode 1 is the primary use case.
    """
    from src.stability_validator import StabilityValidator

    validator = StabilityValidator()

    # ---- Mode 3: sweep analysis ----
    sweep_path = getattr(args, "sweep", None)
    if sweep_path:
        return _validate_sweep(sweep_path, validator)

    # ---- Mode 1 & 2: data file analysis ----
    data_path = getattr(args, "data", None)
    if not data_path:
        return {"error": "Either --data <file> or --sweep <file> is required"}

    data = _load_json(data_path)

    # Detect multi-seed vs single-seed
    if "per_seed_results" in data:
        return _validate_multi_seed(data, validator)

    return _validate_single_seed(data, args, validator)


# ---------------------------------------------------------------------------
# Mode 1: multi-seed perturbation sensitivity
# ---------------------------------------------------------------------------

def _validate_multi_seed(data: dict, validator: StabilityValidator) -> dict:
    per_seed = data.get("per_seed_results", [])
    preset = data.get("preset", "")

    # Gather declarations from primitives
    declarations = _get_declarations(preset)

    result = validator.validate_from_seeds(per_seed, declarations)

    return _format_output(result, {
        "mode": "multi_seed",
        "num_seeds": len(per_seed),
        "preset": preset,
        "aggregated_metrics": data.get("aggregated_metrics", {}),
    })


# ---------------------------------------------------------------------------
# Mode 2: single-seed boundary check
# ---------------------------------------------------------------------------

def _validate_single_seed(data: dict, args, validator: StabilityValidator) -> dict:
    preset = getattr(args, "preset", None) or data.get("preset", "") or data.get("environment_type", "")
    metrics = data.get("final_metrics", {})

    declarations = _get_declarations(preset)

    boundary_ok, boundary_warnings = StabilityValidator.check_boundary_conditions(
        metrics, declarations
    )

    result = StabilityResult(
        stable=boundary_ok,
        stability_level="high" if boundary_ok else "low",
        boundary_safe=boundary_ok,
        perturbation_sensitivity=0.0,
        step_size_sensitivity=0.0,
        warnings=boundary_warnings,
    )
    if not boundary_ok:
        result.recommendations.append("检查动力学方程是否引入了非法状态")
        result.stable = False
        result.stability_level = "unstable"

    return _format_output(result, {
        "mode": "single_seed",
        "preset": preset,
        "environment_type": data.get("environment_type", ""),
        "converged": data.get("converged"),
    })


# ---------------------------------------------------------------------------
# Mode 3: sweep-based stability
# ---------------------------------------------------------------------------

def _validate_sweep(sweep_path: str, validator: StabilityValidator) -> dict:
    data = _load_json(sweep_path)
    sweep_results = data.get("results", [])

    sensitivity = StabilityValidator.from_sweep_results(sweep_results)

    # Build result from sensitivity alone
    if sensitivity <= validator.domain_low:
        level = "high"
        stable = True
    elif sensitivity <= validator.domain_medium:
        level = "medium"
        stable = True
    elif sensitivity <= validator.domain_high:
        level = "low"
        stable = True
    else:
        level = "unstable"
        stable = False

    result = StabilityResult(
        stable=stable,
        stability_level=level,
        perturbation_sensitivity=sensitivity,
        max_deviation=sensitivity,
    )

    if not stable:
        result.warnings.append(f"跨参数指标高度敏感 (CV={sensitivity:.2%})")
        result.recommendations.append("存在参数悬崖风险 — 对参数范围做更细粒度扫描")

    return _format_output(result, {
        "mode": "sweep",
        "parameter": data.get("summary", {}).get("parameter", ""),
        "num_configs": sweep_results.__len__(),
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(json.dumps({"error": f"File not found: {path}"}, ensure_ascii=True),
              file=sys.stderr)
        sys.exit(1)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_declarations(preset: str) -> List[VariableDecl]:
    """Map preset / env_id → primitive VariableDecl list for boundary checks."""
    # Map short IDs and env_ids to primitive_ids
    _PRESET_TO_PRIMITIVE = {
        "social_trust_commons": "social_trust_commons",
        "social_trust": "social_trust_commons",
        "common_pool_resource": "common_pool_resource",
        "common_pool": "common_pool_resource",
        "hawk_dove": "hawk_dove",
        "prisoners_dilemma": "repeated_prisoners_dilemma",
        "repeated_prisoners_dilemma": "repeated_prisoners_dilemma",
        "public_goods": "public_goods",
        "spence_signaling": "spence_signaling",
        "spence": "spence_signaling",
        "vickrey_auction": None,   # No primitive registered
        "vickrey": None,
        "matching": None,
        "two_sided_matching": None,
        "auction_common_value": None,
    }

    prim_id = _PRESET_TO_PRIMITIVE.get(preset, preset)
    if prim_id is None:
        return []

    spec = PrimitiveLibrary.get(prim_id)
    if spec is None:
        return []

    return spec.state_variables


def _format_output(result: StabilityResult, meta: dict) -> dict:
    return {
        "status": "completed",
        "meta": meta,
        **result.to_dict(),
    }
