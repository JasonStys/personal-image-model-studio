"""Train and evaluate a real synthetic custom model; publish reports/previews, never private datasets."""

# Index: declarations module.main@L14, main.progress@L39; variables parser@L16, args@L20, root@L21, dataset@L25, settings@L27, value@L39, started@L43, manifest@L44, reports@L45, colors@L46, shapes@L47, sheet@L48, row@L49, shape@L49, color@L50, column@L50, name@L51, path@L52, config@L53, image@L68. Purposes/parameters: docs/code-map.json.
import argparse
import time
from pathlib import Path
from PIL import Image
from studio.datasets import synthetic_dataset
from studio.files import atomic_json
from studio.training import train
from studio.native import generate


def main():
    """Run fresh bounded training and compare seeded before/after text-conditioned outputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("artifacts/demo"))
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    args = parser.parse_args()
    root = args.root.resolve()
    if root.exists():
        raise SystemExit("Use a new artifact directory; this script never overwrites past results")
    root.mkdir(parents=True)
    dataset = root / "dataset"
    synthetic_dataset(dataset)
    settings = {
        "name": "Synthetic shapes native diffusion",
        "dataset_ids": ["synthetic"],
        "steps": args.steps,
        "resolution": 32,
        "batch_size": 16,
        "learning_rate": 0.001,
        "seed": 1337,
        "device": args.device,
        "max_seconds": 1800,
    }

    def progress(value):
        """Emit short progress records; no tensors or private captions enter logs."""
        print(value, flush=True)

    started = time.perf_counter()
    manifest = train(settings, [dataset], root / "model", progress=progress)
    reports = []
    colors = ("red", "green", "blue")
    shapes = ("circle", "square", "triangle")
    sheet = Image.new("RGB", (3 * 128, 3 * 128))
    for row, shape in enumerate(shapes):
        for column, color in enumerate(colors):
            name = f"{color}-{shape}"
            path = root / f"{name}.png"
            config = {
                "model_id": "demo",
                "prompt": {"description": f"{color} {shape} on white background"},
                "seed": 2026,
                "width": 128,
                "height": 128,
                "steps": 50,
                "guidance": 2.0,
            }
            reports.append(
                {
                    "prompt": config["prompt"],
                    **generate(config, root / "model", path, device=args.device),
                }
            )
            with Image.open(path) as image:
                sheet.paste(image, (column * 128, row * 128))
    sheet.save(root / "samples.png")
    sheet.close()
    atomic_json(
        root / "validation.json",
        {
            "training": manifest,
            "inference": reports,
            "total_seconds": time.perf_counter() - started,
            "limitations": "Small captioned procedural domain, not a general-purpose or photorealistic image model. Denoising MSE is not semantic quality.",
        },
    )
    print("Real custom-model validation complete:", root, flush=True)


if __name__ == "__main__":
    main()
