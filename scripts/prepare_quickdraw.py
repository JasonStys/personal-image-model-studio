"""Opt-in, bounded CC BY 4.0 hand-drawing sample; no accounts, executable files or bulk download."""
# Index: declarations module.raster@L26, module.records@L75, module.prepare@L98, module.main@L170; variables SOURCE@L17, LICENSE@L18, BASE@L19, CATEGORIES@L20, MAX_BYTES@L21, MAX_LINE@L22, ATTRIBUTION@L23, category@L26, record@L26, strokes@L34, points@L37, total@L37, stroke@L38, xs@L41, ys@L41, total@L48, value@L51, flat@L55, point@L55, stroke@L55, left@L56, p@L56, p@L56, top@L56, bottom@L57, p@L57, p@L57, right@L57, extent@L58, scale@L61, dx@L62, dy@L62, canvas@L63, drawing@L64, stroke@L65, projected@L66, x@L66, y@L66, x@L68, y@L68, deadline@L75, response@L75, lines@L77, pending@L77, total@L77, chunk@L78, total@L79, _@L84, line@L84, rest@L84, pending@L85, lines@L86, output@L98, per_category@L98, transport@L98, output@L102, deadline@L106, counts@L107, seen@L107, temporary@L108, staging@L109, client@L112, category@L113, response@L119, record@L122, image@L123, fingerprint@L127, path@L131, summary@L154, category@L162, parser@L172, args@L176. Purposes/parameters: docs/code-map.json.

import argparse
import hashlib
import json
import math
import shutil
import tempfile
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw
from studio.files import atomic_json

SOURCE = "https://github.com/googlecreativelab/quickdraw-dataset"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
BASE = "https://storage.googleapis.com/quickdraw_dataset/full/simplified/"
CATEGORIES = ("sun", "flower", "fish")
MAX_BYTES = 2 * 1024 * 1024
MAX_LINE = 65536
ATTRIBUTION = "Quick, Draw! participants; dataset made available by Google, Inc.; CC BY 4.0"


def raster(record: dict, category: str) -> Image.Image | None:
    """Validate simplified XY strokes and render recognized drawings; discard participant metadata."""
    if not isinstance(record, dict) or record.get("word") != category:
        raise ValueError("Unexpected drawing category/record")
    if type(record.get("recognized")) is not bool:
        raise ValueError("Invalid recognition flag")
    if not record["recognized"]:
        return None
    strokes = record.get("drawing")
    if not isinstance(strokes, list) or not 1 <= len(strokes) <= 128:
        raise ValueError("Invalid drawing strokes")
    points, total = [], 0
    for stroke in strokes:
        if not isinstance(stroke, list) or len(stroke) != 2:
            raise ValueError("Expected simplified XY coordinates")
        xs, ys = stroke
        if (
            not isinstance(xs, list)
            or not isinstance(ys, list)
            or not 1 <= len(xs) == len(ys) <= 4096
        ):
            raise ValueError("Invalid coordinate lengths")
        total += len(xs)
        if total > 20000 or any(
            type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 255
            for value in xs + ys
        ):
            raise ValueError("Coordinates exceed drawing budget")
        points.append(list(zip(xs, ys, strict=True)))
    flat = [point for stroke in points for point in stroke]
    left, top = min(p[0] for p in flat), min(p[1] for p in flat)
    right, bottom = max(p[0] for p in flat), max(p[1] for p in flat)
    extent = max(right - left, bottom - top)
    if extent < 8:
        raise ValueError("Drawing has no usable extent")
    scale = 104 / extent
    dx, dy = 64 - (left + right) * scale / 2, 64 - (top + bottom) * scale / 2
    with Image.new("RGB", (128, 128), "white") as canvas:
        drawing = ImageDraw.Draw(canvas)
        for stroke in points:
            projected = [(x * scale + dx, y * scale + dy) for x, y in stroke]
            if len(projected) == 1:
                x, y = projected[0]
                drawing.ellipse((x - 2, y - 2, x + 2, y + 2), fill="black")
            else:
                drawing.line(projected, fill="black", width=4, joint="curve")
        return canvas.resize((32, 32), Image.Resampling.LANCZOS)


