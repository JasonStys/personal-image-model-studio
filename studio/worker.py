"""Trusted ML subprocess entry point: input JSON, bounded progress and atomic terminal output."""

# Index: declarations module.run@L11, run.parent_closed@L15, run.progress@L33, run.cancel@L37; variables directory@L11, parent@L20, request@L29, config@L30, references@L30, value@L33, model@L46, p@L48, result@L54, model@L60, p@L62, result@L68, source@L74, mask@L75, options@L80, details@L83, result@L93, result@L97, result@L99. Purposes/parameters: docs/code-map.json.
import sys
import os
import threading
from pathlib import Path
from studio.files import atomic_json, read_json


def run(directory: Path) -> None:
    """Dispatch only recognized local tasks; complete artifacts must exist before result publication."""
    if os.environ.get("PIMS_PARENT_GUARD") == "1":

        def parent_closed():
            """Watch the exact parent PID/create-time pair without interfering with ML libraries' standard I/O."""
            import psutil

            try:
                parent = psutil.Process(int(os.environ["PIMS_PARENT_PID"]))
                if parent.create_time() != float(os.environ["PIMS_PARENT_STARTED"]):
                    os._exit(143)
                parent.wait()
            except (psutil.Error, ValueError, KeyError):
                pass
            os._exit(143)

        threading.Thread(target=parent_closed, daemon=True, name="parent-lifecycle").start()
    request = read_json(directory / "request.json")
    config, references = request["config"], request["references"]
    atomic_json(directory / "progress.json", {"stage": "trusted-worker-entry"})

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
                progress({"stage": "loading-native-training-runtime"})
                from studio.training import train

                progress({"stage": "starting-native-optimization"})
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
