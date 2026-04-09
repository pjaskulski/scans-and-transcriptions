import hashlib
import json
from pathlib import Path

from app.paths import json_for_text


def calculate_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_ner_json_path(text_path: str | None) -> str | None:
    if not text_path:
        return None
    return str(json_for_text(text_path))


def load_cache(json_path: str | None) -> dict:
    if not json_path:
        return {}

    path = Path(json_path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_cache(
    text_path: str | None,
    *,
    entities=None,
    coordinates=None,
    checksum=None,
    tts_checksum=None,
) -> str | None:
    json_path = get_ner_json_path(text_path)
    if not json_path:
        return None

    cache_data = load_cache(json_path)

    if checksum:
        cache_data["checksum"] = checksum
    if entities:
        cache_data["entities"] = entities
    if coordinates is not None:
        if coordinates == []:
            cache_data.pop("coordinates", None)
        else:
            cache_data["coordinates"] = coordinates
    if tts_checksum:
        cache_data["tts_checksum"] = tts_checksum

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(cache_data, handle, ensure_ascii=False, indent=4)

    return json_path
