"""Owned local/ZIP dataset ingestion with provenance, duplicate-aware splits and AI quarantine."""

# Index: declarations module.extract_zip@L27, module.scan@L51, module.image_record@L65, module.import_dataset@L105, module.eligible@L179, module.synthetic_dataset@L188; variables EXTENSIONS@L22, MAX_ITEMS@L23, MAX_ZIP_BYTES@L24, destination@L27, path@L27, archive@L29, stream@L29, members@L30, m@L31, member@L33, name@L34, unsafe@L35, root@L51, count@L53, path@L54, count@L55, path@L65, metadata_path@L67, metadata@L68, caption_path@L69, caption@L70, tags@L77, t@L81, origin@L84, t@L88, origin@L90, image@L91, pixel_hash@L92, record@L93, name@L105, output@L105, paths@L105, temporary@L110, staging@L111, prepared@L112, records@L114, seen@L114, index@L115, source@L115, source_path@L116, root@L118, images@L121, images@L125, path@L128, image@L129, record@L129, previous@L132, bucket@L145, target@L146, fingerprint@L156, r@L158, manifest@L162, r@L170, manifest@L179, split@L179, r@L183, count@L188, output@L188, seed@L188, rng@L194, temporary@L196, root@L197, colors@L198, index@L199, color@L200, shape@L201, image@L202, drawing@L203, left@L204, top@L204, bottom@L205, right@L205, box@L206, path@L215. Purposes/parameters: docs/code-map.json.
import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from PIL import Image, ImageDraw
from studio.files import (
    atomic_json,
    digest,
    normalized_image,
    read_json,
    regular_stream,
    regular_bytes,
    no_alias,
)

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MAX_ITEMS = 10000
MAX_ZIP_BYTES = 200 * 1024 * 1024


def extract_zip(path: Path, destination: Path) -> None:
    """Validate every member before extraction; block traversal, links, bombs and encrypted ZIPs."""
    with regular_stream(path, MAX_ZIP_BYTES) as stream, zipfile.ZipFile(stream) as archive:
        members = archive.infolist()
        if len(members) > MAX_ITEMS or sum(m.file_size for m in members) > MAX_ZIP_BYTES:
            raise ValueError("ZIP exceeds item/expanded-size limits")
        for member in members:
            name = PurePosixPath(member.filename)
            unsafe = (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in member.orig_filename
                or ":" in member.orig_filename
                or "\x00" in member.orig_filename
            )
            if unsafe or stat.S_ISLNK(member.external_attr >> 16) or member.flag_bits & 1:
                raise ValueError("ZIP contains an unsafe path, link or encrypted member")
            if member.file_size / max(1, member.compress_size) > 200:
                raise ValueError("ZIP compression ratio is too high")
            if not member.is_dir() and name.suffix.casefold() not in EXTENSIONS | {".txt", ".json"}:
                raise ValueError("ZIP contains unsupported files")
        archive.extractall(destination)


def scan(root: Path):
    """Yield bounded image paths without following symlinks; count all files to bound scanning work."""
    count = 0
    for path in root.rglob("*"):
        count += 1
        if count > MAX_ITEMS * 4:
            raise ValueError("Source contains too many files")
        if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Dataset links are not followed")
        if path.is_file() and path.suffix.casefold() in EXTENSIONS:
            no_alias(path)
            yield path


def image_record(path: Path) -> tuple[dict, Image.Image]:
    """Combine safe sidecar metadata/caption with normalized pixels and explicit origin evidence."""
    metadata_path = path.with_suffix(".json")
    metadata = read_json(metadata_path, 32000) if metadata_path.exists() else {}
    caption_path = path.with_suffix(".txt")
    caption = (
        regular_bytes(caption_path, 8000).decode("utf-8").strip()
        if caption_path.exists()
        else metadata.get("caption", "")
    )
    if not isinstance(caption, str) or len(caption) > 2000:
        raise ValueError("Invalid caption")
    tags = metadata.get("tags", [])
    if (
        not isinstance(tags, list)
        or len(tags) > 64
        or any(not isinstance(t, str) or len(t) > 100 for t in tags)
    ):
        raise ValueError("Invalid tag list")
    origin = metadata.get("origin", "unknown")
    if origin not in {"human", "synthetic_procedural", "ai_generated", "ai_assisted", "unknown"}:
        raise ValueError("Unknown origin label")
    if origin == "unknown" and any(
        t.casefold() in {"ai generated", "ai-generated", "ai assisted", "ai-assisted"} for t in tags
    ):
        origin = "ai_generated"
    image = normalized_image(path)
    pixel_hash = hashlib.sha256(f"{image.size}".encode() + image.tobytes()).hexdigest()
    record = {
        "hash": pixel_hash,
        "caption": caption,
        "tags": tags,
        "origin": origin,
        "name": str(metadata.get("name", path.stem))[:200],
        "artist": str(metadata.get("artist", ""))[:200],
        "license": str(metadata.get("license", "operator rights declaration"))[:500],
    }
    return record, image


