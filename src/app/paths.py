import os
import sys
from pathlib import Path


def src_root() -> Path:
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return src_root().parent


def config_dir() -> Path:
    return project_root() / "config"


def prompts_dir() -> Path:
    return project_root() / "prompt"


def bin_dir() -> Path:
    return project_root() / "bin"


def tests_dir() -> Path:
    return project_root() / "test"


def config_file(filename: str = "config.json") -> Path:
    return config_dir() / filename


def localization_file(filename: str = "localization.json") -> Path:
    return config_dir() / filename


def prompt_file(filename: str) -> Path:
    return prompts_dir() / filename


def sibling_with_suffix(path: str | Path, suffix: str) -> Path:
    return Path(path).with_suffix(suffix)


def json_for_text(text_path: str | Path) -> Path:
    return sibling_with_suffix(text_path, ".json")


def fix_for_text(text_path: str | Path) -> Path:
    return sibling_with_suffix(text_path, ".fix")


def mp3_for_image(image_path: str | Path) -> Path:
    return sibling_with_suffix(image_path, ".mp3")


def wav_for_image(image_path: str | Path) -> Path:
    return sibling_with_suffix(image_path, ".wav")


def tokens_log_for_folder(folder: str | Path) -> Path:
    return Path(folder) / "tokens.log"


def ffmpeg_binary() -> Path:
    name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    return bin_dir() / name


def ffprobe_binary() -> Path:
    name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    return bin_dir() / name
