"""Trusted ML subprocess entry point: input JSON, bounded progress and atomic terminal output."""

# Index: declarations module.run@L9, run.progress@L14, run.cancel@L18; variables directory@L9, request@L11, config@L12, references@L12, value@L14, model@L27, p@L29, result@L35, model@L39, p@L41, result@L47, source@L53, mask@L54, options@L59, details@L62, result@L72, result@L76, result@L78. Purposes/parameters: docs/code-map.json.
import sys
from pathlib import Path
from studio.files import atomic_json, read_json


def run(directory: Path) -> None:
    """Dispatch only recognized local tasks; complete artifacts must exist before result publication."""
    request = read_json(directory / "request.json")
    config, references = request["config"], request["references"]

    def progress(value):
        """Publish a small progress snapshot without retaining an unbounded event history."""
        atomic_json(directory / "progress.json", value)

    def cancel():
        """Read the parent-owned cooperative cancellation flag at safe model boundaries."""
        return (directory / "cancel").exists()

    try:
        if request["kind"] == "train":
            if config.get("mode", "native") == "lora":
                from studio.pretrained import train_lora

                model = train_lora(
                    config,
                    [Path(p) for p in references["datasets"]],
                    Path(references["base"]),
                    directory / "model",
                    progress,
                    cancel,
                )
                result = {"status": model["status"], "lora": "model", "details": model}
            else:
                from studio.training import train

                model = train(
                    config,
                    [Path(p) for p in references["datasets"]],
                    directory / "model",
                    Path(references["resume"]) if references.get("resume") else None,
                    progress,
                    cancel,
                )
                result = {
                    "status": "completed" if model["status"] == "completed" else "cancelled",
                    "model": "model",
                    "details": model["validation"],
                }
        elif request["kind"] == "generate":
            source = Path(references["source"]) if references.get("source") else None
            mask = Path(references["mask"]) if references.get("mask") else None
            if references["model_kind"] == "native":
                from studio.native import generate
            else:
                from studio.pretrained import generate
            options = (
                {"adapter_path": Path(references["adapter"])} if references.get("adapter") else {}
            )
            details = generate(
                config,
                Path(references["model"]),
                directory / "image.png",
                source,
                mask,
                progress,
                cancel,
                **options,
            )
            result = {"status": "completed", "image": "image.png", "details": details}
        else:
            raise ValueError("Unknown worker task")
    except InterruptedError:
        result = {"status": "cancelled"}
    except Exception as error:
        result = {"status": "failed", "error": str(error)[:500]}
    atomic_json(directory / "result.json", result)


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve(strict=True))
