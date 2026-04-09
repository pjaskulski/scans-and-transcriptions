import csv
import json
import os
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
