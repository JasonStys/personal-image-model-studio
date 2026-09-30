# Validation record

Local verification: 2026-09-30, Windows 11, Python 3.12.10, Node 24.18.1. Commands were run against a new independent virtual environment, not the predecessor's installed application. Runtime datasets, weights, access tokens, account information and raw machine paths are excluded from Git.

## Executed checks

| Check | Observed result |
| --- | --- |
| `python -m pytest --cov=studio` | **56 passed**, 27.68 seconds; 45 core/connector/job cases plus 11 real ML cases. |
| In-process statement coverage | **80%**, 1,604 statements, 314 missed. Browser/CLI/worker subprocess activity is not included in this coverage figure. This is not exhaustive proof of correctness. |
| Real native training and resume | Fresh optimizer updates, held-out noise loss improvement, finite weights, EMA, and bitwise same-stack CPU continuous-versus-resumed state passed. |
| Real generation/editing | Repeatable seed, changed numeric weights, regional conditioning, image editing, cancellation and exact protected-pixel preservation passed. |
| Classic SD adapter | Tiny randomly initialized, owned components; two genuine LoRA optimizer steps, nonzero adapter changes, safe reload and image generation passed. This is an integration test, not an artistic quality benchmark. |
| Unsafe input regressions | Traversal/oversized ZIPs, provenance conflicts, tampered dataset pixels, malformed model manifests and escaping/unhashable shard references rejected. |
| DeviantArt contract tests | 16 offline cases passed: PKCE/state, own-account binding, pagination, redirects, data budgets, opt-outs, metadata and separate unauthenticated CDN downloads. **No live account import was tested.** |
| Browser/accessibility suite | **8 passed**, 43.0 seconds: Chromium, Firefox, WebKit and an iPhone-sized viewport. Automated accessibility assertions are not a complete accessibility certification. |
| Browser real-ML workflow | **1 passed**, 29.4 seconds: create owned data → train a new model in a subprocess → register it → generate → display its image. |
| Windows portable shell | PyInstaller build succeeded. Its running authenticated API reached a configured independent worker; that worker trained a real 20-step model and registered it. Shared browser UI exercised against the packaged server. Native window controls were not independently automated/visually inspected. |
| Source quality | Ruff lint/format, TypeScript type check, production Vite build, Prettier, and all 34 exact source declaration/variable indexes passed. |
| Dependency consistency/security | `pip check` passed; isolated-environment `pip-audit` found no known dependency vulnerabilities, with no advisory exemptions. The unpublished project itself has no PyPI advisory record and is checked through source/tests, not this database. `npm audit` also found zero known vulnerabilities. Absence of known advisories is not proof of safety. |

The reference ML environment is Torch 2.14.0 CPU, Torchvision 0.29.0, Diffusers 0.38.0, Transformers 5.12.1, PEFT 0.21.1 and Accelerate 1.15.0. CPU package availability was checked on the official PyTorch index. The earlier genuine CUDA demonstration used a different stack, recorded separately below; it is not attributed to this CPU environment.

## Actual custom model evidence

The [real browser-worker screenshot](ui-real-model.png) shows the completed 20-step integration test. That deliberately tiny test model produces noise-like pixels; it validates the training/generation path, **not** useful image quality. The separately trained 6,000-step model below is the shape-learning demonstration. Neither screenshot contains account artwork or private settings.

[Sanitized measurements](synthetic-training.json) and [generated contact sheet](synthetic-samples.png) were produced by `scripts/train_demo.py` and exported by the guarded `scripts/publish_evidence.py`. The model learned from 307 training and 73 disjoint held-out owned procedural images. It contains 266,211 parameters, was trained for 6,000 steps in 148.42 seconds on a local CUDA device, and achieved held-out noise MSE 0.00808 (EMA 0.00669), versus initialization 1.13190. The report identifies Torch 2.11.0+cu128 for that baseline.

These are small 32-pixel learned shape examples displayed larger, not high-resolution photorealistic images. Noise MSE does not establish prompt fidelity, visual safety, generalization to artwork or comparative model superiority. No website artwork, downloaded base model, password or provider token was used for this evidence.

## Hosted verification

The pinned workflow runs six backend OS/Python combinations, a browser lane, real CPU ML/browser integration and unsigned Windows packaging. It uploads test/audit reports as build artifacts, runs on changes and weekly, and does not upload user runtime data. [Initial hosted run 36685719525](https://github.com/JasonStys/personal-image-model-studio/actions/runs/36685719525), source commit `aec719a616e30fa32f70264bf5b42518c736b088`, completed successfully in all **nine jobs**: Windows/macOS/Linux contracts on Python 3.12/3.14, all browser projects, real CPU ML/browser integration and Windows packaging. Latest commit results are available in [GitHub Actions](https://github.com/JasonStys/personal-image-model-studio/actions).

Hosted `pip-audit` cannot resolve official-index `torch==2.14.0+cpu` and `torchvision==0.29.0+cpu` against PyPI. The workflow additionally audits the pinned upstream release versions in `requirements-cpu-audit.txt` without installing packages or exempting advisories. This closes the release-metadata lookup gap; it is not a binary scan or a guarantee that every build-specific vulnerability is represented. All other installed third-party dependency records are audited normally. The unpublished local package remains outside public package-advisory matching.

## Remaining boundaries

Live DeviantArt OAuth requires a human-registered public OAuth app, exactly whitelisted callback, legal/rights review and account authorization. The browser currently reports access denied; no account access is claimed. Signing/distribution, multi-gigabyte ML installation, native macOS/Linux/mobile packaging, semantic vision evaluation, arbitrary pretrained architectures and automated cloud provisioning remain outside this release. See [requirements](../requirements.md) and [installation](../installation.md).
