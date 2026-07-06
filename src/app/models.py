from dataclasses import dataclass, field


@dataclass
class AppConfig:
    font_size: int = 12
    current_lang: str = "PL"
    default_prompt: str = "prompt_handwritten_pol_xx_century.txt"
    last_folder: str = ""
    llm_provider: str = "gemini"
    api_key: str = ""
    htr_model: str = "gemini-3.1-pro-preview"
    fix_model: str = "gemini-3.1-pro-preview"
    analysis_model: str = "gemini-3.5-flash"
    box_model: str = "gemini-3.1-flash-image"
    ollama_base_url: str = "http://localhost:11434/api"
    ollama_htr_model: str = "fredrezones55/chandra-ocr-2:latest"
    ollama_fix_model: str = "fredrezones55/chandra-ocr-2:latest"
    ollama_analysis_model: str = "fredrezones55/chandra-ocr-2:latest"
    ollama_box_model: str = "fredrezones55/chandra-ocr-2:latest"
    ollama_remove_table_headers: bool = False
    ollama_pretty_html: bool = True
    mistral_ocr_model: str = "mistral-ocr-4-0"
    mistral_include_blocks: bool = False
    mistral_table_format: str = "markdown"
    api_timeout_seconds: int = 300
    stream_transcription: bool = True


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
