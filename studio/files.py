"""Bounded JSON, atomic publications, path confinement and image normalization utilities."""

# Index: declarations module.digest@L17, module.confined@L23, module.read_json@L31, read_json.pairs@L36, module.atomic_json@L53, module.normalized_image@L67; variables MAX_IMAGE_BYTES@L12, MAX_PIXELS@L13, path@L17, stream@L19, relative@L23, root@L23, path@L25, limit@L31, path@L31, items@L36, result@L38, value@L43, _@L46, value@L46, path@L53, value@L53, descriptor@L56, temporary@L56, stream@L58, path@L67, image@L73, normalized@L78. Purposes/parameters: docs/code-map.json.
import hashlib
import json
import os
import tempfile
import warnings
from pathlib import Path
from PIL import Image, ImageOps

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 4_194_304
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def digest(path: Path) -> str:
    """Stream a SHA-256 digest without retaining a whole model in memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def confined(root: Path, relative: str) -> Path:
    """Resolve a known relative artifact path and reject traversal/symlink escapes."""
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact escapes its data root")
    return path


def read_json(path: Path, limit: int = 1_000_000) -> dict:
    """Read a size-bounded JSON object; reject duplicate keys and non-finite numbers."""
    if path.stat().st_size > limit:
        raise ValueError("JSON document exceeds its limit")

    def pairs(items):
        """Reject duplicate keys instead of silently choosing the last value."""
        result = dict(items)
        if len(result) != len(items):
            raise ValueError("Duplicate JSON key")
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON")),
    )
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def atomic_json(path: Path, value: dict) -> None:
    """Publish complete JSON via same-directory replace; clean only this function's temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def normalized_image(path: Path) -> Image.Image:
    """Decode one bounded supported raster, apply EXIF rotation and strip metadata on output."""
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds 20 MiB")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG", "WEBP", "BMP"}:
                raise ValueError("Unsupported image type (PNG/JPEG/WebP/BMP only)")
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Image exceeds pixel limit")
            normalized = ImageOps.exif_transpose(image).convert("RGB")
            normalized.info.clear()
            return normalized
