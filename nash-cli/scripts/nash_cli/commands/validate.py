#!/usr/bin/env python3
"""nash validate — Statistical hypothesis testing and Nobel benchmark validation."""

import json
import sys


def cmd_validate(args) -> dict:
    data = None
    if args.data:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)

    results = {}

    if args.type in ("statistical", "both"):
        results["statistical"] = _validate_statistical(args, data)

    if args.type in ("nobel", "both"):
        results["nobel"] = _validate_nobel(args, data)

    return results


def _validate_statistical(args, data) -> dict:
    from src.statistical_validator import StatisticalValidator

    validator = StatisticalValidator(alpha=0.05)

    if data and "gini_history" in data:
        gini_values = data["gini_history"]
        hostility_values = data.get("hostility_history", [])

        gini_result = validator.compare_to_baseline(
            experimental=gini_values[-10:] if len(gini_values) >= 10 else gini_values,
            baseline=[args.baseline_gini],
        )

        hostility_result = None
        if hostility_values:
            hostility_result = validator.compare_to_baseline(
                experimental=hostility_values[-10:],
                baseline=[args.baseline_hostility],
            )

        final_gini = float(gini_values[-1])
        return {
            "gini": {
                "final_value": final_gini,
                "p_value": gini_result["p_value"],
                "confidence_level": gini_result["confidence_level"],
                "effect_size": gini_result["effect_size"],
                "significant": gini_result["significant"],
                "interpretation": _interpret_gini(final_gini),
            },
            "hostility": hostility_result,
        }
    else:
        # No data file: return capability info
        return {
            "message": "No simulation data provided. Use --data to specify results JSON.",
            "capabilities": ["t_test", "mann_whitney", "ks_test", "compare_to_baseline"],
        }


def _validate_nobel(args, data) -> dict:
    from src.validators.nobel_validator import NobelValidator

    validator = NobelValidator()

    if data and "environment" in data and "final_metrics" in data:
        env_type = data["environment"]
        metrics = data["final_metrics"]
        config = data.get("config", {})
        result = validator.validate(env_type, metrics, config)
        return {
            "model_name": result.model_name,
            "nobel_year": result.nobel_year,
            "hypothesis_supported": result.hypothesis_supported,
            "confidence": result.confidence,
            "metrics": result.metrics,
            "conclusion": result.conclusion,
            "suggestions": result.suggestions or [],
        }
    else:
        return {
            "message": "No environment data provided. Use --data with environment run results.",
            "supported_models": list(validator.NOBEL_MODELS.keys()),
        }


def _interpret_gini(gini: float) -> str:
    if gini < 0.2:
        return "高度平等"
    elif gini < 0.4:
        return "比较平等"
    elif gini < 0.6:
        return "中等不平等"
    elif gini < 0.8:
        return "高度不平等"
    else:
        return "极端不平等"
