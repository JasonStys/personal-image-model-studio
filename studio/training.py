"""Real from-scratch diffusion training with held-out denoising metrics and safe optimizer resume."""

# Index: declarations module.device_for@L19, module.scheduler@L26, module.prepare_dataset@L33, module.batch@L56, module.heldout_loss@L76, module.train@L88; variables requested@L19, roots@L33, seen@L35, train@L35, validation@L35, signatures@L36, root@L37, manifest@L38, split@L40, target@L40, record@L41, path@L43, fingerprint@L52, device@L56, indices@L56, records@L56, resolution@L56, vocab@L56, ids@L58, images@L58, weights@L58, index@L59, caption@L60, path@L60, image@L61, fitted@L62, _@L65, token@L65, weight@L65, device@L76, model@L76, records@L76, resolution@L76, vocab@L76, ids@L78, images@L78, weights@L78, rng@L81, noise@L82, timesteps@L83, prediction@L84, config@L89, roots@L90, output@L91, resume_path@L92, progress@L93, value@L93, cancel@L94, settings@L97, device@L100, rng@L105, fingerprint@L106, train_records@L106, validation_records@L106, _@L107, caption@L107, vocab@L107, previous_steps@L108, model@L110, previous@L110, tensors@L110, previous_steps@L118, ema@L120, name@L121, value@L121, model@L124, ema@L125, name@L125, value@L125, optimizer@L126, group@L129, schedule@L131, initial@L132, started@L133, metrics@L134, status@L135, step@L138, status@L140, indices@L142, ids@L147, images@L147, weights@L147, dropped@L149, noise@L151, timesteps@L152, predicted@L154, loss@L155, name@L162, value@L162, metric@L165, completed@L172, final_raw@L176, name@L177, raw@L177, value@L177, final_ema@L179, seconds@L181, manifest@L182, p@L205. Purposes/parameters: docs/code-map.json.
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import torch
from diffusers import DDPMScheduler
from PIL import ImageOps
from studio import checkpoints
from studio.contracts import Training
from studio.datasets import eligible
from studio.files import confined, normalized_image, read_json, digest
from studio.model import NativeDenoiser, encode, vocabulary


def device_for(requested: str) -> str:
    """Select CUDA only when present; explicit unavailable CUDA fails instead of hiding fallback."""
    if requested == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA requested but unavailable")
    return "cuda" if requested != "cpu" and torch.cuda.is_available() else "cpu"


def scheduler():
    """Use the same cosine DDPM training schedule for all native runs and inference."""
    return DDPMScheduler(
        num_train_timesteps=100, beta_schedule="squaredcos_cap_v2", prediction_type="epsilon"
    )


def prepare_dataset(roots: list[Path]) -> tuple[list, list, str]:
    """Combine manifests, exclude AI-origin records, and prevent cross-dataset duplicate leakage."""
    train, validation, seen = [], [], set()
    signatures = []
    for root in roots:
        manifest = read_json(root / "dataset.json", 16 * 1024 * 1024)
        signatures.append(manifest["fingerprint"])
        for split, target in (("train", train), ("validation", validation)):
            for record in eligible(manifest, split):
                if record["hash"] not in seen:
                    path = confined(root, record["file"])
                    if digest(path) != record["file_sha256"]:
                        raise ValueError(
                            "Dataset pixels changed after import; reimport before training"
                        )
                    target.append((path, record["caption"]))
                    seen.add(record["hash"])
    if len(train) < 8 or len(validation) < 2:
        raise ValueError("Need at least 8 unique captioned training and 2 held-out images")
    fingerprint = hashlib.sha256(json.dumps(sorted(signatures)).encode()).hexdigest()
    return train, validation, fingerprint


def batch(records: list, indices: list[int], vocab: list[str], resolution: int, device: str):
    """Load only one batch into tensor memory; images close promptly and captions stay bounded."""
    images, ids, weights = [], [], []
    for index in indices:
        path, caption = records[index]
        with normalized_image(path) as image:
            fitted = ImageOps.fit(image, (resolution, resolution))
            images.append(np.array(fitted, dtype=np.float32).transpose(2, 0, 1) / 127.5 - 1)
            fitted.close()
        token, weight, _ = encode(caption, vocab)
        ids.append(token)
        weights.append(weight)
    return (
        torch.tensor(np.stack(images), device=device),
        torch.tensor(ids, device=device),
        torch.tensor(weights, device=device),
    )


@torch.no_grad()
def heldout_loss(model, records, vocab, resolution, device):
    """Fixed held-out examples/noise/timesteps allow before/after comparisons without training leakage."""
    images, ids, weights = batch(
        records, list(range(min(16, len(records)))), vocab, resolution, device
    )
    rng = torch.Generator(device=device).manual_seed(2026)
    noise = torch.randn(images.shape, generator=rng, device=device)
    timesteps = torch.randint(10, 90, (len(images),), generator=rng, device=device)
    prediction = model(scheduler().add_noise(images, noise, timesteps), timesteps, ids, weights)
    return float(torch.nn.functional.mse_loss(prediction, noise).cpu())


