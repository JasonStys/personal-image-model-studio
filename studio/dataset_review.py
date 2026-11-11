"""Read-only, bounded dataset readiness review by Jason Stys.
# Index: declarations module.manifest_records@L29, module.difference_hash@L80, module.review_dataset@L91, module.dataset_thumbnail@L208; variables MAX_RECORDS@L21, MAX_SAMPLE@L22, MAX_SAMPLE_BYTES@L23, MAX_SAMPLE_PIXELS@L24, MAX_PAIRS_SHOWN@L25, ORIGINS@L26, expected@L29, root@L29, manifest@L31, records@L32, seen@L41, record@L42, identity@L45, fingerprint@L67, r@L69, image@L80, gray@L82, small@L82, pixels@L83, value@L84, row@L85, column@L86, value@L87, expected@L91, root@L91, _@L93, records@L93, origins@L94, record@L94, eligible@L95, r@L95, splits@L96, r@L97, r@L97, split@L98, selected@L101, index@L102, split@L103, errors@L106, sampled@L106, used_bytes@L107, used_pixels@L107, budget_stopped@L108, record@L109, file@L111, content@L112, size@L113, budget_stopped@L115, header@L119, pixels@L120, budget_stopped@L122, used_bytes@L124, used_pixels@L125, image@L126, candidates@L141, comparisons@L142, pair_count@L142, index@L143, left@L143, left_hash@L143, right@L144, right_hash@L144, comparisons@L147, distance@L148, pair_count@L150, key@L154, key@L155, captions@L159, r@L159, report@L160, r@L165, r@L166, r@L170, expected@L208, identity@L208, root@L208, _@L212, records@L212, item@L213, record@L213, file@L216, content@L217, source@L225, image@L228, output@L236. Purposes/parameters: docs/code-map.json.

Summarizes caption/provenance/split evidence and sampled cross-split visual
similarity. Candidates are review aids, never proof of leakage or authorization.
Exact declarations and variables are generated in docs/code-map.json.
"""

import hashlib
import json
import io
import warnings
import re
from collections import Counter
from pathlib import Path

from PIL import Image

from studio.files import confined, normalized_pixels, read_json, regular_bytes

MAX_RECORDS = 10_000
MAX_SAMPLE = 64
MAX_SAMPLE_BYTES = 32 * 1024 * 1024
MAX_SAMPLE_PIXELS = 16_777_216
MAX_PAIRS_SHOWN = 32
ORIGINS = {"human", "synthetic_procedural", "ai_generated", "ai_assisted", "unknown"}


