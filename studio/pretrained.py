"""Local classic Stable Diffusion generation and real LoRA updates; unsupported families fail explicitly."""

# Index: declarations module.inspect@L23, module.pipeline@L28, module.embeddings@L37, module.generate@L60, generate.callback@L126, module.train_lora@L151; variables path@L23, device@L28, path@L28, pipe@L37, text@L37, tokenizer@L39, limit@L40, ids@L41, weights@L42, span@L43, weight@L43, tokens@L44, warning@L47, ids@L50, weights@L51, device@L54, hidden@L55, config@L61, model@L62, output@L63, source_path@L64, mask_path@L65, progress@L66, value@L66, cancel@L67, adapter_path@L68, settings@L71, compiled@L72, device@L77, pipe@L78, adapter@L80, positive@L89, warnings@L89, negative@L90, notes@L90, mask@L92, source@L92, parameters@L93, original@L103, raw_mask@L105, mask@L106, source@L106, mask@L110, source@L110, pipe@L114, pipe@L117, active@L126, step@L126, timestep@L126, values@L126, started@L133, result@L134, image@L137, image@L139, config@L152, roots@L153, base@L154, output@L155, progress@L156, value@L156, cancel@L157, settings@L164, device@L167, fingerprint@L170, heldout@L170, records@L170, pipe@L171, component@L172, optimizer@L177, p@L178, noise_scheduler@L180, rng@L181, metrics@L182, started@L183, status@L184, step@L185, status@L187, indices@L189, captions@L194, pixels@L194, index@L195, caption@L196, path@L196, image@L197, resized@L198, latents@L203, tokens@L209, text@L216, noise@L217, timesteps@L218, noisy@L225, target@L226, loss@L234, p@L239, item@L243, completed@L250, state@L254, report@L258. Purposes/parameters: docs/code-map.json.
import time
from pathlib import Path
import numpy as np
import torch
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    DDPMScheduler,
)
from PIL import Image, ImageOps
from studio.contracts import Generation, Training
from studio.files import read_json, atomic_json, digest, normalized_image
from studio.native import edit_canvas
from studio.prompts import compile_prompt, weighted
from studio.training import device_for, prepare_dataset
from studio.formats import inspect_diffusers, model_fingerprint


def inspect(path: Path) -> dict:
    """Accept fixed classic SD components, safetensors only and no custom executable pipeline files."""
    return inspect_diffusers(path)


def pipeline(path: Path, device: str):
    """Load fixed local classes with offline safe tensors; preserve supplied model safety checker."""
    inspect(path)
    return StableDiffusionPipeline.from_pretrained(
        str(path), local_files_only=True, use_safetensors=True, torch_dtype=torch.float32
    ).to(device)


@torch.no_grad()
def embeddings(pipe, text: str):
    """Multiply per-token hidden states by explicit span weights; warn instead of hiding truncation."""
    tokenizer = pipe.tokenizer
    limit = min(77, tokenizer.model_max_length)
    ids = [tokenizer.bos_token_id]
    weights = [1.0]
    for span, weight in weighted(text):
        tokens = tokenizer(span, add_special_tokens=False).input_ids
        ids.extend(tokens)
        weights.extend([weight] * len(tokens))
    warning = (
        [f"CLIP prompt truncated to {limit - 2} content tokens"] if len(ids) > limit - 1 else []
    )
    ids = ids[: limit - 1] + [tokenizer.eos_token_id]
    weights = weights[: limit - 1] + [1.0]
    ids.extend([tokenizer.pad_token_id] * (limit - len(ids)))
    weights.extend([1.0] * (limit - len(weights)))
    device = pipe._execution_device
    hidden = pipe.text_encoder(torch.tensor([ids], device=device))[0]
    return hidden * torch.tensor(weights, device=device)[None, :, None], warning


