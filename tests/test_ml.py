"""Real CPU diffusion optimization, safe reload/resume/editing and randomly initialized LoRA integration."""

# Index: declarations module.dataset@L20, module.settings@L27, module.learned@L43, module.generation@L50, module.test_real_learning_and_checkpoint@L64, module.test_resume_matches_continuous_cpu@L80, module.test_seed_weight_and_regional_generation@L95, module.test_black_mask_and_expansion_exactly_preserve@L122, module.test_tampered_pixels_and_checkpoint_manifest@L161, module.test_training_cancellation_publishes_only_updated_checkpoint@L179, module.random_sd@L197, module.test_real_lora_adapter_reload_and_generation@L269, module.test_pretrained_shard_index_cannot_escape_or_crash@L306; variables pytestmark@L16, tmp_path_factory@L20, root@L22, steps@L27, dataset@L43, tmp_path_factory@L43, root@L45, overrides@L50, learned@L64, manifest@L66, _@L71, model@L71, tensors@L71, value@L72, name@L75, value@L75, dataset@L80, learned@L80, tmp_path@L80, first@L82, second@L83, result@L85, full@L87, split@L87, key@L92, learned@L95, tmp_path@L95, config@L97, name@L97, report@L111, learned@L122, tmp_path@L122, source@L124, mask@L125, after@L136, before@L136, after@L145, before@L145, before@L154, learned@L161, tmp_path@L161, root@L163, manifest@L165, image@L166, record@L166, copied@L170, metadata@L172, dataset@L179, tmp_path@L179, updates@L181, result@L182, root@L197, visible@L207, byte@L208, missing@L208, byte@L209, characters@L209, index@L210, vocab@L212, character@L213, special@L216, tokenizer@L218, text@L219, unet@L232, vae@L244, pipe@L255, dataset@L269, tmp_path@L269, base@L276, config@L278, adapter@L285, report@L286, tensors@L287, key@L290, value@L290, result@L294, image@L296, index@L298, shard@L306, tmp_path@L306, base@L310. Purposes/parameters: docs/code-map.json.
from pathlib import Path
import pytest

import torch
from PIL import Image
from safetensors.torch import load_file
from studio import checkpoints
from studio.datasets import synthetic_dataset
from studio.files import atomic_json, read_json, digest
from studio.native import generate, edit_canvas
from studio.training import train, prepare_dataset

pytestmark = pytest.mark.ml


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    """Prepare owned procedural images with disjoint deduplicated train/held-out sets."""
    root = tmp_path_factory.mktemp("ml") / "dataset"
    synthetic_dataset(root, count=96)
    return root


def settings(steps=20):
    """Small real optimization budget for CI; not a promise of visual quality."""
    return {
        "name": "CPU regression native",
        "dataset_ids": ["fixture"],
        "device": "cpu",
        "steps": steps,
        "batch_size": 4,
        "resolution": 32,
        "learning_rate": 0.001,
        "seed": 1337,
        "max_seconds": 120,
    }


@pytest.fixture(scope="module")
def learned(dataset, tmp_path_factory):
    """Train one fresh native model instead of mocking learned inference."""
    root = tmp_path_factory.mktemp("native") / "model"
    train(settings(), [dataset], root)
    return root


def generation(**overrides):
    """Use bounded deterministic generation settings for CPU artifact assertions."""
    return {
        "model_id": "fixture",
        "prompt": {"description": "red circle on white background"},
        "width": 32,
        "height": 32,
        "steps": 4,
        "guidance": 2,
        "seed": 2026,
        **overrides,
    }


def test_real_learning_and_checkpoint(learned):
    """Assert optimizer updates, finite held-out measurements and safe initialized architecture reload."""
    manifest = checkpoints.verify(learned)
    assert manifest["trained_steps"] == 20
    assert manifest["validation"]["final_noise_mse"] < manifest["validation"]["initial_noise_mse"]
    assert manifest["validation"]["train_images"] >= 8
    assert manifest["validation"]["heldout_images"] >= 2
    model, _, tensors = checkpoints.load(learned, "cpu")
    assert all(torch.isfinite(value).all() for value in model.parameters())
    assert any(
        not torch.equal(value, tensors["ema." + name[6:]])
        for name, value in tensors.items()
        if name.startswith("model.")
    )


