import csv
import json
import os
import re
from pathlib import Path

from docx import Document

from app.paths import json_for_text
from services.text_service import prepare_text_for_tei, tag_entities_tei


def export_txt(scan_files: list[dict], target_path: str) -> None:
    merged_content = []

    for pair in scan_files:
        txt_path = pair["txt"]
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as handle:
                text_content = handle.read().strip()
                if text_content:
                    merged_content.append(text_content)

    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write("\n\n".join(merged_content))


def _find_html_tables(text: str) -> list[tuple[str, str]]:
    return re.findall(r"<table\b([^>]*)>(.*?)</table>", text, flags=re.IGNORECASE | re.DOTALL)


def _find_table_header(table_body: str) -> str:
    match = re.search(r"<thead\b[^>]*>.*?</thead>", table_body, flags=re.IGNORECASE | re.DOTALL)
    return match.group(0).strip() if match else ""


def _find_table_rows(table_body: str) -> list[str]:
    body_without_headers = re.sub(r"<thead\b[^>]*>.*?</thead>", "", table_body, flags=re.IGNORECASE | re.DOTALL)
    tbody_matches = re.findall(r"<tbody\b[^>]*>(.*?)</tbody>", body_without_headers, flags=re.IGNORECASE | re.DOTALL)
    row_sources = tbody_matches if tbody_matches else [body_without_headers]
    rows = []
    for source in row_sources:
        rows.extend(
            row.strip()
            for row in re.findall(r"<tr\b[^>]*>.*?</tr>", source, flags=re.IGNORECASE | re.DOTALL)
            if row.strip()
        )
    return rows


def export_merged_html_table(scan_files: list[dict], target_path: str) -> int:
    table_attrs = ""
    table_header = ""
    table_rows = []

    for pair in scan_files:
        txt_path = pair["txt"]
        if not os.path.exists(txt_path):
            continue

        with open(txt_path, "r", encoding="utf-8") as handle:
            tables = _find_html_tables(handle.read())

        for attrs, table_body in tables:
            if not table_attrs:
                table_attrs = attrs.strip()
            if not table_header:
                table_header = _find_table_header(table_body)
            table_rows.extend(_find_table_rows(table_body))

    if not table_rows:
        raise ValueError("Nie znaleziono wierszy tabel HTML w transkrypcjach.")

    table_open = f"<table {table_attrs}>".replace("  ", " ").strip() if table_attrs else "<table>"
    lines = [
        "<!doctype html>",
        '<html lang="pl">',
        "<head>",
        '  <meta charset="utf-8">',
        "</head>",
        "<body>",
        table_open,
    ]
    if table_header:
        lines.append(table_header)
    lines.append("<tbody>")
    lines.extend(table_rows)
    lines.append("</tbody>")
    lines.append("</table>")
    lines.append("</body>")
    lines.append("</html>")

    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return len(table_rows)


def export_docx(scan_files: list[dict], target_path: str) -> None:
    doc = Document()

    for pair in scan_files:
        if os.path.exists(pair["txt"]):
            all_lines = []
            with open(pair["txt"], "r", encoding="utf-8") as handle:
                lines = handle.readlines()
                all_lines.extend([line.strip() for line in lines])

            full_text = ""
            for line in all_lines:
                if not line:
                    full_text += "\n\n"

                if full_text == "":
                    full_text = line
                else:
                    if full_text.endswith("-"):
                        full_text = full_text[:-1] + line
                    else:
                        full_text += " " + line

            doc.add_paragraph(full_text)

    doc.save(target_path)


def export_tei(scan_files: list[dict], target_path: str) -> None:
    tei_content = []
    tei_content.append('<?xml version="1.0" encoding="UTF-8"?>')
    tei_content.append('<TEI xmlns="http://www.tei-c.org/ns/1.0">')
    tei_content.append("  <teiHeader>")
    tei_content.append("    <fileDesc>")
    tei_content.append("      <titleStmt><title>Eksport z ScansAndTranscriptions</title></titleStmt>")
    tei_content.append("      <publicationStmt><p>Wygenerowano automatycznie</p></publicationStmt>")
    tei_content.append("      <sourceDesc><p>Transkrypcje skanów</p></sourceDesc>")
    tei_content.append("    </fileDesc>")
    tei_content.append("  </teiHeader>")
    tei_content.append("  <text>")
    tei_content.append("    <body>")

    for pair in scan_files:
        if not os.path.exists(pair["txt"]):
            continue

        with open(pair["txt"], "r", encoding="utf-8") as handle:
            raw_text = handle.read()

        entities = {}
        json_path = json_for_text(pair["txt"])
        if json_path.exists():
            with json_path.open("r", encoding="utf-8") as handle:
                entities = json.load(handle).get("entities", {})

        processed_text = prepare_text_for_tei(raw_text)
        tagged_text = tag_entities_tei(processed_text, entities)

        tei_content.append(f'      <div type="page" n="{pair["name"]}">')
        for paragraph in tagged_text.split("\n\n"):
            if paragraph.strip():
                tei_content.append(f"        <p>{paragraph.strip()}</p>")
        tei_content.append("      </div>")

    tei_content.append("    </body>")
    tei_content.append("  </text>")
    tei_content.append("</TEI>")

    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(tei_content))


def collect_ner_rows(scan_files: list[dict]) -> list[dict]:
    rows = []

    for pair in scan_files:
        json_path = json_for_text(pair["txt"])
        txt_path = Path(pair["txt"])

        if json_path.exists() and txt_path.exists():
            with json_path.open("r", encoding="utf-8") as handle:
                entities = json.load(handle).get("entities", {})

            for category, names in entities.items():
                for name in names:
                    rows.append(
                        {
                            "orig": name,
                            "cat": category,
                            "file": os.path.basename(pair["img"]),
                        }
                    )

    return rows


def unique_ner_names(rows: list[dict]) -> list[str]:
    return sorted({row["orig"] for row in rows})


def write_ner_csv(
    target_path: str,
    rows: list[dict],
    nominative_map: dict,
    headers: list[str],
) -> None:
    with open(target_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow(headers)

        for row in rows:
            base_name = nominative_map.get(row["orig"], row["orig"])
            writer.writerow([row["orig"], base_name, row["cat"], row["file"]])
