"""Compact text-conditioned U-Net diffusion model; vocabulary and weights start from scratch."""

# Index: declarations module.vocabulary@L10, module.encode@L18, module.Residual@L40, Residual.__init__@L43, Residual.forward@L52, module.NativeDenoiser@L60, NativeDenoiser.__init__@L63, NativeDenoiser.forward@L81; variables captions@L10, text@L12, tokens@L12, word@L12, length@L18, text@L18, vocab@L18, index@L20, lookup@L20, word@L20, pairs@L21, span@L23, weight@L23, word@L24, warnings@L26, _@L27, index@L27, unknown@L27, word@L27, pairs@L32, p@L34, p@L35, channels@L43, context@L43, self@L43, context@L52, image@L52, self@L52, scale@L54, shift@L54, hidden@L55, hidden@L56, channels@L63, self@L63, vocab_size@L63, ids@L81, image@L81, self@L81, timestep@L81, weights@L81, timestep@L84, frequencies@L85, phase@L86, time@L87, text@L88, context@L91, high@L92, low@L93, merged@L94. Purposes/parameters: docs/code-map.json.
import math
import torch
from torch import nn
from studio.prompts import words, weighted


def vocabulary(captions: list[str]) -> list[str]:
    """Deterministically learn a capped word vocabulary from training captions only."""
    tokens = sorted({word for text in captions for word in words(text)})
    if len(tokens) > 4094:
        raise ValueError("Native vocabulary exceeds 4094 words")
    return ["<pad>", "<unknown>", *tokens]


def encode(text: str, vocab: list[str], length: int = 32):
    """Return token IDs, numeric weights and visible unknown/truncation warnings."""
    lookup = {word: index for index, word in enumerate(vocab)}
    pairs = [
        (lookup.get(word, 1), weight, word)
        for span, weight in weighted(text)
        for word in words(span)
    ]
    warnings = []
    unknown = sorted({word for index, _, word in pairs if index == 1})
    if unknown:
        warnings.append("Unlearned native words: " + ", ".join(unknown))
    if len(pairs) > length:
        warnings.append(f"Native prompt truncated to {length} tokens")
    pairs = pairs[:length]
    return (
        [p[0] for p in pairs] + [0] * (length - len(pairs)),
        [p[1] for p in pairs] + [0.0] * (length - len(pairs)),
        warnings,
    )


class Residual(nn.Module):
    """Two spatial convolutions modulated by shared timestep/text context."""

    def __init__(self, channels: int, context: int):
        """Allocate GroupNorm and FiLM modulation at fixed channel dimensions."""
        super().__init__()
        self.norm1 = nn.GroupNorm(8, channels)
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.context = nn.Linear(context, channels * 2)
        self.norm2 = nn.GroupNorm(8, channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)

    def forward(self, image, context):
        """Use image [B,C,H,W] and context [B,D] to return an equal-shaped residual."""
        scale, shift = self.context(context).chunk(2, dim=1)
        hidden = self.conv1(torch.nn.functional.silu(self.norm1(image)))
        hidden = self.norm2(hidden) * (1 + scale[:, :, None, None]) + shift[:, :, None, None]
        return image + self.conv2(torch.nn.functional.silu(hidden))


class NativeDenoiser(nn.Module):
    """Small conditional U-Net with learned word embeddings, time features and spatial skip connection."""

    def __init__(self, vocab_size: int, channels: int = 32):
        """Initialize only fresh parameters; this model never retrieves pretrained weights."""
        super().__init__()
        if not 2 <= vocab_size <= 4096 or channels not in (16, 32, 64):
            raise ValueError("Unsupported native architecture")
        self.embedding = nn.Embedding(vocab_size, 64, padding_idx=0)
        self.time = nn.Sequential(nn.Linear(64, 64), nn.SiLU(), nn.Linear(64, 64))
        self.input = nn.Conv2d(3, channels, 3, padding=1)
        self.high = Residual(channels, 64)
        self.down = nn.Conv2d(channels, channels * 2, 4, stride=2, padding=1)
        self.low1 = Residual(channels * 2, 64)
        self.low2 = Residual(channels * 2, 64)
        self.up = nn.ConvTranspose2d(channels * 2, channels, 4, stride=2, padding=1)
        self.merge = nn.Conv2d(channels * 2, channels, 1)
        self.output = nn.Sequential(
            nn.GroupNorm(8, channels), nn.SiLU(), nn.Conv2d(channels, 3, 3, padding=1)
        )

    def forward(self, image, timestep, ids, weights):
        """Predict diffusion noise using numeric-weighted text embeddings; masks weight only real tokens."""
        if timestep.ndim == 0:
            timestep = timestep.expand(image.shape[0])
        frequencies = torch.exp(torch.arange(32, device=image.device) * (-math.log(10000) / 31))
        phase = timestep.float()[:, None] * frequencies[None, :]
        time = self.time(torch.cat((phase.sin(), phase.cos()), dim=1))
        text = (self.embedding(ids) * weights[:, :, None]).sum(dim=1) / (
            (ids != 0).sum(dim=1).clamp(min=1)[:, None]
        )
        context = time + text
        high = self.high(self.input(image), context)
        low = self.low2(self.low1(self.down(high), context), context)
        merged = self.merge(torch.cat((self.up(low), high), dim=1))
        return self.output(merged)
