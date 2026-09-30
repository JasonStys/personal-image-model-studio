"""Owned local/ZIP dataset ingestion with provenance, duplicate-aware splits and AI quarantine."""

# Index: declarations module.extract_zip@L19, module.scan@L45, module.image_record@L58, module.import_dataset@L100, module.eligible@L174, module.synthetic_dataset@L183; variables EXTENSIONS@L14, MAX_ITEMS@L15, MAX_ZIP_BYTES@L16, destination@L19, path@L19, archive@L23, members@L24, m@L25, member@L27, name@L28, unsafe@L29, root@L45, count@L47, path@L48, count@L49, path@L58, metadata_path@L60, metadata@L61, caption_path@L62, caption@L65, tags@L72, t@L76, origin@L79, t@L83, origin@L85, image@L86, pixel_hash@L87, record@L88, name@L100, output@L100, paths@L100, temporary@L105, staging@L106, prepared@L107, records@L109, seen@L109, index@L110, source@L110, source_path@L111, root@L113, images@L116, images@L120, path@L123, image@L124, record@L124, previous@L127, bucket@L140, target@L141, fingerprint@L151, r@L153, manifest@L157, r@L165, manifest@L174, split@L174, r@L178, count@L183, output@L183, seed@L183, rng@L189, temporary@L191, root@L192, colors@L193, index@L194, color@L195, shape@L196, image@L197, drawing@L198, left@L199, top@L199, bottom@L200, right@L200, box@L201, path@L210. Purposes/parameters: docs/code-map.json.
import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from PIL import Image, ImageDraw
from studio.files import atomic_json, digest, normalized_image, read_json

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MAX_ITEMS = 10000
MAX_ZIP_BYTES = 200 * 1024 * 1024


def extract_zip(path: Path, destination: Path) -> None:
    """Validate every member before extraction; block traversal, links, bombs and encrypted ZIPs."""
    if path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("ZIP exceeds 200 MiB")
    with zipfile.ZipFile(path) as archive:
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
        if path.is_symlink():
            raise ValueError("Dataset links are not followed")
        if path.is_file() and path.suffix.casefold() in EXTENSIONS:
            yield path


def image_record(path: Path) -> tuple[dict, Image.Image]:
    """Combine safe sidecar metadata/caption with normalized pixels and explicit origin evidence."""
    metadata_path = path.with_suffix(".json")
    metadata = read_json(metadata_path, 32000) if metadata_path.exists() else {}
    caption_path = path.with_suffix(".txt")
    if caption_path.exists() and caption_path.stat().st_size > 8000:
        raise ValueError("Caption exceeds 8 KiB")
    caption = (
        caption_path.read_text(encoding="utf-8").strip()
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