@torch.inference_mode()
def generate(
    config: dict,
    model: Path,
    output: Path,
    source_path: Path | None = None,
    mask_path: Path | None = None,
    progress=lambda value: None,
    cancel=lambda: False,
    adapter_path: Path | None = None,
) -> dict:
    """Execute text/img2img/inpaint/outpaint on a local compatible model with exact preserved-pixel overlay."""
    settings = Generation.model_validate(config)
    compiled = compile_prompt(settings.prompt.model_dump())
    if compiled["regions"]:
        raise ValueError(
            "Spatial subject boxes are native-only; classic SD does not implement regional attention"
        )
    device = device_for("auto")
    pipe = pipeline(model, device)
    if adapter_path:
        adapter = read_json(adapter_path / "adapter.json")
        if (
            digest(adapter_path / "pytorch_lora_weights.safetensors") != adapter["weights_sha256"]
            or model_fingerprint(model) != adapter["base_model_fingerprint"]
        ):
            raise ValueError("LoRA adapter or base identity changed")
        pipe.load_lora_weights(
            str(adapter_path), weight_name="pytorch_lora_weights.safetensors", local_files_only=True
        )
    positive, warnings = embeddings(pipe, compiled["positive"])
    negative, notes = embeddings(pipe, compiled["negative"])
    warnings.extend(notes)
    source, mask = None, None
    parameters = {
        "prompt_embeds": positive,
        "negative_prompt_embeds": negative,
        "num_inference_steps": settings.steps,
        "guidance_scale": settings.guidance,
        "generator": torch.Generator(device=device).manual_seed(settings.seed),
    }
    if settings.mode == "text":
        parameters.update(width=settings.width, height=settings.height)
    else:
        with normalized_image(source_path) as original:
            if mask_path:
                with normalized_image(mask_path) as raw_mask:
                    source, mask = edit_canvas(
                        original, raw_mask, settings.width, settings.height, settings.mode
                    )
            else:
                source, mask = edit_canvas(
                    original, None, settings.width, settings.height, settings.mode
                )
        if settings.mode == "edit":
            pipe = StableDiffusionImg2ImgPipeline(**pipe.components)
            parameters.update(image=source, strength=settings.strength)
        else:
            pipe = StableDiffusionInpaintPipeline(**pipe.components)
            parameters.update(
                image=source,
                mask_image=mask,
                width=settings.width,
                height=settings.height,
                strength=1.0,
            )

    def callback(active, step, timestep, values):
        """Check cancellation without executing user code; retain no intermediate tensors in metadata."""
        if cancel():
            raise InterruptedError("Generation cancelled")
        progress({"step": step + 1, "total": settings.steps})
        return values

    started = time.perf_counter()
    result = pipe(**parameters, callback_on_step_end=callback)
    if getattr(result, "nsfw_content_detected", None) and any(result.nsfw_content_detected):
        raise ValueError("The supplied model's safety checker flagged output; no image published")
    image = result.images[0]
    if source is not None and settings.mode != "edit":
        image = Image.composite(image, source, mask)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return {
        "seconds": time.perf_counter() - started,
        "warnings": warnings,
        "width": settings.width,
        "height": settings.height,
        "review": "Structural checks only; correctness depends on supplied model. No semantic judge configured.",
    }