def manifest_records(root: Path, expected: str) -> tuple[dict, list[dict]]:
    """Validate exact normalized imported identities and the existing dataset fingerprint."""
    manifest = read_json(root / "dataset.json", 8 * 1024 * 1024)
    records = manifest.get("records")
    if (
        type(manifest.get("schema")) is not int
        or manifest.get("schema") != 1
        or manifest.get("rights_confirmed") is not True
        or not isinstance(records, list)
        or not 1 <= len(records) <= MAX_RECORDS
    ):
        raise ValueError("Dataset manifest is incomplete or exceeds review limits")
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid dataset review record")
        identity = record.get("hash")
        if (
            not isinstance(identity, str)
            or not re.fullmatch(r"[a-f0-9]{64}", identity)
            or identity in seen
            or not isinstance(record.get("file_sha256"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", record["file_sha256"])
            or not isinstance(record.get("split"), str)
            or record.get("split") not in {"train", "validation"}
            or not isinstance(record.get("origin"), str)
            or record.get("origin") not in ORIGINS
            or not isinstance(record.get("caption"), str)
            or len(record["caption"]) > 2000
            or not isinstance(record.get("name"), str)
            or len(record["name"]) > 200
            or not isinstance(record.get("license"), str)
            or len(record["license"]) > 500
            or record.get("file")
            != f"{'flagged' if record['origin'].startswith('ai_') else 'images'}/{identity}.png"
        ):
            raise ValueError("Dataset review identity or metadata is invalid")
        seen.add(identity)
    fingerprint = hashlib.sha256(
        json.dumps(
            sorted((r["hash"], r["caption"], r["origin"], r["split"]) for r in records),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    if expected != fingerprint or manifest.get("fingerprint") != fingerprint:
        raise ValueError(
            "Dataset changed since import; reconcile and import a new dataset before review"
        )
    return manifest, records


def difference_hash(image: Image.Image) -> int:
    """Compute 64 horizontal grayscale comparisons; collisions and semantic differences remain possible."""
    with image.convert("L") as gray, gray.resize((9, 8), Image.Resampling.LANCZOS) as small:
        pixels = small.tobytes()
    value = 0
    for row in range(8):
        for column in range(8):
            value = (value << 1) | (pixels[row * 9 + column] > pixels[row * 9 + column + 1])
    return value


def review_dataset(root: Path, expected: str) -> dict:
    """Inspect only normalized local data without altering manifests, training selection, models or pixels."""
    _, records = manifest_records(root, expected)
    origins = Counter(record["origin"] for record in records)
    eligible = [r for r in records if r["caption"].strip() and not r["origin"].startswith("ai_")]
    splits = {
        split: sorted((r for r in eligible if r["split"] == split), key=lambda r: r["hash"])
        for split in ("train", "validation")
    }
    # Interleave both splits so the bounded sample does not accidentally contain only one split.
    selected = []
    for index in range(MAX_SAMPLE):
        for split in ("train", "validation"):
            if index < len(splits[split]) and len(selected) < MAX_SAMPLE:
                selected.append(splits[split][index])
    sampled, errors = [], []
    used_bytes = used_pixels = 0
    budget_stopped = False
    for record in selected:
        try:
            file = confined(root, record["file"])
            content = regular_bytes(file, 20 * 1024 * 1024)
            size = len(content)
            if used_bytes + size > MAX_SAMPLE_BYTES:
                budget_stopped = True
                break
            if hashlib.sha256(content).hexdigest() != record["file_sha256"]:
                raise ValueError("Image file fingerprint differs from the imported record")
            with Image.open(io.BytesIO(content)) as header:
                pixels = header.width * header.height
            if used_pixels + pixels > MAX_SAMPLE_PIXELS:
                budget_stopped = True
                break
            used_bytes += size
            used_pixels += pixels
            with normalized_pixels(content) as image:
                if (
                    hashlib.sha256(f"{image.size}".encode() + image.tobytes()).hexdigest()
                    != record["hash"]
                ):
                    raise ValueError("Normalized pixels differ from the imported identity")
                sampled.append((record, difference_hash(image)))
        except (ValueError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            errors.append(
                {
                    "hash": record["hash"],
                    "name": record["name"],
                    "reason": "Missing, changed, unsupported or unsafe image; reconcile the source and import a new dataset",
                }
            )
    candidates = []
    pair_count = comparisons = 0
    for index, (left, left_hash) in enumerate(sampled):
        for right, right_hash in sampled[index + 1 :]:
            if left["split"] == right["split"]:
                continue
            comparisons += 1
            distance = (left_hash ^ right_hash).bit_count()
            if distance <= 4:
                pair_count += 1
                if len(candidates) < MAX_PAIRS_SHOWN:
                    candidates.append(
                        {
                            "left": {key: left[key] for key in ("hash", "name", "split")},
                            "right": {key: right[key] for key in ("hash", "name", "split")},
                            "difference_bits": distance,
                        }
                    )
    captions = Counter(r["caption"].strip().casefold() for r in eligible)
    report = {
        "schema": 1,
        "dataset_fingerprint": expected,
        "counts": {
            "total": len(records),
            "missing_captions": sum(not r["caption"].strip() for r in records),
            "ai_excluded": sum(r["origin"].startswith("ai_") for r in records),
            "unknown_origin": origins["unknown"],
            "default_or_missing_license_note": sum(
                not r["license"].strip() or r["license"] == "operator rights declaration"
                for r in records
            ),
            "eligible_train": len(splits["train"]),
            "eligible_validation": len(splits["validation"]),
            "unique_eligible_captions": len(captions),
        },
        "origins": dict(sorted(origins.items())),
        "minimum_training_counts_met": len(splits["train"]) >= 8 and len(splits["validation"]) >= 2,
        "inspection": {
            "maximum_images": MAX_SAMPLE,
            "maximum_file_bytes": MAX_SAMPLE_BYTES,
            "maximum_pixels": MAX_SAMPLE_PIXELS,
            "selected_images": len(selected),
            "verified_images": len(sampled),
            "remaining_eligible_not_verified": len(eligible) - len(sampled),
            "budget_stopped": budget_stopped,
            "file_bytes": used_bytes,
            "pixels": used_pixels,
            "cross_split_comparisons": comparisons,
            "integrity_errors": errors,
        },
        "near_duplicate_candidates": candidates,
        "candidate_pairs_total": pair_count,
        "candidate_pairs_not_shown": pair_count - len(candidates),
        "method": "64-bit horizontal grayscale difference hash, Hamming distance <=4; cross-split pairs only, deterministic hash-ordered interleaved sample",
        "limitations": [
            "Candidates are not proof of leakage: different colors, flat images, crops and semantic differences can collide or be missed.",
            "Only the bounded sample has pixel/file integrity checks; zero candidates does not establish leak-free splits.",
            "Rights and origin labels are operator declarations, not legal verification or an AI-origin detector.",
            "Counts are training prerequisites only, not an image-quality or model-quality score. Review never changes splits, captions, exclusions or weights.",
        ],
    }
    report["report_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return report


def dataset_thumbnail(root: Path, expected: str, identity: str) -> bytes:
    """Return a metadata-free bounded PNG only for a known, integrity-checked imported record."""
    if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{64}", identity):
        raise KeyError("Unknown dataset image")
    _, records = manifest_records(root, expected)
    record = next((item for item in records if item["hash"] == identity), None)
    if record is None:
        raise KeyError("Unknown dataset image")
    file = confined(root, record["file"])
    content = regular_bytes(file, 20 * 1024 * 1024)
    if (
        len(content) > 20 * 1024 * 1024
        or hashlib.sha256(content).hexdigest() != record["file_sha256"]
    ):
        raise ValueError("Image changed after import; reconcile and import a new dataset")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(content)) as source:
            if source.format != "PNG" or source.width * source.height > 4_194_304:
                raise ValueError("Dataset thumbnail source exceeds normalized image limits")
            with source.convert("RGB") as image:
                if (
                    hashlib.sha256(f"{image.size}".encode() + image.tobytes()).hexdigest()
                    != record["hash"]
                ):
                    raise ValueError("Dataset pixels differ from the imported identity")
                image.thumbnail((192, 192), Image.Resampling.LANCZOS)
                image.info.clear()
                output = io.BytesIO()
                image.save(output, format="PNG")
                return output.getvalue()
