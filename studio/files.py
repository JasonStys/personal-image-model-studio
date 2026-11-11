"""Bounded JSON, atomic publications, path confinement and image normalization utilities."""

# Index: declarations module.no_alias@L21, module.BoundedReader@L34, BoundedReader.__init__@L37, BoundedReader.tell@L41, BoundedReader.seek@L45, BoundedReader.read@L62, BoundedReader.seekable@L73, module.regular_stream@L79, module.regular_bytes@L107, module.digest@L116, module.confined@L128, module.read_json@L151, read_json.pairs@L155, module.replace_file@L172, module.atomic_json@L186, module.normalized_image@L201, module.normalized_pixels@L206; variables MAX_IMAGE_BYTES@L16, MAX_PIXELS@L17, path@L21, part@L23, status@L25, limit@L37, self@L37, stream@L37, self@L41, offset@L45, self@L45, whence@L45, target@L48, target@L50, size@L52, target@L55, self@L62, size@L62, remaining@L64, requested@L67, content@L68, self@L73, limit@L79, path@L79, flags@L86, descriptor@L92, status@L94, stream@L99, descriptor@L100, limit@L107, path@L107, stream@L109, source@L110, limit@L116, path@L116, stream@L118, result@L119, total@L119, block@L120, total@L121, relative@L128, root@L128, base@L139, candidate@L140, result@L142, result@L144, limit@L151, path@L151, source@L153, items@L155, result@L157, value@L162, _@L165, value@L165, destination@L172, source@L172, attempt@L174, path@L186, value@L186, descriptor@L190, temporary@L190, stream@L192, path@L201, content@L206, image@L212, normalized@L217. Purposes/parameters: docs/code-map.json.
import hashlib
import io
import json
import os
import stat
import tempfile
import time
import warnings
from pathlib import Path
from contextlib import contextmanager
from PIL import Image, ImageOps

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 4_194_304
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def no_alias(path: Path) -> None:
    """Reject pre-existing linked/reparse components and multi-link files without claiming race isolation."""
    for part in (*reversed(path.absolute().parents), path.absolute()):
        try:
            status = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(status.st_mode) or getattr(status, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked local artifact is not permitted")
        if stat.S_ISREG(status.st_mode) and status.st_nlink != 1:
            raise ValueError("Hardlinked local artifact is not permitted")


class BoundedReader:
    """A seekable descriptor view whose actual read positions cannot cross the caller's fixed byte cap."""

    def __init__(self, stream, limit: int):
        """Retain an already owned regular descriptor; the surrounding context alone closes it."""
        self.stream, self.limit = stream, limit

    def tell(self) -> int:
        """Expose the current descriptor position without reopening a pathname."""
        return self.stream.tell()

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        """Refuse positions outside the byte view, including a grown physical end-of-file."""
        if whence == os.SEEK_SET:
            target = offset
        elif whence == os.SEEK_CUR:
            target = self.tell() + offset
        elif whence == os.SEEK_END:
            size = os.fstat(self.stream.fileno()).st_size
            if size > self.limit:
                raise ValueError("Artifact grew beyond its byte limit")
            target = size + offset
        else:
            raise ValueError("Unknown artifact seek mode")
        if not 0 <= target <= self.limit:
            raise ValueError("Artifact seek exceeds its byte limit")
        return self.stream.seek(target)

    def read(self, size: int = -1) -> bytes:
        """Cap the allocation and bytes actually returned even when a parser asks for an unbounded read."""
        remaining = self.limit - self.tell()
        if remaining < 0:
            raise ValueError("Artifact read exceeds its byte limit")
        requested = remaining + 1 if size < 0 else min(size, remaining + 1)
        content = self.stream.read(requested)
        if len(content) > remaining:
            raise ValueError("Artifact grew beyond its byte limit")
        return content

    def seekable(self) -> bool:
        """Allow the standard ZIP parser's fixed local-file seeking interface."""
        return True


@contextmanager
def regular_stream(path: Path, limit: int):
    """Open one nonblocking/no-follow descriptor and enforce regular single-link size before any read."""
    if type(limit) is not int or not 1 <= limit <= 20 * 1024**3:
        raise ValueError("Invalid file byte limit")
    no_alias(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Artifact must be a regular file")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(path, flags)
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
            raise ValueError("Artifact must be a regular file with one link")
        if status.st_size > limit:
            raise ValueError("Artifact exceeds its byte limit")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            yield BoundedReader(stream, limit)
    finally:
        if descriptor != -1:
            os.close(descriptor)


def regular_bytes(path: Path, limit: int) -> bytes:
    """Bound actual bytes from the admitted descriptor even if an owned file grows after stat."""
    with regular_stream(path, limit) as stream:
        source = stream.read(limit + 1)
    if len(source) > limit:
        raise ValueError("Artifact exceeds its byte limit")
    return source


def digest(path: Path, limit: int = 20 * 1024**3) -> str:
    """Hash an admitted descriptor in bounded chunks, retaining no complete large model in memory."""
    with regular_stream(path, limit) as stream:
        result, total = hashlib.sha256(), 0
        while block := stream.read(min(1024 * 1024, limit - total + 1)):
            total += len(block)
            if total > limit:
                raise ValueError("Artifact grew beyond its byte limit")
            result.update(block)
        return result.hexdigest()


def confined(root: Path, relative: str) -> Path:
    """Normalize a relative artifact and enforce full-component trusted-root containment before use."""
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or ":" in relative
        or "\x00" in relative
        or os.path.isabs(relative)
    ):
        raise ValueError("Invalid relative artifact path")
    base = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(base, relative))
    if candidate == base:
        result = Path(base)
    elif candidate.startswith(base + os.sep):
        result = Path(candidate)
    else:
        raise ValueError("Artifact escapes its data root")
    no_alias(result)
    return result


def read_json(path: Path, limit: int = 1_000_000) -> dict:
    """Read a size-bounded JSON object; reject duplicate keys and non-finite numbers."""
    source = regular_bytes(path, limit)

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
    no_alias(path)
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
    return normalized_pixels(regular_bytes(path, MAX_IMAGE_BYTES))


def normalized_pixels(content: bytes) -> Image.Image:
    """Decode exactly the bounded bytes already admitted/hashed by the caller, never reopen a pathname."""
    if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds its byte limit")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP", "BMP"}:
                raise ValueError("Unsupported image type (PNG/JPEG/WebP/BMP only)")
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Image exceeds pixel limit")
            normalized = ImageOps.exif_transpose(image).convert("RGB")
            normalized.info.clear()
            return normalized
