from __future__ import annotations

from dataclasses import dataclass
import importlib
import inspect
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class EnvironmentSpec:
    env_id: str
    short_id: str
    module_name: str
    creator_name: str
    creator: Callable[..., Tuple[Any, Dict[str, Any]]]
    env_class: type
    default_config: Dict[str, Any]


_ENV_REGISTRY: Optional[Dict[str, EnvironmentSpec]] = None
_SHORT_TO_LONG: Optional[Dict[str, str]] = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _environments_dir() -> Path:
    return _project_root() / "src" / "environments"


def _short_id_for(env_id: str) -> str:
    if env_id == "auction_common_value":
        return env_id
    if env_id.startswith("repeated_"):
        return env_id.removeprefix("repeated_")
    if env_id.endswith("_resource"):
        return env_id.removesuffix("_resource")
    if env_id.endswith("_auction"):
        return env_id.removesuffix("_auction")
    if env_id.endswith("_signaling"):
        return env_id.removesuffix("_signaling")
    if env_id == "two_sided_matching":
        return "matching"
    return env_id


def _safe_creator_kwargs(creator: Callable[..., Any]) -> Dict[str, Any]:
    sig = inspect.signature(creator)
    kwargs: Dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name in ("num_rounds",):
            kwargs[name] = 1
        elif name in ("num_agents", "num_workers", "num_bidders"):
            kwargs[name] = 2
        elif name in ("num_firms",):
            kwargs[name] = 1
        elif name in ("num_men", "num_women"):
            kwargs[name] = 1
        elif param.default is inspect._empty:
            kwargs[name] = 1
    return kwargs


def get_environment_registry() -> Dict[str, EnvironmentSpec]:
    global _ENV_REGISTRY, _SHORT_TO_LONG
    if _ENV_REGISTRY is not None and _SHORT_TO_LONG is not None:
        return _ENV_REGISTRY

    env_dir = _environments_dir()
    if not env_dir.exists():
        raise RuntimeError(f"Missing environments directory: {env_dir}")

    registry: Dict[str, EnvironmentSpec] = {}
    short_to_long: Dict[str, str] = {}

    for file in sorted(env_dir.glob("*.py")):
        if file.name in ("__init__.py", "base.py"):
            continue

        try:
            module_name = f"src.environments.{file.stem}"
            mod = importlib.import_module(module_name)

            creator_candidates = sorted(
                name
                for name, obj in vars(mod).items()
                if callable(obj) and name.startswith("create_")
            )
            if not creator_candidates:
                continue

            creator_name = creator_candidates[0]
            creator = getattr(mod, creator_name)
            env, cfg = creator(**_safe_creator_kwargs(creator))

            env_id = cfg.get("environment", {}).get("type", "")
            if not env_id:
                continue

            short_id = _short_id_for(env_id)
            spec = EnvironmentSpec(
                env_id=env_id,
                short_id=short_id,
                module_name=module_name,
                creator_name=creator_name,
                creator=creator,
                env_class=env.__class__,
                default_config=cfg,
            )

            registry[env_id] = spec
            short_to_long[short_id] = env_id
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to load environment {file.stem}: {e}")
            continue

    _ENV_REGISTRY = registry
    _SHORT_TO_LONG = short_to_long
    return _ENV_REGISTRY


def list_presets() -> List[str]:
    get_environment_registry()
    assert _SHORT_TO_LONG is not None
    return sorted(_SHORT_TO_LONG.keys())


def resolve_environment_id(name: str) -> Optional[str]:
    registry = get_environment_registry()
    if name in registry:
        return name
    assert _SHORT_TO_LONG is not None
    return _SHORT_TO_LONG.get(name)


def get_environment_spec(name: str) -> Optional[EnvironmentSpec]:
    env_id = resolve_environment_id(name)
    if not env_id:
        return None
    registry = get_environment_registry()
    return registry.get(env_id)


def build_run_config(spec: EnvironmentSpec, agents: int, rounds: int) -> Dict[str, Any]:
    import copy

    cfg = copy.deepcopy(spec.default_config)
    params = cfg.setdefault("parameters", {})

    if "num_agents" in params:
        params["num_agents"] = {"value": agents}
    elif "num_bidders" in params:
        params["num_bidders"] = {"value": agents}
    elif "num_workers" in params:
        params["num_workers"] = {"value": agents}
    elif "num_men" in params or "num_women" in params:
        half = max(1, agents // 2)
        if "num_men" in params:
            params["num_men"] = {"value": half}
        if "num_women" in params:
            params["num_women"] = {"value": half}

    if "num_rounds" in params:
        params["num_rounds"] = {"value": rounds}

    return cfg