def train(
    config: dict,
    roots: list[Path],
    output: Path,
    resume_path: Path | None = None,
    progress=lambda value: None,
    cancel=lambda: False,
) -> dict:
    """Optimize real weights, checkpoint bounded work, and report metrics without promising image quality."""
    settings = Training.model_validate(config)
    if settings.mode != "native":
        raise ValueError("Native trainer requires native mode")
    device = device_for(settings.device)
    torch.set_num_threads(2)
    torch.manual_seed(settings.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    rng = torch.Generator(device=device).manual_seed(settings.seed)
    train_records, validation_records, fingerprint = prepare_dataset(roots)
    vocab = vocabulary([caption for _, caption in train_records])
    previous_steps = 0
    if resume_path:
        model, previous, tensors = checkpoints.load(resume_path, device, True)
        if (
            previous["dataset_fingerprint"] != fingerprint
            or previous["vocab"] != vocab
            or previous["resolution"] != settings.resolution
            or previous["channels"] != 32
        ):
            raise ValueError("Resume dataset/vocabulary/resolution differs from checkpoint")
        previous_steps = previous["trained_steps"]
        rng.set_state(tensors["rng"].cpu())
        ema = {
            name[4:]: value.clone() for name, value in tensors.items() if name.startswith("ema.")
        }
    else:
        model = NativeDenoiser(len(vocab)).to(device)
        ema = {name: value.detach().clone() for name, value in model.state_dict().items()}
    optimizer = torch.optim.AdamW(model.parameters(), lr=settings.learning_rate)
    if resume_path:
        checkpoints.restore_optimizer(optimizer, resume_path, previous["optimizer_groups"], device)
        for group in optimizer.param_groups:
            group["lr"] = settings.learning_rate
    schedule = scheduler()
    initial = heldout_loss(model, validation_records, vocab, settings.resolution, device)
    started = time.perf_counter()
    metrics = []
    status = "completed"
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for step in range(1, settings.steps + 1):
        if cancel() or time.perf_counter() - started > settings.max_seconds:
            status = "cancelled" if cancel() else "time_limit"
            break
        indices = (
            torch.randint(len(train_records), (settings.batch_size,), generator=rng, device=device)
            .cpu()
            .tolist()
        )
        images, ids, weights = batch(train_records, indices, vocab, settings.resolution, device)
        # Classifier-free conditioning dropout makes an empty/negative branch usable at inference.
        dropped = torch.rand((len(images),), generator=rng, device=device) < 0.1
        weights[dropped] = 0
        noise = torch.randn(images.shape, generator=rng, device=device)
        timesteps = torch.randint(0, 100, (len(images),), generator=rng, device=device)
        optimizer.zero_grad(set_to_none=True)
        predicted = model(schedule.add_noise(images, noise, timesteps), timesteps, ids, weights)
        loss = torch.nn.functional.mse_loss(predicted, noise)
        if not torch.isfinite(loss):
            raise ValueError("Non-finite training loss; checkpoint not published")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        with torch.no_grad():
            for name, value in model.state_dict().items():
                ema[name].lerp_(value, 0.01)
        if step == 1 or step % 25 == 0 or step == settings.steps:
            metric = {
                "step": previous_steps + step,
                "loss": float(loss.detach().cpu()),
                "seconds": time.perf_counter() - started,
            }
            metrics.append(metric)
            progress(metric)
    completed = step if status == "completed" else step - 1
    if completed == 0:
        raise ValueError("Training stopped before an optimizer update; no model published")
    model.eval()
    final_raw = heldout_loss(model, validation_records, vocab, settings.resolution, device)
    raw = {name: value.detach().clone() for name, value in model.state_dict().items()}
    model.load_state_dict(ema)
    final_ema = heldout_loss(model, validation_records, vocab, settings.resolution, device)
    model.load_state_dict(raw)
    seconds = time.perf_counter() - started
    manifest = {
        "format": "image-studio-native-v1",
        "name": settings.name,
        "channels": 32,
        "resolution": settings.resolution,
        "vocab": vocab,
        "dataset_fingerprint": fingerprint,
        "trained_steps": previous_steps + completed,
        "settings": settings.model_dump(),
        "status": status,
        "metrics": metrics,
        "validation": {
            "initial_noise_mse": initial,
            "final_noise_mse": final_raw,
            "ema_noise_mse": final_ema,
            "train_images": len(train_records),
            "heldout_images": len(validation_records),
            "seconds": seconds,
            "steps_per_second": completed / max(seconds, 1e-9),
            "device": device,
            "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated()
            if device == "cuda"
            else None,
            "parameter_count": sum(p.numel() for p in model.parameters()),
            "torch": torch.__version__,
        },
    }
    return checkpoints.save(output, model, ema, optimizer, rng, manifest)