def records(response, deadline: float):
    """Stream bounded NDJSON lines; stop early and never buffer an entire public category file."""
    pending, total, lines = bytearray(), 0, 0
    for chunk in response.iter_bytes(chunk_size=8192):
        total += len(chunk)
        if total > MAX_BYTES or time.monotonic() > deadline:
            raise ValueError("Sample exceeded byte/time budget")
        pending.extend(chunk)
        while b"\n" in pending:
            line, _, rest = pending.partition(b"\n")
            pending = bytearray(rest)
            lines += 1
            if len(line) > MAX_LINE or lines > 4096:
                raise ValueError("Sample exceeded line budget")
            if line.strip():
                try:
                    yield json.loads(line)
                except (ValueError, UnicodeError, RecursionError):
                    raise ValueError("Invalid bounded NDJSON record") from None
        if len(pending) > MAX_LINE:
            raise ValueError("Sample exceeded line budget")


def prepare(output: Path, per_category: int = 128, transport=None) -> dict:
    """Atomically create a new attributed sample of three fixed categories; never overwrite data."""
    if type(per_category) is not int or not 16 <= per_category <= 128:
        raise ValueError("Choose 16..128 drawings per category")
    output = output.resolve()
    if output.exists():
        raise ValueError("Use a new sample directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 120
    counts, seen = {}, set()
    with tempfile.TemporaryDirectory(prefix=".quickdraw-", dir=output.parent) as temporary:
        staging = Path(temporary)
        with httpx.Client(
            transport=transport, timeout=20, trust_env=False, follow_redirects=False
        ) as client:
            for category in CATEGORIES:
                counts[category] = 0
                with client.stream(
                    "GET",
                    BASE + category + ".ndjson",
                    headers={"Range": f"bytes=0-{MAX_BYTES - 1}", "Accept-Encoding": "identity"},
                ) as response:
                    if response.status_code not in (200, 206):
                        raise ValueError(f"Public sample unavailable (HTTP {response.status_code})")
                    for record in records(response, deadline):
                        image = raster(record, category)
                        if image is None:
                            continue
                        with image:
                            fingerprint = hashlib.sha256(image.tobytes()).hexdigest()
                            if fingerprint in seen:
                                continue
                            seen.add(fingerprint)
                            path = staging / f"{category}-{counts[category]:03d}.png"
                            image.save(path)
                        atomic_json(
                            path.with_suffix(".json"),
                            {
                                "name": f"Quick Draw {category} sample",
                                "caption": f"black line drawing of {category} on white background",
                                "tags": [category, "hand drawing", "line art"],
                                "origin": "human",
                                "artist": ATTRIBUTION,
                                "license": f"CC BY 4.0; {LICENSE}; source {SOURCE}",
                                "source_url": BASE + category + ".ndjson",
                                "modifications": "recognized prefix sample; centered, scaled and rasterized at 32 pixels",
                                "disclaimer": "No endorsement or warranties; labels are dataset provenance, not AI detection",
                            },
                        )
                        counts[category] += 1
                        if counts[category] == per_category:
                            break
                if counts[category] != per_category:
                    raise ValueError(
                        "Insufficient unique recognized drawings within bounded prefix"
                    )
        summary = {
            "source": SOURCE,
            "license": LICENSE,
            "attribution": ATTRIBUTION,
            "counts": counts,
            "total": sum(counts.values()),
            "selection": "first unique recognized drawings in bounded category prefixes; not representative",
            "modifications": "participant metadata discarded; vectors centered and rasterized to 32x32 RGB",
            "source_urls": [BASE + category + ".ndjson" for category in CATEGORIES],
            "limitations": "source moderation is not a visual safety guarantee; inspect before further use",
        }
        atomic_json(staging / "source.json", summary)
        shutil.move(str(staging), str(output))
        return summary


def main():
    """Require explicit opt-in before fetching public data; report only non-account sample metadata."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-category", type=int, default=128)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if not args.download:
        parser.error("Review docs/licensed-sample.md, then explicitly opt in with --download")
    print(json.dumps(prepare(args.output, args.per_category), indent=2))


if __name__ == "__main__":
    main()
