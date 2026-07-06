import json
from json import JSONDecodeError
from typing import Tuple

from app.models import AppConfig
from app.paths import config_file, localization_file
from services.gemini_service import (
    DEFAULT_ANALYSIS_MODEL,
    DEFAULT_API_TIMEOUT_SECONDS,
    DEFAULT_BOX_MODEL,
    DEFAULT_FIX_MODEL,
    DEFAULT_HTR_MODEL,
    normalize_model_selection,
)
from services.ollama_service import DEFAULT_OLLAMA_BASE_URL, DEFAULT_OLLAMA_MODEL, normalize_base_url


def _normalize_provider(provider: str | None) -> str:
    return provider if provider in {"gemini", "ollama"} else "gemini"


def _load_json_file(path):
    if not path.exists() or path.stat().st_size == 0:
        return {}

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except JSONDecodeError:
        return {}


def load_localization(filename: str = "localization.json") -> Tuple[dict, list[str]]:
    path = localization_file(filename)
    if not path.exists():
        return {}, []

    with path.open("r", encoding="utf-8") as handle:
        localization = json.load(handle)

    return localization, list(localization.keys())


def load_app_config(filename: str = "config.json") -> AppConfig:
    path = config_file(filename)
    data = _load_json_file(path)
    timeout_seconds = data.get("api_timeout_seconds", DEFAULT_API_TIMEOUT_SECONDS)
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        timeout_seconds = DEFAULT_API_TIMEOUT_SECONDS
    timeout_seconds = max(30, min(timeout_seconds, 3600))

    return AppConfig(
        font_size=data.get("font_size", 12),
        current_lang=data.get("current_lang", "PL"),
        default_prompt=data.get("default_prompt", "prompt_handwritten_pol_xx_century.txt"),
        last_folder=data.get("last_folder", ""),
        llm_provider=_normalize_provider(data.get("llm_provider", "gemini")),
        api_key=data.get("api_key", ""),
        htr_model=normalize_model_selection("htr", data.get("htr_model", DEFAULT_HTR_MODEL)),
        fix_model=normalize_model_selection(
            "fix", data.get("fix_model", data.get("htr_model", DEFAULT_FIX_MODEL))
        ),
        analysis_model=normalize_model_selection(
            "analysis", data.get("analysis_model", DEFAULT_ANALYSIS_MODEL)
        ),
        box_model=normalize_model_selection("box", data.get("box_model", DEFAULT_BOX_MODEL)),
        ollama_base_url=normalize_base_url(data.get("ollama_base_url", DEFAULT_OLLAMA_BASE_URL)),
        ollama_htr_model=data.get("ollama_htr_model", DEFAULT_OLLAMA_MODEL) or DEFAULT_OLLAMA_MODEL,
        ollama_fix_model=data.get("ollama_fix_model", data.get("ollama_htr_model", DEFAULT_OLLAMA_MODEL))
        or DEFAULT_OLLAMA_MODEL,
        ollama_analysis_model=data.get("ollama_analysis_model", data.get("ollama_htr_model", DEFAULT_OLLAMA_MODEL))
        or DEFAULT_OLLAMA_MODEL,
        ollama_box_model=data.get("ollama_box_model", data.get("ollama_htr_model", DEFAULT_OLLAMA_MODEL))
        or DEFAULT_OLLAMA_MODEL,
        ollama_remove_table_headers=bool(data.get("ollama_remove_table_headers", False)),
        ollama_pretty_html=bool(data.get("ollama_pretty_html", True)),
        api_timeout_seconds=timeout_seconds,
        stream_transcription=bool(data.get("stream_transcription", True)),
    )


def save_app_config(app_config: AppConfig, filename: str = "config.json") -> None:
    path = config_file(filename)
    data = _load_json_file(path)

    data["font_size"] = app_config.font_size
    data["current_lang"] = app_config.current_lang
    data["default_prompt"] = app_config.default_prompt
    data["last_folder"] = app_config.last_folder or ""
    data["llm_provider"] = _normalize_provider(app_config.llm_provider)
    data["api_key"] = app_config.api_key or ""
    data["htr_model"] = normalize_model_selection("htr", app_config.htr_model)
    data["fix_model"] = normalize_model_selection("fix", app_config.fix_model)
    data["analysis_model"] = normalize_model_selection("analysis", app_config.analysis_model)
    data["box_model"] = normalize_model_selection("box", app_config.box_model)
    data["ollama_base_url"] = normalize_base_url(app_config.ollama_base_url)
    data["ollama_htr_model"] = app_config.ollama_htr_model or DEFAULT_OLLAMA_MODEL
    data["ollama_fix_model"] = app_config.ollama_fix_model or DEFAULT_OLLAMA_MODEL
    data["ollama_analysis_model"] = app_config.ollama_analysis_model or DEFAULT_OLLAMA_MODEL
    data["ollama_box_model"] = app_config.ollama_box_model or DEFAULT_OLLAMA_MODEL
    data["ollama_remove_table_headers"] = bool(app_config.ollama_remove_table_headers)
    data["ollama_pretty_html"] = bool(app_config.ollama_pretty_html)
    data["api_timeout_seconds"] = max(30, min(int(app_config.api_timeout_seconds), 3600))
    data["stream_transcription"] = bool(app_config.stream_transcription)
    data.pop("tts_lang", None)
    data.pop("tts_model", None)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle)
