"""Небольшие пользовательские настройки SDC-Studio."""

from __future__ import annotations

import json
from pathlib import Path


APP_DIR = Path.home() / ".sdc-studio"
SETTINGS_FILE = APP_DIR / "settings.json"


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(data: dict) -> None:
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    except OSError:
        # Настройка темы не должна ломать запуск приложения.
        pass
