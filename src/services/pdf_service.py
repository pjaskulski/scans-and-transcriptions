from pathlib import Path
import re

try:
    import pymupdf
except ImportError:  # pragma: no cover - optional dependency at runtime
    pymupdf = None


def can_extract_pdf_pages() -> bool:
    return pymupdf is not None


def _number_width_for_import(folder_path: Path, image_prefix: str, total_pages: int) -> int:
    max_number = total_pages
    pattern = re.compile(rf"^{re.escape(image_prefix)}-(\d+)\.png$", re.IGNORECASE)

    for path in folder_path.iterdir():
        match = pattern.match(path.name)
        if match:
            max_number = max(max_number, int(match.group(1)) + total_pages)

    return max(2, len(str(max_number)))


def extract_pdf_pages(
    folder: str,
    pdf_files: list[str],
    image_prefix: str = "img",
    dpi: int = 300,
    progress_callback=None,
) -> list[str]:
    if not can_extract_pdf_pages():
        raise RuntimeError("Brak biblioteki PyMuPDF w środowisku aplikacji.")

    folder_path = Path(folder)
    created_images = []
    next_index = 1

    total_pages = 0
    for pdf_file in sorted(pdf_files):
        pdf_path = folder_path / pdf_file
        with pymupdf.open(pdf_path) as document:
            total_pages += len(document)

    number_width = _number_width_for_import(folder_path, image_prefix, total_pages)
    processed_pages = 0

    for pdf_file in sorted(pdf_files):
        pdf_path = folder_path / pdf_file

        with pymupdf.open(pdf_path) as document:
            for page_number, page in enumerate(document, start=1):
                while True:
                    target_name = f"{image_prefix}-{next_index:0{number_width}d}.png"
                    target_path = folder_path / target_name
                    next_index += 1
                    if not target_path.exists():
                        break

                pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                pixmap.save(target_path)
                created_images.append(str(target_path))
                processed_pages += 1

                if progress_callback:
                    progress_callback(
                        processed_pages,
                        total_pages,
                        pdf_file,
                        page_number,
                        len(document),
                    )

    return created_images
