# Research used in implementation

Reviewed 2026-09-29/30. Primary documentation and local installed source informed the implementation; provider/license texts are reference material, not instructions to accept agreements or access accounts.

| Source | Application here |
| --- | --- |
| [Diffusers basic training](https://huggingface.co/docs/diffusers/tutorials/basic_training) | Train noise predictions from real image batches; fresh model training is distinct from sampling a pretrained model. |
| [DDIM scheduler](https://huggingface.co/docs/diffusers/api/schedulers/ddim) | Matching train/inference schedule, seeded eta-zero sampling and clipped-output noise correction. |
| [LoRA training](https://huggingface.co/docs/diffusers/training/lora) | Freeze base/VAE/text encoder, optimize attention adapters and preserve an explicit local base dependency. |
| [Weighted prompts](https://huggingface.co/docs/diffusers/main/using-diffusers/weighted_prompts) | Numerical conditioning weights are implemented, not just stored as decorative prompt strings. This parser supports a deliberately smaller flat grammar. |
| [Inpainting pipeline](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/inpaint) | White-edit/black-preserve convention, source/mask validation and final exact-known-pixel overlay. |
| [PyTorch reproducibility](https://docs.pytorch.org/docs/stable/notes/randomness.html) | Dedicated RNG, fixed CPU resume comparison and no cross-hardware bitwise reproducibility guarantee. |
| [Safetensors](https://huggingface.co/docs/safetensors) | Non-pickle model/optimizer tensors, strict fixed architecture and supplementary hashes/bounds. |
| [PEFT releases](https://github.com/huggingface/peft/releases) | Transformers 5 requires a newer PEFT release than the predecessor's adapter dependency. |
| [Accelerate advisory](https://github.com/advisories/GHSA-4j2p-28q2-5m79) | Upgrade beyond affected≤1.14 versions and explicitly guard shard paths/file types. |
| [Setuptools advisory](https://github.com/advisories/GHSA-h35f-9h28-mq5c) | Use patched build tooling, keep private data out of distribution sources and audit dependencies. |
| [DeviantArt OAuth](https://deviantart.readme.io/docs/authentication) | Public-client S256 PKCE, exact callback/state, server-side bearer exchange and memory-only token handling. |
| [Gallery](https://deviantart.readme.io/reference/gallery_all), [metadata](https://deviantart.readme.io/reference/deviation_metadata), [whoami](https://deviantart.readme.io/reference/user_whoami) | Read-only own-account binding, bounded paging and retained inert captions/tags. |
| [Provider getting started](https://deviantart.readme.io/docs/getting-started) | User-agent/compression requirements and human review of API terms before live use. |

Local prototype history supplied desired workflows; the implementation choices and capability limits were independently reviewed. Automatic tag research, broad semantic judging, arbitrary models/websites and paid cloud provisioning were not implemented based on unsupported assumptions.
