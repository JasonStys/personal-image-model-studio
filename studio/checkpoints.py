"""Versioned native safetensors checkpoints; verify bounded manifests/hashes before allocation."""

# Index: declarations module.verify@L8, module.save@L40, module.load@L74, module.restore_optimizer@L95; variables path@L8, manifest@L10, vocab@L19, word@L23, word@L28, artifacts@L30, expected@L33, name@L33, file@L34, ema@L40, generator@L40, manifest@L40, model@L40, optimizer@L40, path@L40, tensors@L46, name@L48, value@L48, name@L51, value@L51, state@L55, optimizer_tensors@L56, fields@L58, index@L58, name@L59, value@L59, manifest@L63, name@L67, device@L74, path@L74, resume@L74, manifest@L80, model@L81, tensors@L82, prefix@L83, state@L84, name@L85, value@L85, value@L90, device@L95, groups@L95, optimizer@L95, path@L95, tensors@L99, state@L100, key@L101, value@L101, index@L102, name@L102. Purposes/parameters: docs/code-map.json.
from pathlib import Path
from studio.files import read_json, digest, atomic_json, confined


def verify(path: Path) -> dict:
    """Reject unknown architecture, oversized/tampered weights and invalid vocabularies."""
    manifest = read_json(path / "model.json")
    if manifest.get("format") != "image-studio-native-v1":
        raise ValueError("Not a supported native checkpoint")
    if manifest.get("resolution") not in (32, 64, 128) or manifest.get("channels") not in (
        16,
        32,
        64,
    ):
        raise ValueError("Unsupported native model dimensions")
    vocab = manifest.get("vocab", [])
    if (
        not isinstance(vocab, list)
        or not 2 <= len(vocab) <= 4096
        or any(not isinstance(word, str) or len(word) > 100 for word in vocab)
        or len(set(vocab)) != len(vocab)
        or vocab[:2] != ["<pad>", "<unknown>"]
    ):
        raise ValueError("Invalid checkpoint vocabulary")
    if any(not isinstance(word, str) or len(word) > 100 for word in vocab):
        raise ValueError("Invalid vocabulary token")
    artifacts = manifest.get("artifacts", {})
    if set(artifacts) != {"weights.safetensors", "optimizer.safetensors"}:
        raise ValueError("Invalid checkpoint artifact list")
    for name, expected in artifacts.items():
        file = confined(path, name)
        if file.stat().st_size > 100 * 1024 * 1024 or digest(file) != expected:
            raise ValueError("Checkpoint integrity failure")
    return manifest


def save(path: Path, model, ema: dict, optimizer, generator, manifest: dict) -> dict:
    """Write model/EMA/RNG and AdamW tensors without pickle, then publish the manifest last."""
    import torch
    from safetensors.torch import save_file

    path.mkdir(parents=True, exist_ok=False)
    tensors = {
        "model." + name: value.detach().cpu().contiguous().clone()
        for name, value in model.state_dict().items()
    }
    tensors.update(
        {"ema." + name: value.detach().cpu().contiguous().clone() for name, value in ema.items()}
    )
    tensors["rng"] = generator.get_state().cpu().clone()
    save_file(tensors, str(path / "weights.safetensors"))
    state = optimizer.state_dict()
    optimizer_tensors = {
        f"{index}.{name}": value.detach().cpu().contiguous().clone()
        for index, fields in state["state"].items()
        for name, value in fields.items()
        if isinstance(value, torch.Tensor)
    }
    save_file(optimizer_tensors, str(path / "optimizer.safetensors"))
    manifest = {
        **manifest,
        "optimizer_groups": state["param_groups"],
        "artifacts": {
            name: digest(path / name) for name in ("weights.safetensors", "optimizer.safetensors")
        },
    }
    atomic_json(path / "model.json", manifest)
    return verify(path)


def load(path: Path, device: str, resume: bool = False):
    """Build the exact fixed architecture and load safe tensors after integrity verification."""
    import torch
    from safetensors.torch import load_file
    from studio.model import NativeDenoiser

    manifest = verify(path)
    model = NativeDenoiser(len(manifest["vocab"]), manifest["channels"]).to(device)
    tensors = load_file(str(path / "weights.safetensors"), device=device)
    prefix = "model." if resume else "ema."
    state = {
        name[len(prefix) :]: value for name, value in tensors.items() if name.startswith(prefix)
    }
    if set(state) != set(model.state_dict()):
        raise ValueError("Checkpoint tensor names do not match architecture")
    model.load_state_dict(state, strict=True)
    if any(not torch.isfinite(value).all().item() for value in model.parameters()):
        raise ValueError("Checkpoint has non-finite weights")
    return model, manifest, tensors


def restore_optimizer(optimizer, path: Path, groups: list, device: str) -> None:
    """Restore fixed AdamW tensor slots using safe JSON/tensor data, not Python objects."""
    from safetensors.torch import load_file

    tensors = load_file(str(path / "optimizer.safetensors"), device=device)
    state = {}
    for key, value in tensors.items():
        index, name = key.split(".", 1)
        if name not in {"step", "exp_avg", "exp_avg_sq"}:
            raise ValueError("Unknown optimizer state field")
        state.setdefault(int(index), {})[name] = value
    optimizer.load_state_dict({"state": state, "param_groups": groups})