def test_resume_matches_continuous_cpu(dataset, learned, tmp_path):
    """Real AdamW+RNG+EMA restore yields the same raw state as uninterrupted fixed-stack CPU training."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    train(settings(10), [dataset], first)
    result = train(settings(10), [dataset], second, resume_path=first)
    assert result["trained_steps"] == 20
    full, split = (
        load_file(str(learned / "weights.safetensors")),
        load_file(str(second / "weights.safetensors")),
    )
    assert full.keys() == split.keys()
    assert all(torch.equal(full[key], split[key]) for key in full)


def test_seed_weight_and_regional_generation(learned, tmp_path):
    """A real model produces repeatable seed output; numeric text weights affect tensors/artifacts."""
    for name, config in [
        ("one", generation()),
        ("two", generation()),
        ("weighted", generation(prompt={"description": "(red:1.8) circle on white background"})),
        (
            "region",
            generation(
                prompt={
                    "tags": "white background",
                    "subjects": [{"description": "red circle", "region": [0, 0, 0.5, 1]}],
                }
            ),
        ),
    ]:
        report = generate(config, learned, tmp_path / f"{name}.png", device="cpu")
        assert report["learned_resolution"] == 32
    assert digest(tmp_path / "one.png") == digest(tmp_path / "two.png")
    assert digest(tmp_path / "weighted.png") != digest(tmp_path / "one.png")
    with pytest.raises(InterruptedError):
        generate(
            generation(), learned, tmp_path / "cancelled.png", device="cpu", cancel=lambda: True
        )
    assert not (tmp_path / "cancelled.png").exists()


def test_black_mask_and_expansion_exactly_preserve(learned, tmp_path):
    """Final overlays preserve known source pixels bit-for-bit, not merely similar latent reconstructions."""
    source = tmp_path / "source.png"
    mask = tmp_path / "mask.png"
    Image.new("RGB", (32, 32), (31, 57, 93)).save(source)
    Image.new("L", (32, 32), 0).save(mask)
    generate(
        generation(mode="inpaint", image_id="source", mask_id="mask"),
        learned,
        tmp_path / "inpaint.png",
        source,
        mask,
        device="cpu",
    )
    with Image.open(source) as before, Image.open(tmp_path / "inpaint.png") as after:
        assert before.tobytes() == after.tobytes()
    generate(
        generation(mode="expand", image_id="source", width=64, height=32),
        learned,
        tmp_path / "expanded.png",
        source,
        device="cpu",
    )
    with Image.open(tmp_path / "expanded.png") as after, Image.open(source) as before:
        assert after.crop((16, 0, 48, 32)).tobytes() == before.tobytes()
    generate(
        generation(mode="edit", image_id="source", strength=0.5),
        learned,
        tmp_path / "edited.png",
        source,
        device="cpu",
    )
    with Image.open(source) as before:
        with pytest.raises(ValueError):
            edit_canvas(before, None, 16, 32, "expand")
        with pytest.raises(ValueError):
            edit_canvas(before, Image.new("L", (8, 8)), 32, 32, "inpaint")


def test_tampered_pixels_and_checkpoint_manifest(learned, tmp_path):
    """Mutation after import cannot silently train/resume with stale provenance."""
    root = tmp_path / "data"
    synthetic_dataset(root, count=48)
    manifest = read_json(root / "dataset.json")
    image = next(record for record in manifest["records"] if record["caption"])
    (root / image["file"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="pixels changed"):
        prepare_dataset([root])
    copied = tmp_path / "bad"
    copied.mkdir()
    metadata = checkpoints.verify(learned)
    metadata["vocab"] = ["<pad>", {}]
    atomic_json(copied / "model.json", metadata)
    with pytest.raises(ValueError, match="vocabulary"):
        checkpoints.verify(copied)


def test_training_cancellation_publishes_only_updated_checkpoint(dataset, tmp_path):
    """Cancellation after a genuine optimizer update leaves a recoverable safe checkpoint."""
    updates = []
    result = train(
        settings(100),
        [dataset],
        tmp_path / "cancelled",
        progress=updates.append,
        cancel=lambda: bool(updates),
    )
    assert result["status"] == "cancelled"
    assert result["trained_steps"] == 1
    assert checkpoints.verify(tmp_path / "cancelled")["trained_steps"] == 1
    with pytest.raises(ValueError, match="before an optimizer"):
        train(settings(), [dataset], tmp_path / "not-published", cancel=lambda: True)
    assert not (tmp_path / "not-published").exists()


def random_sd(root: Path):
    """Create tiny typed components from random weights; no downloaded/pickle model or claimed artistry."""
    from diffusers import (
        StableDiffusionPipeline,
        UNet2DConditionModel,
        AutoencoderKL,
        DDIMScheduler,
    )
    from transformers import CLIPTokenizer, CLIPTextConfig, CLIPTextModel

    visible = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    missing = [byte for byte in range(256) if byte not in visible]
    characters = [chr(byte) for byte in visible] + [
        chr(256 + index) for index in range(len(missing))
    ]
    vocab = {}
    for character in characters:
        vocab[character] = len(vocab)
        vocab[character + "</w>"] = len(vocab)
    for special in ("<|startoftext|>", "<|endoftext|>"):
        vocab[special] = len(vocab)
    tokenizer = CLIPTokenizer(vocab=vocab, merges=[], model_max_length=32)
    text = CLIPTextModel(
        CLIPTextConfig(
            vocab_size=len(tokenizer),
            hidden_size=16,
            intermediate_size=32,
            num_hidden_layers=1,
            num_attention_heads=2,
            max_position_embeddings=32,
            bos_token_id=tokenizer.bos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    )
    unet = UNet2DConditionModel(
        sample_size=16,
        in_channels=4,
        out_channels=4,
        layers_per_block=1,
        block_out_channels=(16, 32),
        down_block_types=("DownBlock2D", "CrossAttnDownBlock2D"),
        up_block_types=("CrossAttnUpBlock2D", "UpBlock2D"),
        cross_attention_dim=16,
        attention_head_dim=4,
        norm_num_groups=8,
    )
    vae = AutoencoderKL(
        in_channels=3,
        out_channels=3,
        down_block_types=("DownEncoderBlock2D", "DownEncoderBlock2D"),
        up_block_types=("UpDecoderBlock2D", "UpDecoderBlock2D"),
        block_out_channels=(16, 32),
        layers_per_block=1,
        latent_channels=4,
        norm_num_groups=8,
        sample_size=32,
    )
    pipe = StableDiffusionPipeline(
        unet=unet,
        vae=vae,
        text_encoder=text,
        tokenizer=tokenizer,
        scheduler=DDIMScheduler(num_train_timesteps=100, steps_offset=1, clip_sample=False),
        safety_checker=None,
        feature_extractor=None,
        requires_safety_checker=False,
    )
    pipe.save_pretrained(root, safe_serialization=True)
    return root


def test_real_lora_adapter_reload_and_generation(dataset, tmp_path):
    """Optimize actual attention adapter tensors, verify nonzero changes, reload and run fixed SD pipeline."""
    import peft

    assert peft.__version__ == "0.21.1"
    from studio.pretrained import train_lora, generate as sd_generate, inspect

    base = random_sd(tmp_path / "base")
    inspect(base)
    config = {
        **settings(2),
        "name": "Random fixture adapter",
        "mode": "lora",
        "base_model_id": "base",
        "batch_size": 1,
    }
    adapter = tmp_path / "adapter"
    report = train_lora(config, [dataset], base, adapter)
    tensors = load_file(str(adapter / "pytorch_lora_weights.safetensors"))
    assert any(
        torch.count_nonzero(value).item()
        for key, value in tensors.items()
        if "lora.up" in key or "lora_B" in key
    )
    assert report["steps"] == 2
    result = sd_generate(generation(steps=2), base, tmp_path / "lora.png", adapter_path=adapter)
    assert result["width"] == 32
    with Image.open(tmp_path / "lora.png") as image:
        assert image.size == (32, 32)
    index = read_json(base / "model_index.json")
    index["scheduler"] = ["os", "system"]
    atomic_json(base / "model_index.json", index)
    with pytest.raises(ValueError, match="scheduler"):
        inspect(base)


@pytest.mark.parametrize("shard", ["../../outside.safetensors", "C:/outside.safetensors", {}, []])
def test_pretrained_shard_index_cannot_escape_or_crash(tmp_path, shard):
    """Reject malformed or escaping indexes before a pretrained loader can open any shard."""
    from studio.formats import inspect_diffusers

    base = random_sd(tmp_path / "base")
    atomic_json(
        base / "unet" / "diffusion_pytorch_model.safetensors.index.json",
        {
            "weight_map": {"tensor": shard},
        },
    )
    with pytest.raises(ValueError, match="shard"):
        inspect_diffusers(base)
