from dataclasses import dataclass, field


@dataclass
class AppConfig:
    font_size: int = 12
    current_lang: str = "PL"
    default_prompt: str = "prompt_handwritten_pol_xx_century.txt"
    api_key: str = ""
    tts_lang: str = "pl"


@dataclass
class ScanFile:
    img: str
    txt: str
    name: str


@dataclass
class NerCache:
    checksum: str = ""
    tts_checksum: str = ""
    entities: dict = field(default_factory=dict)
    coordinates: list = field(default_factory=list)
