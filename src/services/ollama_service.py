import base64
import html
import json
import logging
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/api"
DEFAULT_OLLAMA_MODEL = "fredrezones55/chandra-ocr-2:latest"
DEFAULT_OLLAMA_KEEP_ALIVE = "30m"
DEFAULT_OLLAMA_IMAGE_MAX_EDGE = 3000
DEFAULT_OLLAMA_NUM_CTX = 32768
DEFAULT_OLLAMA_NUM_PREDICT = 8192

UNICODE_FRACTIONS = {
    ("0", "3"): "↉",
    ("1", "2"): "½",
    ("1", "3"): "⅓",
    ("2", "3"): "⅔",
    ("1", "4"): "¼",
    ("3", "4"): "¾",
    ("1", "5"): "⅕",
    ("2", "5"): "⅖",
    ("3", "5"): "⅗",
    ("4", "5"): "⅘",
    ("1", "6"): "⅙",
    ("5", "6"): "⅚",
    ("1", "7"): "⅐",
    ("1", "8"): "⅛",
    ("3", "8"): "⅜",
    ("5", "8"): "⅝",
    ("7", "8"): "⅞",
    ("1", "9"): "⅑",
    ("1", "10"): "⅒",
}

logger = logging.getLogger(__name__)


class InvalidOllamaTableResponse(RuntimeError):
    pass


@dataclass
class OllamaUsageMetadata:
    prompt_token_count: int = 0
    candidates_token_count: int = 0
    total_token_count: int = 0


@dataclass
class OllamaResponse:
    text: str = ""
    usage_metadata: OllamaUsageMetadata | None = None
    raw_response: str = ""
    raw_thinking: str = ""


