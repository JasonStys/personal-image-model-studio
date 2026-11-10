"""Bounded JSON, atomic publications, path confinement and image normalization utilities."""

# Index: declarations module.digest@L19, module.confined@L25, module.read_json@L33, read_json.pairs@L42, module.replace_file@L59, module.atomic_json@L73, module.normalized_image@L87; variables MAX_IMAGE_BYTES@L14, MAX_PIXELS@L15, path@L19, stream@L21, relative@L25, root@L25, path@L27, limit@L33, path@L33, stream@L37, source@L38, items@L42, result@L44, value@L49, _@L52, value@L52, destination@L59, source@L59, attempt@L61, path@L73, value@L73, descriptor@L76, temporary@L76, stream@L78, path@L87, image@L93, normalized@L98. Purposes/parameters: docs/code-map.json.
import hashlib
import json
import os
import stat
import tempfile
import time
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
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("JSON document must be a regular file")
    with path.open("rb") as stream:
        source = stream.read(limit + 1)
    if len(source) > limit:
        raise ValueError("JSON document exceeds its limit")

    def pairs(items):
        """Reject duplicate keys instead of silently choosing the last value."""
        result = dict(items)
        if len(result) != len(items):
            raise ValueError("Duplicate JSON key")
        return result

    value = json.loads(
        source.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON")),
    )
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def replace_file(source: str | Path, destination: Path) -> None:
    """Atomically replace with at most eight attempts for Windows file-sharing errors; never relax ACLs."""
    for attempt in range(8):
        try:
            os.replace(source, destination)
            return
        except PermissionError as error:
            # Concurrent readers/antivirus can briefly deny deletion on Windows.
            # Other errors fail immediately; permanent denials still fail within two seconds.
            if getattr(error, "winerror", None) not in {5, 32, 33} or attempt == 7:
                raise
            time.sleep(min(0.05 * 2**attempt, 0.4))


def atomic_json(path: Path, value: dict) -> None:
    """Publish complete JSON via same-directory replace; clean only this function's temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        replace_file(temporary, path)
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
