import difflib
import re
import xml.sax.saxutils as saxutils


def tk_index_from_offset(text: str, offset: int) -> str:
    lines = text[:offset].split("\n")
    line = len(lines)
    column = len(lines[-1])
    return f"{line}.{column}"


def build_diff_ranges(old_text: str, new_text: str) -> list[tuple[str, str]]:
    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    ranges = []

    for tag, i1, i2, _, _ in matcher.get_opcodes():
        if tag != "equal":
            ranges.append(
                (tk_index_from_offset(old_text, i1), tk_index_from_offset(old_text, i2))
            )

    return ranges


def prepare_text_for_tei(text: str) -> str:
    lines = text.splitlines()
    joined_text = ""
    for line in lines:
        line = line.strip()
        if not line:
            joined_text += "\n\n"
        elif joined_text.endswith("-"):
            joined_text = joined_text[:-1] + line
        else:
            joined_text += (" " if joined_text and not joined_text.endswith("\n\n") else "") + line
    return joined_text


def tag_entities_tei(text: str, entities: dict) -> str:
    tag_map = {
        "PERS": "persName",
        "LOC": "placeName",
        "ORG": "orgName",
    }

    escaped_text = saxutils.escape(text)

    all_names = []
    for cat, names in entities.items():
        if cat in tag_map:
            for name in names:
                all_names.append((name, tag_map[cat]))

    all_names.sort(key=lambda item: len(item[0]), reverse=True)

    for name, tag in all_names:
        escaped_name = saxutils.escape(name)
        pattern = re.compile(rf"\b{re.escape(escaped_name)}\b", re.IGNORECASE)
        escaped_text = pattern.sub(f"<{tag}>{escaped_name}</{tag}>", escaped_text)

    return escaped_text