def normalize_base_url(base_url: str | None) -> str:
    url = (base_url or DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    if not url:
        return DEFAULT_OLLAMA_BASE_URL
    if not url.endswith("/api"):
        url = f"{url}/api"
    return url


def _request_json(base_url: str, endpoint: str, payload: dict | None, timeout_seconds: int) -> dict:
    url = f"{normalize_base_url(base_url)}/{endpoint.lstrip('/')}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace").strip()
        details = f": {error_body}" if error_body else ""
        raise RuntimeError(f"Ollama odrzuciła żądanie pod adresem {url}: HTTP {exc.code} {exc.reason}{details}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(
            f"Ollama nie zwróciła odpowiedzi w ciągu {timeout_seconds} s pod adresem {url}. "
            "Jeśli to pierwsze użycie dużego modelu, poczekaj aż model się załaduje albo zwiększ timeout w ustawieniach."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Nie można połączyć się z Ollama pod adresem {url}: {exc}") from exc


def list_models(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout_seconds: int = 10) -> list[str]:
    data = _request_json(base_url, "tags", None, timeout_seconds)
    return [item.get("name") or item.get("model") for item in data.get("models", []) if item.get("name") or item.get("model")]


def _image_base64(image_path: str) -> str:
    path = Path(image_path)
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail(
            (DEFAULT_OLLAMA_IMAGE_MAX_EDGE, DEFAULT_OLLAMA_IMAGE_MAX_EDGE),
            Image.Resampling.LANCZOS,
        )
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=92, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("ascii")


def _usage_from_response(data: dict) -> OllamaUsageMetadata:
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    output_tokens = int(data.get("eval_count") or 0)
    return OllamaUsageMetadata(
        prompt_token_count=prompt_tokens,
        candidates_token_count=output_tokens,
        total_token_count=prompt_tokens + output_tokens,
    )


def _response_text(data: dict) -> str:
    return (data.get("response") or data.get("thinking") or "").strip()


def _select_transcription_text(prompt_text: str, response: "OllamaResponse") -> str:
    if _prompt_requests_html_table(prompt_text):
        if _looks_like_html_table(response.raw_response):
            return response.raw_response
        if _looks_like_html_table(response.raw_thinking):
            return response.raw_thinking
    return response.text


def _prompt_requests_html_table(prompt_text: str) -> bool:
    normalized = prompt_text.lower()
    wants_html = "html" in normalized or "<table" in normalized
    wants_table = any(word in normalized for word in ["table", "tabela", "tabelę", "tabeli", "tabel"])
    return wants_html and wants_table


def _looks_like_html_table(text: str) -> bool:
    return bool(
        re.search(r"<table\b", text, flags=re.IGNORECASE)
        and re.search(r"</table>", text, flags=re.IGNORECASE)
        and re.search(r"<tr\b", text, flags=re.IGNORECASE)
        and re.search(r"</tr>", text, flags=re.IGNORECASE)
    )


def _validate_transcription_response(
    prompt_text: str,
    response_text: str,
    raw_response: str = "",
    raw_thinking: str = "",
    log_full_response: bool = True,
) -> None:
    if _prompt_requests_html_table(prompt_text) and not _looks_like_html_table(response_text):
        preview = re.sub(r"\s+", " ", response_text).strip()[:500]
        if log_full_response:
            if raw_response or raw_thinking:
                print("Ollama/Chandra invalid HTML table response. Raw fields follow:", flush=True)
                print("=== response ===", flush=True)
                print(raw_response, flush=True)
                print("=== thinking ===", flush=True)
                print(raw_thinking, flush=True)
                print("=== selected text ===", flush=True)
                print(response_text, flush=True)
            else:
                print(
                    "Ollama/Chandra invalid HTML table response. Full response follows:\n"
                    + response_text,
                    flush=True,
                )
        raise InvalidOllamaTableResponse(
            "Ollama/Chandra nie zwróciła oczekiwanej tabeli HTML. "
            "Odpowiedź wygląda na opis zadania albo tekst bez znaczników <table>/<tr>, więc nie została zapisana. "
            f"Początek odpowiedzi: {preview}"
        )


def _html_to_text(text: str) -> str:
    if not re.search(r"</?(div|p|br|h[1-6]|sup)\b", text, flags=re.IGNORECASE):
        return text.strip()

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _strip_table_borders(html_text: str) -> str:
    if not re.search(r"<\s*(table|tr|td|th)\b", html_text, flags=re.IGNORECASE):
        return html_text

    def clean_tag(match):
        tag_name = match.group(1)
        attrs = match.group(2) or ""
        attrs = re.sub(r'\s(?:border|frame|rules)=("[^"]*"|\'[^\']*\'|[^\s>]+)', "", attrs, flags=re.IGNORECASE)

        def clean_style(style_match):
            quote = style_match.group(1)
            style = style_match.group(2)
            declarations = []
            for declaration in style.split(";"):
                declaration = declaration.strip()
                if not declaration:
                    continue
                property_name = declaration.split(":", 1)[0].strip().lower()
                if property_name == "border" or property_name.startswith("border-") or property_name == "outline":
                    continue
                declarations.append(declaration)

            if tag_name.lower() in {"table", "td", "th"}:
                declarations.append("border: none")
            if tag_name.lower() == "table":
                declarations.append("border-collapse: collapse")

            return f' style={quote}{"; ".join(declarations)}{quote}' if declarations else ""

        if re.search(r"\sstyle=", attrs, flags=re.IGNORECASE):
            attrs = re.sub(r'\sstyle=(["\'])(.*?)\1', clean_style, attrs, flags=re.IGNORECASE | re.DOTALL)
        elif tag_name.lower() in {"table", "td", "th"}:
            style = "border: none"
            if tag_name.lower() == "table":
                style += "; border-collapse: collapse"
            attrs += f' style="{style}"'

        return f"<{tag_name}{attrs}>"

    return re.sub(r"<\s*(table|tr|td|th)\b([^>]*)>", clean_tag, html_text, flags=re.IGNORECASE)


def _replace_latex_fractions(text: str) -> str:
    def replacement(match):
        numerator = match.group(1).strip()
        denominator = match.group(2).strip()
        return UNICODE_FRACTIONS.get((numerator, denominator), match.group(0))

    text = re.sub(r"\\frac\s*\{\s*(\d+)\s*\}\s*\{\s*(\d+)\s*\}", replacement, text)
    fraction_chars = "".join(re.escape(char) for char in UNICODE_FRACTIONS.values())
    text = re.sub(rf"\$\s*([{fraction_chars}])\s*\$", r"\1", text)
    text = re.sub(rf"\\\(\s*([{fraction_chars}])\s*\\\)", r"\1", text)
    text = re.sub(rf"\\\[\s*([{fraction_chars}])\s*\\\]", r"\1", text)
    mixed_fraction = rf"\d+\s*[{fraction_chars}]|[{fraction_chars}]"
    text = re.sub(rf"\$\s*({mixed_fraction})\s*\$", r"\1", text)
    text = re.sub(rf"\\\(\s*({mixed_fraction})\s*\\\)", r"\1", text)
    text = re.sub(rf"\\\[\s*({mixed_fraction})\s*\\\]", r"\1", text)
    text = re.sub(rf"<math\b[^>]*>\s*({mixed_fraction})\s*</math>", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(
        rf"<math\b[^>]*>\s*<m(?:n|text)\b[^>]*>\s*({mixed_fraction})\s*</m(?:n|text)>\s*</math>",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _plain_fraction_to_unicode(value: str) -> str:
    value = html.unescape(value).strip()
    match = re.fullmatch(r"(\d+)\s*/\s*(\d+)", value)
    if match:
        return UNICODE_FRACTIONS.get((match.group(1), match.group(2)), value)

    match = re.fullmatch(r"(\d+)\s+(\d+)\s*/\s*(\d+)", value)
    if match:
        fraction = UNICODE_FRACTIONS.get((match.group(2), match.group(3)))
        if fraction:
            return f"{match.group(1)}{fraction}"

    return value


def _replace_table_cell_plain_fractions(text: str) -> str:
    def replacement(match):
        tag_name = match.group(1)
        attrs = match.group(2) or ""
        content = match.group(3)
        sup_sub_match = re.fullmatch(
            r"\s*(?:(\d+)\s*)?<sup\b[^>]*>\s*(\d+)\s*</sup>\s*/\s*<sub\b[^>]*>\s*(\d+)\s*</sub>\s*",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if sup_sub_match:
            whole_number = sup_sub_match.group(1) or ""
            fraction = UNICODE_FRACTIONS.get((sup_sub_match.group(2), sup_sub_match.group(3)))
            if fraction:
                return f"<{tag_name}{attrs}>{whole_number}{fraction}</{tag_name}>"

        plain_content = re.sub(r"<[^>]+>", "", content).strip()
        converted = _plain_fraction_to_unicode(plain_content)
        if converted == html.unescape(plain_content):
            return match.group(0)
        return f"<{tag_name}{attrs}>{converted}</{tag_name}>"

    return re.sub(
        r"<\s*(td|th)\b([^>]*)>(.*?)</\s*\1\s*>",
        replacement,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _remove_table_headers(html_text: str) -> str:
    return re.sub(r"<thead\b[^>]*>.*?</thead>", "", html_text, flags=re.IGNORECASE | re.DOTALL)


def _format_html(text: str) -> str:
    if not re.search(r"<[a-zA-Z][^>]*>", text):
        return text

    block_tags = {
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "td",
        "th",
        "div",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
    }
    text = re.sub(r">\s*<", ">\n<", text.strip())
    lines = []
    indent = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        closing_match = re.match(r"</\s*([a-zA-Z0-9]+)\b", line)
        opening_match = re.match(r"<\s*([a-zA-Z0-9]+)\b", line)
        is_closing = bool(closing_match)
        tag_name = (closing_match or opening_match).group(1).lower() if (closing_match or opening_match) else ""

        if is_closing and tag_name in block_tags:
            indent = max(indent - 1, 0)

        lines.append("  " * indent + line)

        is_self_closing = line.endswith("/>") or re.match(r"<\s*(br|hr|img|meta|link|input)\b", line, re.IGNORECASE)
        has_same_line_close = bool(tag_name and re.search(rf"</\s*{re.escape(tag_name)}\s*>", line, re.IGNORECASE))
        if (
            opening_match
            and not is_closing
            and tag_name in block_tags
            and not is_self_closing
            and not has_same_line_close
        ):
            indent += 1

    return "\n".join(lines)


def _postprocess_transcription_html(
    text: str,
    remove_table_headers: bool = False,
    pretty_html: bool = True,
) -> str:
    text = _strip_table_borders(text)
    if remove_table_headers:
        text = _remove_table_headers(text)
    text = _replace_latex_fractions(text)
    text = _replace_table_cell_plain_fractions(text)
    if pretty_html:
        text = _format_html(text)
    return text


def _html_table_retry_prompt(prompt_text: str) -> str:
    return (
        "CRITICAL OUTPUT FORMAT REQUIREMENT:\n"
        "Return ONLY a complete HTML table.\n"
        "The answer MUST start with <table and MUST contain <tr> rows and table cells.\n"
        "Do NOT write analysis, markdown, JSON, layout labels, bounding boxes, comments, or explanations.\n"
        "Do NOT describe what you see. Transcribe the visible table cells into HTML.\n"
        "If a cell is unreadable, put [nieczytelne] inside that cell.\n\n"
        "Original user instructions:\n"
        f"{prompt_text}"
    )


def _prepare_transcription_response(
    prompt_text: str,
    response: OllamaResponse,
    remove_table_headers: bool,
    pretty_html: bool,
    log_full_response: bool,
) -> OllamaResponse:
    response.text = _select_transcription_text(prompt_text, response)
    _validate_transcription_response(
        prompt_text,
        response.text,
        raw_response=response.raw_response,
        raw_thinking=response.raw_thinking,
        log_full_response=log_full_response,
    )
    response.text = _postprocess_transcription_html(
        response.text,
        remove_table_headers=remove_table_headers,
        pretty_html=pretty_html,
    )
    return response


def generate(
    prompt_text: str,
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    image_path: str | None = None,
    timeout_seconds: int = 300,
    format_json: bool = False,
) -> tuple[str, OllamaResponse]:
    payload = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": False,
        "think": False,
        "keep_alive": DEFAULT_OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0,
            "num_ctx": DEFAULT_OLLAMA_NUM_CTX,
            "num_predict": DEFAULT_OLLAMA_NUM_PREDICT,
        },
    }
    if image_path:
        payload["system"] = (
            "You transcribe document images. Return only the requested transcription/output. "
            "Do not describe the task, do not explain your plan, do not add comments, "
            "and do not answer in prose unless the user explicitly asks for prose."
        )
        payload["images"] = [_image_base64(image_path)]
    if format_json:
        payload["format"] = "json"

    logger.info("Ollama request started: model=%s image=%s timeout=%ss", model_name, image_path, timeout_seconds)
    data = _request_json(base_url, "generate", payload, timeout_seconds)
    logger.info("Ollama request finished: model=%s image=%s", model_name, image_path)
    return model_name, OllamaResponse(
        text=_response_text(data),
        usage_metadata=_usage_from_response(data),
        raw_response=(data.get("response") or "").strip(),
        raw_thinking=(data.get("thinking") or "").strip(),
    )


def generate_stream(
    prompt_text: str,
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    image_path: str | None = None,
    timeout_seconds: int = 300,
):
    payload = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": True,
        "think": False,
        "keep_alive": DEFAULT_OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0,
            "num_ctx": DEFAULT_OLLAMA_NUM_CTX,
            "num_predict": DEFAULT_OLLAMA_NUM_PREDICT,
        },
    }
    if image_path:
        payload["system"] = (
            "You transcribe document images. "
            "Return only the requested transcription/output. "
            "Do not describe the task, do not explain your plan, do not add comments, "
            "and do not answer in prose unless the user explicitly asks for prose."
        )
        payload["images"] = [_image_base64(image_path)]

    url = f"{normalize_base_url(base_url)}/generate"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    def response_stream():
        logger.info("Ollama stream started: model=%s image=%s timeout=%ss", model_name, image_path, timeout_seconds)
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                for raw_line in response:
                    if not raw_line:
                        continue
                    data = json.loads(raw_line.decode("utf-8"))
                    text = data.get("response") or data.get("thinking") or ""
                    usage_metadata = _usage_from_response(data) if data.get("done") else None
                    yield OllamaResponse(text=text, usage_metadata=usage_metadata)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace").strip()
            details = f": {error_body}" if error_body else ""
            raise RuntimeError(f"Ollama odrzuciła żądanie pod adresem {url}: HTTP {exc.code} {exc.reason}{details}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(
                f"Ollama nie zwróciła odpowiedzi w ciągu {timeout_seconds} s pod adresem {url}. "
                "Jeśli to pierwsze użycie dużego modelu, poczekaj aż model się załaduje albo zwiększ timeout w ustawieniach."
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Nie można połączyć się z Ollama pod adresem {url}: {exc}") from exc
        logger.info("Ollama stream finished: model=%s image=%s", model_name, image_path)

    return model_name, response_stream()


def transcribe_image(
    prompt_text: str,
    image_path: str,
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = 300,
    remove_table_headers: bool = False,
    pretty_html: bool = True,
):
    model, response = generate(
        prompt_text,
        model_name=model_name,
        base_url=base_url,
        image_path=image_path,
        timeout_seconds=timeout_seconds,
    )
    try:
        response = _prepare_transcription_response(
            prompt_text,
            response,
            remove_table_headers=remove_table_headers,
            pretty_html=pretty_html,
            log_full_response=False,
        )
    except InvalidOllamaTableResponse:
        if not _prompt_requests_html_table(prompt_text):
            raise
        logger.info("Ollama table OCR retry started: model=%s image=%s", model_name, image_path)
        retry_prompt = _html_table_retry_prompt(prompt_text)
        model, response = generate(
            retry_prompt,
            model_name=model_name,
            base_url=base_url,
            image_path=image_path,
            timeout_seconds=timeout_seconds,
        )
        response = _prepare_transcription_response(
            retry_prompt,
            response,
            remove_table_headers=remove_table_headers,
            pretty_html=pretty_html,
            log_full_response=True,
        )
    return model, response


def stream_transcribe_image(
    prompt_text: str,
    image_path: str,
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = 300,
):
    return generate_stream(
        prompt_text,
        model_name=model_name,
        base_url=base_url,
        image_path=image_path,
        timeout_seconds=timeout_seconds,
    )


def verify_transcription(
    image_path: str,
    original_text: str,
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = 300,
):
    prompt = """
Otrzymasz skan dokumentu oraz jego wstępną transkrypcję.

Twoim zadaniem jest zweryfikować tekst z obrazem i poprawić wszelkie błędy:
1. Popraw literówki i błędnie odczytane słowa.
2. Uzupełnij pominięte słowa.
3. Zachowaj oryginalny układ wierszy.
4. Nie dodawaj własnych komentarzy, zwróć TYLKO poprawiony tekst.

Pamiętaj o zasadach oznaczania niepewności:
- Jeśli fragment (słowo lub litera) jest całkowicie nieczytelny (plama, zniszczenie), oznacz go jako: [nieczytelne].
- Jeśli odczyt jest wątpliwy, ale masz przypuszczenie, zapisz je i dodaj znak zapytania w nawiasie, np.: [słowo?] lub słow[o?].
- Jeśli w tekście występuje skreślenie, oznacz je jako: [skreślenie].

Transkrypcja:
"""
    return generate(
        prompt + original_text,
        model_name=model_name,
        base_url=base_url,
        image_path=image_path,
        timeout_seconds=timeout_seconds,
    )


def extract_entities(
    text: str,
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = 300,
):
    prompt = """
Jesteś ekspertem w dziedzinie historii i paleografii XVIII, XIX oraz XX wieku. Twoim zadaniem
jest ekstrakcja nazw własnych z transkrypcji dokumentów historycznych.

Zasady klasyfikacji:
1. PERS (Osoby): Wyodrębnij nazwy osób, mogą to być pełne imiona i nazwiska, ale także zapisy
   samych nazwisk lub imion, zapisy inicjałów np. A. T., zapisy nazw stosowane w średniowieczu
   np. Jan z Dąbrówki, uwzględnij także nazwy narodów lub plemion. DOŁĄCZ do nazwy towarzyszące im
   tytuły szlacheckie (np. hr., margrabia), stopnie wojskowe (np. kpt., gen.),
   funkcje urzędowe (np. rządzca, wójt) oraz zwroty grzecznościowe (np. JW Pan, Ob.),
   jeśli występują bezpośrednio przy nazwisku.
2. LOC (Geografia): Wyodrębnij nazwy miast, wsi, krajów, państw, folwarków, majątków ziemskich, rzek,
   jezior, guberni oraz konkretne nazwy ulic i placów.
3. ORG (Organizacje): Wyodrębnij nazwy urzędów, instytucji, pułków wojskowych, parafii, komitetów, stowarzyszeń,
   fabryk i towarzystw (np. "Towarzystwo Kredytowe Ziemskie").

Instrukcje techniczne:
- Rekonstrukcja: Jeśli nazwa jest podzielona między wiersze (np. "Krak-" i "ów"),
  połącz ją w jedno słowo bez dywizu ("Kraków").
- Normalizacja: Zwróć nazwy w takiej formie (deklinacji), w jakiej występują w tekście, ale usuń
  znaki podziału wiersza.
- Czystość: Ignoruj nazwy pospolite, chyba że są częścią nazwy własnej.

Zwróć wynik WYŁĄCZNIE jako JSON w formacie:
{
  "PERS": ["nazwa1", ...],
  "LOC": ["nazwa1", ...],
  "ORG": ["nazwa1", ...]
}
"""
    return generate(
        prompt + "\nTekst: " + text,
        model_name=model_name,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        format_json=True,
    )


def locate_entities(
    image_path: str,
    entities_to_find: list[tuple[str, str]],
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = 300,
):
    entities_str = "".join(f"{name},{category}\n" for name, category in entities_to_find)
    prompt = f"""
Na załączonym obrazie znajdź lokalizację następujących nazw,
(podanych w formie listy par: nazwa_do_wyszukania, kategoria_nazwy, każda para w osobnym wierszu np.
Felicjan Słomkowski, PERS
Gniezno, LOC):

{entities_str}.

Uwzględnij tylko i wyłącznie nazwy z listy, inne zignoruj.
Dla każdej nazwy podaj współrzędne ramki w formacie:

nazwa, nazwa_kategorii [ymin, xmin, ymax, xmax]

Wszystkie współrzędne w skali 0-1000.
Zwróć tylko listę tych danych bez żadnych dodatkowych komentarzy.
"""
    return generate(
        prompt,
        model_name=model_name,
        base_url=base_url,
        image_path=image_path,
        timeout_seconds=timeout_seconds,
    )


def build_nominative_map(
    names_list: list[str],
    model_name: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout_seconds: int = 300,
):
    nominative_map = {}
    usage_entries = []

    for i in range(0, len(names_list), 50):
        batch = names_list[i:i + 50]
        prompt = (
            "Dla podanej listy nazw własnych z dokumentów historycznych, "
            "podaj ich formę w mianowniku, nie zmieniaj rodzaju nazw (męski, żeński, nijaki). "
            "Zwróć WYŁĄCZNIE czysty JSON: {\"oryginał\": \"mianownik\", ...}. "
            f"Lista: {', '.join(batch)}"
        )
        model, response = generate(
            prompt,
            model_name=model_name,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            format_json=True,
        )
        if response.usage_metadata:
            usage_entries.append((model, response.usage_metadata))
        if response.text:
            json_str = response.text.replace("```json", "").replace("```", "").strip()
            nominative_map.update(json.loads(json_str))

    return nominative_map, usage_entries
