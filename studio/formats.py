"""Lightweight fixed-class pretrained model inspection; no ML imports or executable model code."""

# Index: declarations module.inspect_diffusers@L19, module.model_fingerprint@L102; variables SCHEDULERS@L8, path@L19, model@L21, expected@L26, contract@L32, name@L32, scheduler@L35, allowed@L43, key@L43, key@L50, value@L50, count@L58, size@L58, file@L59, count@L60, size@L68, index@L72, mapping@L73, shard@L76, shard@L78, target@L87, component@L96, path@L102, signature@L105, file@L106. Purposes/parameters: docs/code-map.json.
from pathlib import Path
import hashlib
from studio.files import read_json, digest, confined

SCHEDULERS = {
    "DDPMScheduler",
    "DDIMScheduler",
    "PNDMScheduler",
    "EulerDiscreteScheduler",
    "EulerAncestralDiscreteScheduler",
    "LMSDiscreteScheduler",
    "DPMSolverMultistepScheduler",
}


def inspect_diffusers(path: Path) -> dict:
    """Bound file counts/sizes and allow only explicitly supported classic SD component classes."""
    model = read_json(path / "model_index.json")
    if not isinstance(model, dict) or model.get("_class_name") != "StableDiffusionPipeline":
        raise ValueError(
            "Only classic single-encoder StableDiffusionPipeline directories are supported"
        )
    expected = {
        "unet": ["diffusers", "UNet2DConditionModel"],
        "vae": ["diffusers", "AutoencoderKL"],
        "text_encoder": ["transformers", "CLIPTextModel"],
        "tokenizer": ["transformers", "CLIPTokenizer"],
    }
    for name, contract in expected.items():
        if model.get(name) != contract or not (path / name).is_dir():
            raise ValueError("Unexpected pretrained component")
    scheduler = model.get("scheduler", [])
    if (
        not isinstance(scheduler, list)
        or len(scheduler) != 2
        or scheduler[0] != "diffusers"
        or scheduler[1] not in SCHEDULERS
    ):
        raise ValueError("Unsupported scheduler class")
    for key, allowed in {
        "safety_checker": ([None, None], ["stable_diffusion", "StableDiffusionSafetyChecker"]),
        "feature_extractor": ([None, None], ["transformers", "CLIPImageProcessor"]),
        "image_encoder": ([None, None],),
    }.items():
        if model.get(key, [None, None]) not in allowed:
            raise ValueError("Unsupported optional component class")
    for key, value in model.items():
        if (
            not key.startswith("_")
            and isinstance(value, list)
            and key not in expected
            and key not in {"scheduler", "safety_checker", "feature_extractor", "image_encoder"}
        ):
            raise ValueError("Unknown pretrained component")
    count, size = 0, 0
    for file in path.rglob("*"):
        count += 1
        if (
            count > 10000
            or file.is_symlink()
            or file.suffix.casefold() in {".py", ".pkl", ".pickle", ".bin", ".pt", ".pth", ".ckpt"}
        ):
            raise ValueError("Unsafe/oversized model tree, executable/pickle file or symbolic link")
        if file.is_file():
            size += file.stat().st_size
            if size > 20 * 1024**3:
                raise ValueError("Model files exceed 20 GiB budget")
            if file.name.endswith(".index.json"):
                index = read_json(file, 4 * 1024 * 1024)
                mapping = index.get("weight_map")
                if not isinstance(mapping, dict) or not mapping or len(mapping) > 100000:
                    raise ValueError("Invalid bounded model shard index")
                if not all(isinstance(shard, str) for shard in mapping.values()):
                    raise ValueError("Unsafe model shard path")
                for shard in set(mapping.values()):
                    if (
                        not isinstance(shard, str)
                        or Path(shard).is_absolute()
                        or "\\" in shard
                        or ":" in shard
                        or ".." in Path(shard).parts
                    ):
                        raise ValueError("Unsafe model shard path")
                    target = confined(file.parent, shard)
                    if (
                        target.suffix != ".safetensors"
                        or not target.is_file()
                        or target.is_symlink()
                    ):
                        raise ValueError("Shard must be a confined regular safe-tensor file")
        elif not file.is_dir():
            raise ValueError("Model tree contains a non-regular file")
    for component in ("unet", "vae", "text_encoder"):
        if not list((path / component).glob("*.safetensors")):
            raise ValueError("Pretrained components need safe tensor weights")
    return model


def model_fingerprint(path: Path) -> str:
    """Bind adapters to all inspected base files, not merely a reusable model-index class declaration."""
    inspect_diffusers(path)
    signature = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_file():
            signature.update(file.relative_to(path).as_posix().encode())
            signature.update(digest(file).encode())
    return signature.hexdigest()
