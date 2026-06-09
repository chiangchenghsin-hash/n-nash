from typing import Dict, Any, Optional
import json
import yaml
from pathlib import Path
import logging

from src.contracts import SimulationConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: Optional[SimulationConfig] = None
        self._load_default_config()

    def _load_default_config(self):
        self.config = SimulationConfig()

    def load_config(self, config_path: str) -> SimulationConfig:
        try:
            path = Path(config_path)
            
            if not path.exists():
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return self.config
            
            if path.suffix in ['.yaml', '.yml']:
                with open(path, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f)
            elif path.suffix == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
            else:
                logger.warning(f"Unsupported config format: {path.suffix}, using defaults")
                return self.config
            
            self.config = SimulationConfig(**config_dict)
            self.config_path = config_path
            
            logger.info(f"Loaded config from {config_path}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return self.config

    def save_config(self, config_path: Optional[str] = None) -> bool:
        try:
            if self.config is None:
                logger.error("No config to save")
                return False
            
            path = Path(config_path or self.config_path or "config.yaml")
            
            config_dict = self.config.model_dump()
            
            if path.suffix in ['.yaml', '.yml']:
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            elif path.suffix == '.json':
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
            else:
                logger.warning(f"Unsupported config format: {path.suffix}, using YAML")
                path = path.with_suffix('.yaml')
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Saved config to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def update_config(self, **kwargs) -> SimulationConfig:
        try:
            if self.config is None:
                self.config = SimulationConfig()
            
            config_dict = self.config.model_dump()
            config_dict.update(kwargs)
            
            self.config = SimulationConfig(**config_dict)
            
            logger.info(f"Updated config with {len(kwargs)} changes")
            return self.config

        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return self.config

    def get_config(self) -> SimulationConfig:
        if self.config is None:
            self.config = SimulationConfig()
        return self.config

    def get_value(self, key: str, default: Any = None) -> Any:
        if self.config is None:
            return default
        
        config_dict = self.config.model_dump()
        return config_dict.get(key, default)

    def validate_config(self) -> Dict[str, Any]:
        try:
            if self.config is None:
                return {"valid": False, "errors": ["No config loaded"]}
            
            config_dict = self.config.model_dump()
            errors = []
            warnings = []
            
            if config_dict['num_agents'] < 10:
                errors.append("num_agents must be at least 10")
            
            if config_dict['num_agents'] > 1000:
                warnings.append("num_agents > 1000 may cause performance issues")
            
            if config_dict['width'] < 10 or config_dict['height'] < 10:
                errors.append("Grid dimensions must be at least 10x10")
            
            if config_dict['center_pool'] < 0:
                errors.append("center_pool must be non-negative")
            
            if config_dict['base_gain'] < 0:
                errors.append("base_gain must be non-negative")
            
            if config_dict['metabolism'] < 0:
                errors.append("metabolism must be non-negative")
            
            if config_dict['mutation_rate'] < 0 or config_dict['mutation_rate'] > 1:
                errors.append("mutation_rate must be in [0, 1]")
            
            if config_dict['mutation_amount'] < 0 or config_dict['mutation_amount'] > 0.5:
                errors.append("mutation_amount must be in [0, 0.5]")
            
            valid = len(errors) == 0
            
            return {
                "valid": valid,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }

    def reset_to_defaults(self) -> SimulationConfig:
        self.config = SimulationConfig()
        logger.info("Reset config to defaults")
        return self.config

    def export_config(self, export_format: str = 'dict') -> Any:
        if self.config is None:
            return None
        
        config_dict = self.config.model_dump()
        
        if export_format == 'dict':
            return config_dict
        elif export_format == 'json':
            return json.dumps(config_dict, indent=2, ensure_ascii=False)
        elif export_format == 'yaml':
            return yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
        else:
            logger.warning(f"Unknown export format: {export_format}, returning dict")
            return config_dict

    def import_config(self, config_data: Any, config_format: str = 'dict') -> SimulationConfig:
        try:
            if config_format == 'dict':
                config_dict = config_data
            elif config_format == 'json':
                config_dict = json.loads(config_data)
            elif config_format == 'yaml':
                config_dict = yaml.safe_load(config_data)
            else:
                logger.warning(f"Unknown import format: {config_format}, treating as dict")
                config_dict = config_data
            
            self.config = SimulationConfig(**config_dict)
            
            logger.info(f"Imported config from {config_format}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return self.config

    def create_experiment_config(self, experiment_name: str, 
                                 base_config: Optional[SimulationConfig] = None) -> SimulationConfig:
        try:
            base = base_config or self.config or SimulationConfig()
            
            config_dict = base.model_dump()
            config_dict['experiment_name'] = experiment_name
            
            self.config = SimulationConfig(**config_dict)
            
            logger.info(f"Created experiment config: {experiment_name}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to create experiment config: {e}")
            return self.config

    def compare_configs(self, other_config: SimulationConfig) -> Dict[str, Any]:
        try:
            if self.config is None:
                return {"error": "No config loaded"}
            
            self_dict = self.config.model_dump()
            other_dict = other_config.model_dump()
            
            differences = {}
            
            for key in self_dict:
                if key in other_dict:
                    if self_dict[key] != other_dict[key]:
                        differences[key] = {
                            "current": self_dict[key],
                            "other": other_dict[key]
                        }
            
            return {
                "differences": differences,
                "num_differences": len(differences)
            }

        except Exception as e:
            logger.error(f"Config comparison failed: {e}")
            return {"error": str(e)}
