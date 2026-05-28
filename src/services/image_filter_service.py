from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


FILTER_SUFFIXES = {
    "invert": ".inv",
    "contrast": ".con",
}


def is_generated_filter_image(path):
    path = Path(path)
    return any(path.stem.endswith(suffix) for suffix in FILTER_SUFFIXES.values())


def filtered_image_path(image_path, mode):
    suffix = FILTER_SUFFIXES.get(mode)
    if not suffix:
        return Path(image_path)

    path = Path(image_path)
    return path.with_name(f"{path.stem}{suffix}{path.suffix}")


def apply_image_filter(image, mode):
    if mode == "invert":
        return _invert_image(image)
    if mode == "contrast":
        return _contrast_image(image)
    return image.copy()


def ensure_filtered_image(image_path, mode):
    if mode not in FILTER_SUFFIXES:
        return str(image_path)

    output_path = filtered_image_path(image_path, mode)
    if output_path.exists():
        return str(output_path)

    with Image.open(image_path) as image:
        filtered = apply_image_filter(image, mode)
        save_kwargs = {}
        if image.format:
            save_kwargs["format"] = image.format
        filtered.save(output_path, **save_kwargs)

    return str(output_path)


def _invert_image(image):
    if image.mode == "RGBA":
        r, g, b, alpha = image.split()
        rgb = Image.merge("RGB", (r, g, b))
        inverted = ImageOps.invert(rgb)
        inverted.putalpha(alpha)
        return inverted

    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")

    return ImageOps.invert(image)


def _contrast_image(image):
    filtered = ImageEnhance.Contrast(image).enhance(2.0)
    return ImageEnhance.Sharpness(filtered).enhance(1.5)
