import json
import logging
import mimetypes
import os
import socket
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from dataclasses import asdict
from pathlib import Path

from datalab_sdk import ConvertOptions, DatalabClient


DEFAULT_DATALAB_API_URL = "https://www.datalab.to/api/v1"
DEFAULT_DATALAB_OUTPUT_FORMAT = "markdown"
DEFAULT_DATALAB_MODE = "balanced"
DATALAB_OUTPUT_FORMATS = {"markdown", "html", "json"}
DATALAB_MODES = {"fast", "balanced", "accurate"}

logger = logging.getLogger(__name__)


@dataclass
class DatalabUsageMetadata:
    prompt_token_count: int = 0
    candidates_token_count: int = 0
    total_token_count: int = 0
    page_count: int = 0
    total_cost: float = 0.0


@dataclass
class DatalabResponse:
    text: str = ""
    usage_metadata: DatalabUsageMetadata | None = None
    raw_response: dict | None = None


def get_api_key() -> str:
    api_key = os.environ.get("DATALAB_API_KEY", "").strip()
    if api_key:
        return api_key

    try:
        from dotenv import load_dotenv

        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
    except Exception:
        pass

    return os.environ.get("DATALAB_API_KEY", "").strip()


def normalize_output_format(value: str | None) -> str:
    return value if value in DATALAB_OUTPUT_FORMATS else DEFAULT_DATALAB_OUTPUT_FORMAT


def normalize_mode(value: str | None) -> str:
    return value if value in DATALAB_MODES else DEFAULT_DATALAB_MODE


def _request_json(request: urllib.request.Request, timeout_seconds: int) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace").strip()
        details = f": {error_body}" if error_body else ""
        raise RuntimeError(f"Datalab odrzucił żądanie: HTTP {exc.code} {exc.reason}{details}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"Datalab nie zwrócił odpowiedzi w ciągu {timeout_seconds} s.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Nie można połączyć się z Datalab: {exc}") from exc


def _multipart_body(fields: dict[str, str], file_path: str) -> tuple[bytes, str]:
    boundary = f"----ScansAndTranscriptions{uuid.uuid4().hex}"
    path = Path(file_path)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode("ascii"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="file.0"; filename="{path.name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("ascii"))
    return bytes(body), boundary


def _submit_convert_request(
    image_path: str,
    *,
    api_key: str,
    output_format: str,
    mode: str,
    timeout_seconds: int,
) -> dict:
    body, boundary = _multipart_body(
        {
            "output_format": normalize_output_format(output_format),
            "mode": normalize_mode(mode),
        },
        image_path,
    )
    request = urllib.request.Request(
        f"{DEFAULT_DATALAB_API_URL}/convert",
        data=body,
        headers={
            "X-API-Key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    return _request_json(request, timeout_seconds)


def _poll_convert_result(
    request_id: str,
    *,
    api_key: str,
    timeout_seconds: int,
    poll_interval_seconds: float = 2.0,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_data = {}

    while time.monotonic() < deadline:
        url = f"{DEFAULT_DATALAB_API_URL}/convert/{urllib.parse.quote(request_id)}"
        request = urllib.request.Request(url, headers={"X-API-Key": api_key}, method="GET")
        last_data = _request_json(request, max(5, min(30, timeout_seconds)))
        status = (last_data.get("status") or "").lower()

        if status == "complete":
            if last_data.get("success") is False:
                raise RuntimeError(last_data.get("error") or "Datalab zakończył konwersję błędem.")
            return last_data
        if status == "failed":
            raise RuntimeError(last_data.get("error") or "Datalab zakończył konwersję błędem.")

        time.sleep(poll_interval_seconds)

    raise RuntimeError(
        f"Datalab nie zakończył konwersji w ciągu {timeout_seconds} s. "
        f"Ostatni status: {last_data.get('status') or 'nieznany'}."
    )


def _result_text(data: dict, output_format: str) -> str:
    output_format = normalize_output_format(output_format)
    if output_format == "html":
        return (data.get("html") or "").strip()
    if output_format == "json":
        payload = data.get("json")
        if payload is None:
            payload = data
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return (data.get("markdown") or "").strip()


def _usage_from_result(data: dict) -> DatalabUsageMetadata:
    return DatalabUsageMetadata(
        page_count=int(data.get("page_count") or 0),
        total_cost=float(data.get("total_cost") or 0.0),
    )


def _usage_from_sdk_result(result) -> DatalabUsageMetadata:
    return DatalabUsageMetadata(
        page_count=int(getattr(result, "page_count", None) or 0),
    )


def _sdk_result_text(result, output_format: str) -> str:
    output_format = normalize_output_format(output_format)
    if output_format == "html":
        return (getattr(result, "html", None) or "").strip()
    if output_format == "json":
        payload = getattr(result, "json", None)
        if payload is None:
            payload = asdict(result)
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return (getattr(result, "markdown", None) or "").strip()


def convert_image(
    image_path: str,
    *,
    api_key: str | None = None,
    output_format: str = DEFAULT_DATALAB_OUTPUT_FORMAT,
    mode: str = DEFAULT_DATALAB_MODE,
    timeout_seconds: int = 300,
):
    api_key = (api_key or get_api_key()).strip()
    if not api_key:
        raise RuntimeError("Brak klucza Datalab API. Ustaw zmienną środowiskową DATALAB_API_KEY.")

    output_format = normalize_output_format(output_format)
    mode = normalize_mode(mode)

    logger.info(
        "Datalab SDK convert started: image=%s output_format=%s mode=%s timeout=%ss",
        image_path,
        output_format,
        mode,
        timeout_seconds,
    )
    try:
        client = DatalabClient(api_key=api_key, timeout=timeout_seconds)
        result = client.convert(
            file_path=image_path,
            options=ConvertOptions(output_format=output_format, mode=mode),
            max_polls=max(1, int(timeout_seconds)),
            poll_interval=1,
        )
    except Exception as exc:
        logger.exception("Datalab SDK convert failed: image=%s", image_path)
        raise RuntimeError(f"Datalab nie wykonał konwersji: {exc}") from exc

    if getattr(result, "success", True) is False:
        raise RuntimeError(getattr(result, "error", None) or "Datalab zakończył konwersję błędem.")

    logger.info("Datalab SDK convert finished: image=%s", image_path)
    return "datalab-convert", DatalabResponse(
        text=_sdk_result_text(result, output_format),
        usage_metadata=_usage_from_sdk_result(result),
        raw_response=asdict(result),
    )
