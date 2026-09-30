"""Create explicitly public synthetic validation evidence; never copies dataset paths, weights or credentials."""

# Index: declarations module.main@L10; variables parser@L12, args@L14, result@L15, training@L16, destination@L21. Purposes/parameters: docs/code-map.json.
import shutil
import argparse
from pathlib import Path
from studio.files import read_json, atomic_json


def main():
    """Sanitize a known procedural demo into a small measurements report/contact sheet."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
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
        destination / "synthetic-training.json",
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
            "runtime_note": "GPU baseline used Torch 2.11 CUDA before the new reference environment's security upgrades to Torch 2.14 CPU; not a Torch 2.14 GPU benchmark",
        },
    )
    shutil.copyfile(args.source / "samples.png", destination / "synthetic-samples.png")
    print(
        "Published owned synthetic measurements and preview; no training images/model weights copied"
    )


if __name__ == "__main__":
    main()
