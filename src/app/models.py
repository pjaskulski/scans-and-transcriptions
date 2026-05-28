from dataclasses import dataclass, field


@dataclass
class AppConfig:
    font_size: int = 12
    current_lang: str = "PL"
    default_prompt: str = "prompt_handwritten_pol_xx_century.txt"
    api_key: str = ""
    htr_model: str = "gemini-3.1-pro-preview"
    analysis_model: str = "gemini-3.5-flash"
    box_model: str = "gemini-3.1-flash-image"


@dataclass
class ScanFile:
    img: str
    txt: str
    name: str


@dataclass
class NerCache:
    checksum: str = ""
    entities: dict = field(default_factory=dict)
    coordinates: list = field(default_factory=list)
