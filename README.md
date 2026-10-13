# Personal Image Model Studio

[![Validate](https://github.com/JasonStys/personal-image-model-studio/actions/workflows/validate.yml/badge.svg)](https://github.com/JasonStys/personal-image-model-studio/actions/workflows/validate.yml)

A local-first image-generation workbench by **Jason Stys**, with real private accounts, **actual custom diffusion training**, structured prompts and auditable datasets. Python handles learning and the local service; TypeScript/HTML/CSS provide the responsive interface; SQL indexes account-scoped records.

## Download and open

Get the checksummed CPU application for your OS from [Releases](https://github.com/JasonStys/personal-image-model-studio/releases). Extract and open `PersonalImageModelStudio` (`.exe` on Windows). It launches a private website in your normal browser, with no Python/npm setup for native-model training or generation. Keep the application process running. This is an **unsigned portable application**, not a signed installer or public hosted service.

Create an alias/password, save the once-shown login recovery code and choose a separate vault phrase. Private files live outside Git and the installation. Locked workspaces use authenticated encryption; active ML needs temporary plaintext on your own device. OS administrators/compromised devices can access active data; crashes can leave protected recovery files. No telemetry, ad SDK, default external AI calls, automatic model downloads or developer account-access backdoor is included. Forgotten vault phrases cannot be recovered.

[Private installation/help](docs/private-installation.md) · [Account security and limits](docs/private-accounts.md) · [New validation evidence](docs/reports/private-validation.md) · [Jason's contact](https://www.linkedin.com/in/jason-stys-31b30b351/)

It does not generate placeholder images when no model exists. Train a fresh compact native model or explicitly register an authorized, compatible local classic Stable Diffusion export. No third-party artwork or pretrained weights are distributed here.

![Real learned synthetic CPU samples](docs/reports/synthetic-cpu-samples.png)

Rows: circle, square, triangle. Columns: red, green, blue. These samples came from real learned weights after 6,000 optimizer updates on owned procedural shapes, using the reference Torch 2.14 CPU environment—not a procedural renderer at inference time. The small model still produces rough edges and is **not a general-purpose or photorealistic generator**. See [validation evidence](docs/reports/validation.md), including exact runtime versions, separately retained earlier GPU evidence and limitations.

## Features

- Independent scene, style, tag, negative and subject fields; explicit `(phrase:1.4)` weights; optional experimental native subject boxes.
- Real from-scratch diffusion: learned caption vocabulary/embeddings, small UNet, held-out denoising evaluation, EMA weights, safe checkpoint reload and AdamW/RNG resume.
- Text generation, image-to-image editing, white-edit/black-preserve masks and centered aspect-ratio expansion. Known pixels are overlaid exactly at output; semantic quality remains model-dependent.
- Directory/ZIP ingestion with caption and metadata sidecars, provenance, pixel deduplication, deterministic train/validation splitting and physically separate AI-origin quarantine metadata.
- Classic single-encoder Stable Diffusion safe-tensor imports and real attention-only LoRA training. Supported families are explicit; arbitrary executable models are rejected.
- Human feedback, explicit revisions and consented feedback ZIP exports. Generated pixels keep their AI-origin labels; ordinary training excludes them. No hidden retraining or automatic score inflation.
- Reviewed tag glossary, transparent local phrase rules, private run reports, bounded job queue, cancellation and interrupted-run recovery.
- Prioritized DeviantArt OAuth/PKCE connector with read-only operations for your own authorized gallery. Provider token permissions may be broader, including Sta.sh management: review the actual consent screen. Passwords stay in the provider browser; OAuth tokens stay in memory. Live account access requires your registered public client ID and authorization.
- Account login/recovery/deletion, account-scoped file pickers, encrypted idle snapshots, lock/sign-out, human-idle timeout and built-in help. Browser mode cannot select executable runtimes or read arbitrary PC paths.
- Responsive browser UI plus portable CPU packages built and smoke-tested on Windows amd64, macOS arm64 and Linux x86_64 before publication. Mobile viewport coverage is not a native iOS/Android installer or public mobile host.

## Run locally

Python 3.12 and Node 24 are the reference toolchains. Choose an isolated environment; ML dependencies are substantial. CPU works without Docker. For a compatible GPU build, consult the official PyTorch installer and verify the version/driver combination rather than silently replacing system drivers.

```bash
python -m venv .venv
# Activate .venv using your operating system's normal activation command.
python -m pip install -e ".[dev,ml,desktop]"
npm ci
npm run build
python -m studio.private_cli
```

The launcher opens a token-free loopback URL at an available port. Sign in, then unlock the separate vault. Source mode with full ML extras preserves compatible classic SD/LoRA; the bundled CPU application supports native models only. `python scripts/build_native.py` builds that CPU package after the UI build. No model weights or GPU drivers are bundled.

**Legacy developer mode:** `python -m studio.cli --port 8016` / `--desktop` and `scripts/build_desktop.py` remain for historical reproducibility. They use a single-user bearer-token workspace, not the new encrypted account mode. Do not expose either launcher to a public network. Existing legacy data is preserved and not silently migrated.

[Installation and packaging](docs/installation.md) · [Walkthrough](docs/user-guide.md) · [DeviantArt setup](docs/deviantart.md)

For a small real-artwork training example without an account, use the optional [licensed sketch sample](docs/licensed-sample.md). The actual app test trained a fresh 6,000-step model on 384 sketches and verified generation/seed replay; [measurements](docs/reports/quickdraw-training.json) also record its rough scribble-like outputs and weak category fidelity. Downloads require explicit opt-in; existing synthetic examples remain available.

Live DeviantArt authorization and identity lookup were verified. The approved own-gallery sample returned no supported images, so account-artwork training remains unvalidated until eligible permitted images are supplied. The real synthetic custom-model evidence above is separate; see the [live validation record](docs/reports/deviantart-live-validation.json).

## Reproduce validation

```bash
python -m pytest tests/test_core.py tests/test_deviantart.py tests/test_quickdraw.py tests/test_jobs.py
python -m pytest tests/test_ml.py
python -m pytest tests/test_private.py tests/test_private_ml.py
python -m ruff check studio scripts tests
python -m ruff format --check studio scripts tests
npm run build
node scripts/code_index.mjs --check
npm run test:browser
npm run test:private
# RUN_ML_BROWSER=1 selects the separate real browser-to-ML-worker test.
python scripts/train_demo.py --root artifacts/my-demo --steps 6000 --device auto
```

Demo outputs/checkpoints are local and ignored by Git. Use a new output directory; existing models are never overwritten. CI repeats contract/account tests on three OSes/two Python versions, real CPU training/resume/LoRA and browser-worker tests, four browser profiles, dependency audits and legacy Windows packaging. A separate release gate requires green exact-source validation and real training/generation/encrypted-reopen tests of all three packaged executables. CI artifact uploads are opt-in (`PIMS_UPLOAD_CI_ARTIFACTS=true`); downloads use Releases rather than Actions storage. CI is not a GPU quality evaluation or proof of compatibility with every device/model.

## Layout and file responsibilities

| File/group | Responsibility |
| --- | --- |
| `studio/contracts.py` | Closed bounded input schemas and cross-field validation. |
| `studio/api.py` | Preserved internal ML API and legacy single-user routes, provenance and artifacts. |
| `studio/cli.py` | Legacy browser/native launch and per-process bearer session. |
| `studio/private_cli.py`, `private_api.py` | Default account launcher, loopback/CSRF boundary, account routes, uploads and scoped ML proxy. |
| `studio/accounts.py` | Scrypt passwords, session/recovery digests, throttles and versioned key configuration. |
| `studio/private_workspace.py`, `vault.py`, `permissions.py` | Exclusive local engine, streaming encrypted archive, protected roots, lock/recovery lifecycle. |
| `studio/prompts.py` | Numeric weight syntax, independent sections and phrase policy. |
| `studio/files.py` | Atomic JSON, hashes, confinement and metadata-stripping raster decode. |
| `studio/datasets.py` | Safe local/ZIP import, deduplication, splits, AI exclusion and owned fixtures. |
| `studio/model.py` | Fresh word vocabulary, weighted text/time conditioning and compact denoiser. |
| `studio/training.py` | Actual native optimization, held-out metrics, EMA and continuation. |
| `studio/checkpoints.py` | Fixed-architecture safe-tensor manifests, integrity and optimizer recovery. |
| `studio/native.py` | Learned DDIM sampling, regions and source-preserving edits. |
| `studio/formats.py` | Fixed pretrained classes, file budgets and base-model fingerprints. |
| `studio/pretrained.py` | Offline classic SD generation and real LoRA adapter training. |
| `studio/jobs.py`, `worker.py` | Serialized bounded subprocess lifecycle and trusted dispatch. |
| `studio/store.py` | Parameterized short-lived SQLite connections and quarantine database. |
| `studio/feedback.py` | Explicit latest-consent AI-labelled feedback export. |
| `studio/deviantart.py` | Own-gallery OAuth/PKCE, memory credentials, bounded metadata/raster downloads. |
| `studio/__init__.py` | Package marker. |
| `web/main.ts`, `portal.ts`, `workspace.ts`, `api.ts`, `types.ts`, `style.css` | Fail-closed mode selection, login/key derivation/help, ML UI, cookie transport, contracts and responsive styling. |
| `index.html`, `tsconfig.json`, `package*.json`, `pyproject.toml` | Entry document, strict compilation, locked browser dependencies and Python extras. |
| `scripts/train_demo.py` | Real fresh training and learned sample contact sheet. |
| `scripts/build_desktop.py`, `desktop_entry.py` | Native portable shell packaging/entry. |
| `scripts/build_native.py`, `native_entry.py`, `smoke_native.py` | Checksummed CPU executable, embedded worker entry and actual packaged account/ML validation. |
| `scripts/private_browser_server.py`, `playwright.private.config.ts`, `tests/private*.spec.ts` | Disposable profile services, real account browsers and genuine training workflows. |
| `tests/test_private.py`, `test_private_ml.py` | Ownership/authentication, boundary/crypto/corruption/recovery and actual encrypted ML lifecycle tests. |
| `scripts/code_index.mjs`, `python_index.py` | Reproducible exact declaration/variable line headers and detailed code map. |
| `tests/test_core.py`, `test_deviantart.py`, `test_jobs.py`, `test_ml.py` | Core/privacy/property, mocked provider-contract, lifecycle and real ML regression tests. |
| `scripts/prepare_quickdraw.py`, `evaluate_quickdraw.py`, `tests/test_quickdraw.py` | Opt-in licensed sketch sampling, genuine checkpoint/inference evaluation and offline bounded-input tests. |
| `tests/browser*.spec.ts`, `playwright.config.ts` | Real browser accessibility/portability and separate real ML-worker workflow. |
| `.github/workflows/validate.yml`, `release-native.yml` | Pinned validation/audits and exact-source three-platform draft-to-published release gates. |
| `requirements-cpu-audit.txt` | Upstream advisory lookup for pinned official CPU-wheel releases; not an installer. |
| `scripts/publish_evidence.py`, `.gitattributes` | Guarded synthetic-only public evidence export and stable text line endings. |
| `docs/` | Architecture, requirements traceability, threats, complexity, research, operating instructions and validation reports. |
| `.gitignore`, `LICENSE`, `SECURITY.md` | Private-artifact exclusions, software license and safe vulnerability reporting. |

[Detailed source map](docs/code-map.json) includes each declaration, argument/local variable, actual line and source-derived purpose. Header indexes are generated and checked in CI so line references cannot silently drift.

## Scope and responsible use

Use only data/models you own or are permitted to process and train on. Account access is not a copyright/license grant. AI-origin detection uses explicit labels—not an infallible visual detector. A human checks captions, rights, image quality and safety. Accounts isolate local records, but only one account may unlock the engine at a time. This is not hardened multi-tenant hosting and must not be exposed to a public network. An archive download alone lacks account/key settings: cold-back up the complete protected data root. The [requirements matrix](docs/requirements.md) separates preserved capabilities and limitations.
