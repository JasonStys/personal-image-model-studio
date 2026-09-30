"""Create explicitly public synthetic validation evidence; never copies dataset paths, weights or credentials."""

# Index: declarations module.main@L10; variables parser@L12, args@L15, result@L16, training@L17, destination@L22. Purposes/parameters: docs/code-map.json.
import shutil
import argparse
from pathlib import Path
from studio.files import read_json, atomic_json


def main():
    """Sanitize a known procedural demo into a small measurements report/contact sheet."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--prefix", choices=["synthetic", "synthetic-cpu"], default="synthetic")
    args = parser.parse_args()
    result = read_json(args.source / "validation.json", 2_000_000)
    training = result["training"]
    if training["name"] != "Synthetic shapes native diffusion" or training["settings"][
        "dataset_ids"
    ] != ["synthetic"]:
        raise SystemExit("Only the owned procedural demo may be published by this helper")
    destination = Path("docs/reports")
    destination.mkdir(parents=True, exist_ok=True)
    atomic_json(
        destination / f"{args.prefix}-training.json",
        {
            "evidence": "Actual procedural-dataset training, not a mocked pipeline",
            "trained_steps": training["trained_steps"],
            "status": training["status"],
            "learned_resolution": training["resolution"],
            "validation": training["validation"],
            "dataset_fingerprint": training["dataset_fingerprint"],
            "settings": training["settings"],
            "inference": result["inference"],
            "limitations": result["limitations"],
            "runtime_note": f"Actual training device {training['validation']['device']}; Torch {training['validation']['torch']}. Results from different devices/software stacks are not controlled comparative benchmarks.",
        },
    )
    shutil.copyfile(args.source / "samples.png", destination / f"{args.prefix}-samples.png")
    print(
        "Published owned synthetic measurements and preview; no training images/model weights copied"
    )


if __name__ == "__main__":
    main()