def train_lora(
    config: dict,
    roots: list[Path],
    base: Path,
    output: Path,
    progress=lambda value: None,
    cancel=lambda: False,
) -> dict:
    """Train attention-only LoRA parameters on authorized image-caption pairs and save safe adapter weights."""
    from peft import LoraConfig
    from peft.utils import get_peft_model_state_dict
    from diffusers.utils import convert_state_dict_to_diffusers

    settings = Training.model_validate(config)
    if settings.mode != "lora":
        raise ValueError("LoRA trainer requires adapter mode")
    device = device_for(settings.device)
    torch.manual_seed(settings.seed)
    torch.set_num_threads(2)
    records, heldout, fingerprint = prepare_dataset(roots)
    pipe = pipeline(base, device)
    for component in (pipe.vae, pipe.text_encoder, pipe.unet):
        component.requires_grad_(False)
    pipe.unet.add_adapter(
        LoraConfig(r=4, lora_alpha=4, target_modules=["to_q", "to_k", "to_v", "to_out.0"])
    )
    optimizer = torch.optim.AdamW(
        [p for p in pipe.unet.parameters() if p.requires_grad], lr=settings.learning_rate
    )
    noise_scheduler = DDPMScheduler.from_config(pipe.scheduler.config)
    rng = torch.Generator(device=device).manual_seed(settings.seed)
    metrics = []
    started = time.perf_counter()
    status = "completed"
    for step in range(1, settings.steps + 1):
        if cancel() or time.perf_counter() - started > settings.max_seconds:
            status = "cancelled"
            break
        indices = (
            torch.randint(len(records), (settings.batch_size,), generator=rng, device=device)
            .cpu()
            .tolist()
        )
        pixels, captions = [], []
        for index in indices:
            path, caption = records[index]
            with normalized_image(path) as image:
                resized = ImageOps.fit(image, (settings.resolution, settings.resolution))
                pixels.append(np.asarray(resized, dtype=np.float32).transpose(2, 0, 1) / 127.5 - 1)
                resized.close()
            captions.append(caption)
        with torch.no_grad():
            latents = (
                pipe.vae.encode(torch.tensor(np.stack(pixels), device=device)).latent_dist.sample(
                    generator=rng
                )
                * pipe.vae.config.scaling_factor
            )
            tokens = pipe.tokenizer(
                captions,
                padding="max_length",
                truncation=True,
                max_length=pipe.tokenizer.model_max_length,
                return_tensors="pt",
            ).input_ids.to(device)
            text = pipe.text_encoder(tokens)[0]
        noise = torch.randn(latents.shape, generator=rng, device=device)
        timesteps = torch.randint(
            0,
            noise_scheduler.config.num_train_timesteps,
            (len(latents),),
            generator=rng,
            device=device,
        )
        noisy = noise_scheduler.add_noise(latents, noise, timesteps)
        target = (
            noise
            if noise_scheduler.config.prediction_type == "epsilon"
            else noise_scheduler.get_velocity(latents, noise, timesteps)
        )
        if noise_scheduler.config.prediction_type not in {"epsilon", "v_prediction"}:
            raise ValueError("Unsupported base-model training target")
        optimizer.zero_grad(set_to_none=True)
        loss = torch.nn.functional.mse_loss(pipe.unet(noisy, timesteps, text).sample, target)
        if not torch.isfinite(loss):
            raise ValueError("Non-finite LoRA loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            [p for p in pipe.unet.parameters() if p.requires_grad], 1.0, error_if_nonfinite=True
        )
        optimizer.step()
        if step == 1 or step % 25 == 0 or step == settings.steps:
            item = {
                "step": step,
                "loss": float(loss.detach().cpu()),
                "seconds": time.perf_counter() - started,
            }
            metrics.append(item)
            progress(item)
    completed = step if status == "completed" else step - 1
    if not completed:
        raise InterruptedError("No LoRA optimizer update completed")
    output.mkdir(parents=True, exist_ok=False)
    state = convert_state_dict_to_diffusers(get_peft_model_state_dict(pipe.unet))
    StableDiffusionPipeline.save_lora_weights(
        str(output), unet_lora_layers=state, safe_serialization=True
    )
    report = {
        "format": "image-studio-lora-v1",
        "name": settings.name,
        "status": status,
        "steps": completed,
        "metrics": metrics,
        "dataset_fingerprint": fingerprint,
        "base_model_index_sha256": digest(base / "model_index.json"),
        "base_model_fingerprint": model_fingerprint(base),
        "weights_sha256": digest(output / "pytorch_lora_weights.safetensors"),
        "heldout_images": len(heldout),
        "limits": "Training loss only; this adapter does not include a base model or optimizer-resume state",
    }
    atomic_json(output / "adapter.json", report)
    return report
