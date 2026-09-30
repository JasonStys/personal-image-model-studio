"""Actual learned native diffusion inference, numeric prompt weights and source-preserving masked edits."""

# Index: declarations module.edit_canvas@L18, module.generate@L40, generate.condition@L71; variables height@L18, mask@L18, mode@L18, source@L18, width@L18, canvas@L23, edit@L24, left@L25, top@L25, canvas@L29, config@L41, checkpoint@L42, output@L43, source_path@L44, mask_path@L45, progress@L46, value@L46, cancel@L47, device@L48, settings@L51, selected@L52, _@L54, manifest@L54, model@L54, compiled@L56, size@L57, work_width@L59, work_height@L62, rng@L65, noise@L66, schedule@L67, warnings@L69, text@L71, ids@L73, notes@L73, weights@L73, positive@L77, negative@L78, regions@L79, r@L80, mask@L82, source@L82, image@L83, timesteps@L84, original@L86, raw_mask@L88, mask@L89, source@L89, mask@L93, source@L93, tensor@L96, mask_tensor@L104, count@L112, timesteps@L113, image@L114, started@L115, index@L116, timestep@L116, neg@L119, pos@L120, prediction@L121, box@L122, local_negative@L122, local_positive@L122, bottom@L123, left@L123, right@L123, top@L123, xe@L124, xs@L124, ye@L128, ys@L128, local_neg@L132, local_pos@L133, image@L137, previous@L141, image@L146, pixels@L151, result@L152, result@L156. Purposes/parameters: docs/code-map.json.
import time
from pathlib import Path
import numpy as np
import torch
from diffusers import DDIMScheduler
from PIL import Image, ImageOps
from studio.checkpoints import load
from studio.contracts import Generation
from studio.files import normalized_image
from studio.model import encode
from studio.prompts import compile_prompt
from studio.training import device_for, scheduler


def edit_canvas(source: Image.Image, mask: Image.Image | None, width: int, height: int, mode: str):
    """White means generate. Expansion preserves the centered source pixel-for-pixel without rescaling."""
    if mode == "expand":
        if width < source.width or height < source.height:
            raise ValueError("Expansion canvas must not crop or shrink the original image")
        canvas = Image.new("RGB", (width, height), (255, 255, 255))
        edit = Image.new("L", (width, height), 255)
        left, top = (width - source.width) // 2, (height - source.height) // 2
        canvas.paste(source, (left, top))
        edit.paste(0, (left, top, left + source.width, top + source.height))
        return canvas, edit
    canvas = ImageOps.fit(source, (width, height))
    if mode == "inpaint":
        if mask is None or mask.size != source.size:
            raise ValueError("Mask must match the source image dimensions")
        return canvas, ImageOps.fit(
            mask.convert("L"), (width, height), method=Image.Resampling.NEAREST
        )
    return canvas, Image.new("L", (width, height), 255)


@torch.inference_mode()
def generate(
    config: dict,
    checkpoint: Path,
    output: Path,
    source_path: Path | None = None,
    mask_path: Path | None = None,
    progress=lambda value: None,
    cancel=lambda: False,
    device="auto",
) -> dict:
    """Sample trained noise predictions; enforce a source overlay after denoising to preserve black mask pixels."""
    settings = Generation.model_validate(config)
    selected = device_for(device)
    torch.set_num_threads(2)
    model, manifest, _ = load(checkpoint, selected)
    model.eval()
    compiled = compile_prompt(settings.prompt.model_dump())
    size = manifest["resolution"]
    # Native inference is capped to 4x the training area, not an untrained 1024px quality promise.
    work_width = max(
        16, round(settings.width * size / max(settings.width, settings.height) / 2) * 2
    )
    work_height = max(
        16, round(settings.height * size / max(settings.width, settings.height) / 2) * 2
    )
    rng = torch.Generator(device=selected).manual_seed(settings.seed)
    noise = torch.randn((1, 3, work_height, work_width), generator=rng, device=selected)
    schedule = DDIMScheduler.from_config(scheduler().config, timestep_spacing="trailing")
    schedule.set_timesteps(settings.steps, device=selected)
    warnings = []

    def condition(text):
        """Encode weighted known tokens and return visible vocabulary/truncation warnings."""
        ids, weights, notes = encode(text, manifest["vocab"])
        warnings.extend(notes)
        return torch.tensor([ids], device=selected), torch.tensor([weights], device=selected)

    positive = condition(compiled["positive"])
    negative = condition(compiled["negative"])
    regions = [
        (condition(r["positive"]), condition(r["negative"]), r["box"]) for r in compiled["regions"]
    ]
    source, mask = None, None
    image = noise
    timesteps = schedule.timesteps
    if settings.mode != "text":
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
        tensor = torch.tensor(
            np.array(source.resize((work_width, work_height)), dtype=np.float32).transpose(2, 0, 1)[
                None
            ]
            / 127.5
            - 1,
            device=selected,
        )
        mask_tensor = torch.tensor(
            np.array(
                mask.resize((work_width, work_height), Image.Resampling.NEAREST), dtype=np.float32
            )[None, None]
            / 255,
            device=selected,
        )
        if settings.mode == "edit":
            count = max(1, int(len(timesteps) * settings.strength))
            timesteps = timesteps[-count:]
        image = schedule.add_noise(tensor, noise, timesteps[:1])
    started = time.perf_counter()
    for index, timestep in enumerate(timesteps):
        if cancel():
            raise InterruptedError("Generation cancelled")
        neg = model(image, timestep, *negative)
        pos = model(image, timestep, *positive)
        prediction = neg + settings.guidance * (pos - neg)
        for local_positive, local_negative, box in regions:
            left, top, right, bottom = box
            xs, xe = (
                int(left * work_width),
                max(int(right * work_width), int(left * work_width) + 1),
            )
            ys, ye = (
                int(top * work_height),
                max(int(bottom * work_height), int(top * work_height) + 1),
            )
            local_neg = model(image, timestep, *local_negative)
            local_pos = model(image, timestep, *local_positive)
            prediction[:, :, ys:ye, xs:xe] = (
                local_neg + settings.guidance * (local_pos - local_neg)
            )[:, :, ys:ye, xs:xe]
        image = schedule.step(
            prediction, timestep, image, eta=0, use_clipped_model_output=True
        ).prev_sample
        if source is not None:
            previous = (
                schedule.add_noise(tensor, noise, timesteps[index + 1 : index + 2])
                if index + 1 < len(timesteps)
                else tensor
            )
            image = image * mask_tensor + previous * (1 - mask_tensor)
        if index % 5 == 0:
            progress({"step": index + 1, "total": len(timesteps)})
    if not torch.isfinite(image).all():
        raise ValueError("Model produced non-finite output")
    pixels = ((image[0].clamp(-1, 1) + 1) * 127.5).round().byte().cpu().numpy().transpose(1, 2, 0)
    result = Image.fromarray(pixels).resize(
        (settings.width, settings.height), Image.Resampling.LANCZOS
    )
    if source is not None:
        result = Image.composite(result, source, mask)
        source.close()
        mask.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output)
    result.close()
    return {
        "seconds": time.perf_counter() - started,
        "warnings": sorted(set(warnings)),
        "learned_resolution": size,
        "width": settings.width,
        "height": settings.height,
        "trained_steps": manifest["trained_steps"],
        "review": "Dimensions/finite pixels verified; no semantic correctness or visual safety judgement is claimed",
    }
