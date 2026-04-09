import json
import os
from typing import Tuple

from dotenv import load_dotenv

from app.models import AppConfig
from app.paths import config_file, localization_file


def load_localization(filename: str = "localization.json") -> Tuple[dict, list[str]]:
    path = localization_file(filename)
    if not path.exists():
        return {}, []

    with path.open("r", encoding="utf-8") as handle:
        localization = json.load(handle)

    return localization, list(localization.keys())


def load_app_config(filename: str = "config.json") -> AppConfig:
    path = config_file(filename)
    if not path.exists():
        return AppConfig()

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    return AppConfig(
        font_size=data.get("font_size", 12),
        current_lang=data.get("current_lang", "PL"),
        default_prompt=data.get("default_prompt", "prompt_handwritten_pol_xx_century.txt"),
        api_key=data.get("api_key", ""),
        tts_lang=data.get("tts_lang", "pl"),
    )


def save_app_config(app_config: AppConfig, filename: str = "config.json") -> None:
    path = config_file(filename)
    data = {}

    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

    data["font_size"] = app_config.font_size
    data["current_lang"] = app_config.current_lang
    data["default_prompt"] = app_config.default_prompt
    data["tts_lang"] = app_config.tts_lang
    data.setdefault("api_key", app_config.api_key or "")

    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle)


def load_api_key_from_env() -> str:
    load_dotenv()
    return os.environ.get("GEMINI_API_KEY", "")
