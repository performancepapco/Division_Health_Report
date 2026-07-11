"""Loads pipeline_config.yaml — the single source of truth for section
templates and validation. generate_templates.py and pipeline/validate.py
both go through this module so they can never read the config differently.
"""
from pathlib import Path
import yaml

BASE = Path(__file__).parent.parent
CONFIG_PATH = BASE / "pipeline_config.yaml"


class ConfigError(Exception):
    pass


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if "sections" not in cfg:
        raise ConfigError(f"{path}: missing top-level 'sections' key")
    return cfg


def get_section(cfg: dict, name: str) -> dict:
    try:
        return cfg["sections"][name]
    except KeyError:
        known = ", ".join(sorted(cfg["sections"]))
        raise ConfigError(f"Unknown section '{name}'. Known sections: {known}")


def section_names(cfg: dict) -> list[str]:
    return list(cfg["sections"].keys())