def import_dataset(paths: list[str], output: Path, name: str) -> dict:
    """Atomically publish a dataset; deduplicate normalized pixels before deterministic splitting."""
    if output.exists():
        raise ValueError("Dataset output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".import-", dir=output.parent) as temporary:
        staging = Path(temporary)
        prepared = staging / "prepared"
        prepared.mkdir()
        records, seen = [], {}
        for index, source in enumerate(paths):
            source_path = Path(source).resolve(strict=True)
            if source_path.is_file() and source_path.suffix.casefold() == ".zip":
                root = staging / f"zip-{index}"
                root.mkdir()
                extract_zip(source_path, root)
                images = scan(root)
            elif source_path.is_dir():
                if output.resolve().is_relative_to(source_path):
                    raise ValueError("Dataset output must not be inside an input source")
                images = scan(source_path)
            else:
                raise ValueError("Source must be an image folder or ZIP")
            for path in images:
                record, image = image_record(path)
                if record["hash"] in seen:
                    image.close()
                    previous = seen[record["hash"]]
                    if (record["origin"], record["caption"]) != (
                        previous["origin"],
                        previous["caption"],
                    ):
                        raise ValueError(
                            "Duplicate pixels have conflicting origin/caption metadata; reconcile sources first"
                        )
                    continue
                seen[record["hash"]] = record
                if len(seen) > MAX_ITEMS:
                    raise ValueError("Dataset exceeds 10000 unique images")
                # AI-origin examples are retained but excluded by training's eligible filter.
                bucket = "flagged" if record["origin"].startswith("ai_") else "images"
                target = prepared / bucket / f"{record['hash']}.png"
                target.parent.mkdir(exist_ok=True)
                image.save(target)
                image.close()
                record["file"] = target.relative_to(prepared).as_posix()
                record["file_sha256"] = digest(target)
                record["split"] = "train" if int(record["hash"][:8], 16) % 10 < 8 else "validation"
                records.append(record)
        if not records:
            raise ValueError("No supported images found")
        fingerprint = hashlib.sha256(
            json.dumps(
                sorted((r["hash"], r["caption"], r["origin"], r["split"]) for r in records),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        manifest = {
            "schema": 1,
            "name": name,
            "fingerprint": fingerprint,
            "records": records,
            "rights_confirmed": True,
            "counts": {
                "total": len(records),
                "flagged": sum(r["origin"].startswith("ai_") for r in records),
            },
        }
        atomic_json(prepared / "dataset.json", manifest)
        atomic_json(prepared / "glossary.json", {"schema": 1, "entries": {}})
        shutil.move(str(prepared), str(output))
        return manifest


def eligible(manifest: dict, split: str) -> list[dict]:
    """Only captioned non-AI-origin records in the chosen split may enter ordinary training."""
    return [
        r
        for r in manifest["records"]
        if r["split"] == split and r["caption"].strip() and not r["origin"].startswith("ai_")
    ]


def synthetic_dataset(output: Path, count: int = 384, seed: int = 42) -> dict:
    """Create licensed procedural shapes and captions; no pretrained model or downloaded art is used."""
    import random

    if output.exists() or not 24 <= count <= 1024:
        raise ValueError("Use a new output directory and 24..1024 samples")
    rng = random.Random(seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".synthetic-", dir=output.parent) as temporary:
        root = Path(temporary)
        colors = {"red": (235, 55, 70), "green": (45, 190, 105), "blue": (45, 110, 230)}
        for index in range(count):
            color = list(colors)[index % 3]
            shape = ("circle", "square", "triangle")[(index // 3) % 3]
            image = Image.new("RGB", (32, 32), (245, 245, 245))
            drawing = ImageDraw.Draw(image)
            left, top = rng.randint(4, 9), rng.randint(4, 9)
            right, bottom = rng.randint(23, 28), rng.randint(23, 28)
            box = (left, top, right, bottom)
            if shape == "circle":
                drawing.ellipse(box, fill=colors[color])
            elif shape == "square":
                drawing.rectangle(box, fill=colors[color])
            else:
                drawing.polygon(
                    ((left + right) // 2, top, right, bottom, left, bottom), fill=colors[color]
                )
            path = root / f"sample-{index:04d}.png"
            image.save(path)
            image.close()
            atomic_json(
                path.with_suffix(".json"),
                {
                    "caption": f"{color} {shape} on white background",
                    "origin": "synthetic_procedural",
                    "license": "CC0 procedural test data",
                    "artist": "repository synthetic generator",
                    "tags": [color, shape],
                },
            )
        return import_dataset([str(root)], output, "Synthetic colored shapes")
