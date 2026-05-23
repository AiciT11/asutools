import json
import os
from pathlib import Path
from typing import Any

from .paths import (
    CATEGORIES_JSON,
    ENVIRONMENTS_JSON,
    SETTINGS_JSON,
    TOOLS_JSON,
    ensure_data_dir,
)


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write(path: Path, data: Any) -> None:
    ensure_data_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_tools() -> list[dict]:
    tools = _read(TOOLS_JSON, [])
    # 展开 ~ 为实际 home 目录，支持跨用户迁移
    for tool in tools:
        if isinstance(tool.get("path"), str):
            tool["path"] = os.path.expanduser(tool["path"])
    return tools


def save_tools(tools: list[dict]) -> None:
    _write(TOOLS_JSON, tools)


def load_categories() -> list[dict]:
    return _read(CATEGORIES_JSON, [])


def save_categories(categories: list[dict]) -> None:
    _write(CATEGORIES_JSON, categories)


def load_environments() -> dict:
    data = _read(ENVIRONMENTS_JSON, {"environments": [], "defaults": {}})
    # 展开 ~ 为实际 home 目录，支持跨用户迁移
    for env in data.get("environments", []):
        if isinstance(env.get("path"), str):
            env["path"] = os.path.expanduser(env["path"])
    return data


def save_environments(envs: dict) -> None:
    _write(ENVIRONMENTS_JSON, envs)


def load_settings() -> dict:
    return _read(SETTINGS_JSON, {"theme": "dark"})


def save_settings(settings: dict) -> None:
    _write(SETTINGS_JSON, settings)
