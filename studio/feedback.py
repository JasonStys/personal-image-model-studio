"""Explicit bounded feedback export; AI-produced pixels retain origin labels and human consent."""

# Index: declarations module.export_feedback@L11; variables store@L11, buffer@L13, count@L14, size@L14, archive@L15, image@L16, entries@L17, consent@L18, path@L21, size@L22, prompt@L25, caption@L26, field@L28, metadata@L31, count@L41. Purposes/parameters: docs/code-map.json.
import io
import json
import zipfile
from pathlib import Path
from studio.store import Store


def export_feedback(store: Store) -> bytes:
    """Export up to 32 consenting generated examples, capped at 64 MiB; never relabel them human art."""
    buffer = io.BytesIO()
    count, size = 0, 0
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for image in store.list("image", 100):
            entries = store.feedback(image["id"])
            consent = entries[0] if entries and entries[0].get("allow_training") else None
            if not consent or not image.get("request"):
                continue
            path = Path(image["path"])
            size += path.stat().st_size
            if size > 64 * 1024 * 1024 or count >= 32:
                raise ValueError("Feedback export exceeds bounded limit; use a smaller workspace")
            prompt = image["request"]["prompt"]
            caption = ", ".join(
                str(prompt.get(field, ""))
                for field in ("description", "style", "tags")
                if prompt.get(field)
            )[:2000]
            metadata = {
                "origin": "ai_generated",
                "tags": ["ai-generated"],
                "caption": caption,
                "name": image["name"],
                "feedback": consent,
                "license": "Human consent for explicit local feedback experiments",
            }
            archive.write(path, image["id"] + ".png")
            archive.writestr(image["id"] + ".json", json.dumps(metadata, allow_nan=False))
            count += 1
    if not count:
        raise ValueError("No generated images have explicit feedback-export consent")
    return buffer.getvalue()
