"""Evaluate an actual licensed sketch checkpoint and export sanitized generated evidence only."""
# Index: declarations module.evaluate@L17, module.main@L123; variables dataset_path@L17, model_path@L17, output@L17, dataset@L21, records@L22, category@L29, record@L30, fingerprint@L33, heldout@L33, training@L33, _@L34, manifest@L34, model@L34, metrics@L35, value@L39, key@L42, record@L47, training_hashes@L47, heldout_hashes@L48, record@L48, generations@L52, samples@L52, sheet@L53, labels@L54, category@L55, row@L55, column@L57, seed@L57, name@L58, path@L59, config@L60, details@L71, image@L72, duplicate@L77, report@L90, key@L108, value@L108, parser@L125, args@L129, result@L130. Purposes/parameters: docs/code-map.json.

import argparse
import math
from pathlib import Path

import torch
from PIL import Image, ImageDraw
from scripts.prepare_quickdraw import ATTRIBUTION, CATEGORIES, LICENSE, SOURCE
from studio import checkpoints
from studio.files import atomic_json, digest, read_json
from studio.native import generate
from studio.training import prepare_dataset


def evaluate(model_path: Path, dataset_path: Path, output: Path) -> dict:
    """Require attributed public samples and matching verified model/data; reject existing output."""
    if output.exists():
        raise ValueError("Use a new evaluation directory")
    dataset = read_json(dataset_path / "dataset.json", 16 * 1024 * 1024)
    records = dataset["records"]
    if not 48 <= len(records) <= 384 or any(
        record["artist"] != ATTRIBUTION
        or record["origin"] != "human"
        or LICENSE not in record["license"]
        or SOURCE not in record["license"]
        or record["caption"]
        not in {f"black line drawing of {category} on white background" for category in CATEGORIES}
        for record in records
    ):
        raise ValueError("This exporter accepts only the explicitly attributed Quick Draw recipe")
    training, heldout, fingerprint = prepare_dataset([dataset_path])
    model, manifest, _ = checkpoints.load(model_path, "cpu")
    metrics = manifest["validation"]
    if (
        manifest["status"] != "completed"
        or manifest["dataset_fingerprint"] != fingerprint
        or not all(torch.isfinite(value).all().item() for value in model.parameters())
        or not all(
            math.isfinite(metrics[key])
            for key in ("initial_noise_mse", "final_noise_mse", "ema_noise_mse")
        )
        or metrics["final_noise_mse"] >= metrics["initial_noise_mse"]
    ):
        raise ValueError("Model/data/finite-learning verification failed")
    training_hashes = {record["hash"] for record in records if record["split"] == "train"}
    heldout_hashes = {record["hash"] for record in records if record["split"] == "validation"}
    if training_hashes & heldout_hashes:
        raise ValueError("Train/held-out pixel leakage")
    output.mkdir(parents=True)
    samples, generations = [], []
    with Image.new("RGB", (384, 500), "white") as sheet:
        labels = ImageDraw.Draw(sheet)
        for row, category in enumerate(CATEGORIES):
            labels.text((4, row * 152 + 4), f"{category} | seeds 2026, 2027, 2028", fill="black")
            for column, seed in enumerate((2026, 2027, 2028)):
                name = f"{category}-{seed}.png"
                path = output / name
                config = {
                    "model_id": "public-sketch-sample",
                    "prompt": {
                        "description": f"black line drawing of {category} on white background"
                    },
                    "width": 128,
                    "height": 128,
                    "steps": 50,
                    "guidance": 2,
                    "seed": seed,
                }
                details = generate(config, model_path, path, device="cpu")
                with Image.open(path) as image:
                    sheet.paste(image, (column * 128, row * 152 + 24))
                samples.append(digest(path))
                generations.append({"category": category, "seed": seed, "details": details})
                if row == 0 and column == 0:
                    duplicate = output / "repeat-seed.png"
                    generate(config, model_path, duplicate, device="cpu")
                    if digest(duplicate) != samples[-1]:
                        raise ValueError("Same-stack seed replay failed")
        if len(set(samples)) != len(samples):
            raise ValueError("Prompt/seed examples did not produce distinct artifacts")
        labels.text(
            (4, 460), "Learned AI outputs, not source strokes; 32px displayed larger", fill="black"
        )
        labels.text(
            (4, 476), "Training data: Quick Draw / Google, CC BY 4.0 (see report)", fill="black"
        )
        sheet.save(output / "samples.png")
    report = {
        "evidence": "Actual from-scratch training and learned inference on public hand drawings",
        "source": SOURCE,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "modifications": "recognized subset; vectors centered/rasterized to 32px; model outputs AI generated",
        "no_endorsement_or_warranties": True,
        "dataset": {
            "total": len(records),
            "train_images": len(training),
            "heldout_images": len(heldout),
            "disjoint_normalized_pixels": True,
            "fingerprint": fingerprint,
        },
        "trained_steps": manifest["trained_steps"],
        "learned_resolution": manifest["resolution"],
        "settings": {
            key: value
            for key, value in manifest["settings"].items()
            if key not in {"dataset_ids", "resume_model_id", "base_model_id"}
        },
        "validation": metrics,
        "heldout_noise_evaluation_examples": min(16, len(heldout)),
        "inference_runtime": {"torch": torch.__version__, "device": "cpu"},
        "same_seed_replay": "passed on this CPU/software stack",
        "distinct_prompt_seed_artifacts": len(set(samples)),
        "generations": generations,
        "limitations": "Small proof-of-function sketch model; prefix sample is not representative. Noise MSE and distinct pixels do not establish semantic correctness, visual safety or polished artwork. No pretrained model or account artwork used.",
    }
    atomic_json(output / "validation.json", report)
    return report


def main():
    """Validate a selected checkpoint/data pair; leave weights, training artwork and private IDs local."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.model, args.dataset, args.output)
    print(f"Verified {result['trained_steps']} learned steps and 9 generated samples")


if __name__ == "__main__":
    main()
