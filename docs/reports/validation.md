# Validation record

Local verification: 2026-09-30, Windows 11, Python 3.12.10, Node 24.18.1. Commands were run against a new independent virtual environment, not the predecessor's installed application. Runtime datasets, weights, access tokens, account information and raw machine paths are excluded from Git.

## Executed checks

| Check | Observed result |
| --- | --- |
| `python -m pytest -p no:cacheprovider --basetemp=<fresh-owned-artifact-dir> --cov=studio` | **67 passed**, 49.70 seconds; 56 core/connector/job cases plus 11 real ML cases. Includes malformed-provider/input regressions and an explicit empty-gallery cleanup/no-download test. Earlier 66-case run passed in 34.94 seconds. |
| In-process statement coverage | **81%** rounded, 1,618 statements, 312 missed. Browser/CLI/worker subprocess activity is not included in this coverage figure. This is not exhaustive proof of correctness. |
| Real native training and resume | Fresh optimizer updates, held-out noise loss improvement, finite weights, EMA, and bitwise same-stack CPU continuous-versus-resumed state passed. |
| Real generation/editing | Repeatable seed, changed numeric weights, regional conditioning, image editing, cancellation and exact protected-pixel preservation passed. |
| Classic SD adapter | Tiny randomly initialized, owned components; two genuine LoRA optimizer steps, nonzero adapter changes, safe reload and image generation passed. This is an integration test, not an artistic quality benchmark. |
| Unsafe input regressions | Traversal/oversized ZIPs, provenance conflicts, tampered dataset pixels, malformed model manifests and escaping/unhashable shard references rejected. |
| DeviantArt contract tests | **27 offline cases passed**: PKCE/state, required scopes, own-account binding, pagination, redirects, data budgets, opt-outs, malformed/null fields, empty-gallery cleanup and separate unauthenticated CDN downloads. These fixtures are not live artwork evidence. |
| Live DeviantArt authorization/import | Human-approved token exchange and identity lookup **passed**. Separately authorized import of at most 24 own-gallery entries returned HTTP 400, `No supported images found`, in about 0.47 seconds. No dataset was registered or import staging directory retained; account-artwork training did not start. |
| Browser/accessibility suite | All **8 cases passed** across runs: six Chromium/WebKit/mobile cases in 37.9 seconds; two Firefox cases in 16.4 seconds using a freshly downloaded isolated official runtime after the existing runtime failed to launch. Includes actual permission-warning visibility. Automated accessibility assertions are not a complete accessibility certification. |
| Browser real-ML workflow | **1 passed**, 37.9 seconds: create owned data → train a new model in a subprocess → register it → generate → display its image. |
| Windows portable shell | PyInstaller build succeeded. Its running authenticated API reached a configured independent worker; that worker trained a real 20-step model and registered it. Shared browser UI exercised against the packaged server. Native window controls were not independently automated/visually inspected. |
| Source quality | Ruff lint/format, TypeScript type check, production Vite build, Prettier, and all 34 exact source declaration/variable indexes passed. |
| Dependency consistency/security | `pip check` passed; isolated-environment `pip-audit` found no known dependency vulnerabilities, with no advisory exemptions. The unpublished project itself has no PyPI advisory record and is checked through source/tests, not this database. `npm audit` also found zero known vulnerabilities. Absence of known advisories is not proof of safety. |

The reference ML environment is Torch 2.14.0 CPU, Torchvision 0.29.0, Diffusers 0.38.0, Transformers 5.12.1, PEFT 0.21.1 and Accelerate 1.15.0. CPU package availability was checked on the official PyTorch index. The earlier genuine CUDA demonstration used a different stack, recorded separately below; it is not attributed to this CPU environment.

### Test-environment incidents and recovery

The first continuation pytest run encountered permissions errors at an old shared temporary directory (22 cases passed, 34 setup errors). A new task-owned `--basetemp` and disabling the inaccessible old pytest cache resolved the setup issue; no ACLs were relaxed. The existing Firefox runtime reported `spawn UNKNOWN`; the same two tests passed with an isolated official Playwright Firefox download without changing browser/system settings. One overlapping browser-suite invocation encountered the shared port and disrupted another run's trace cleanup. Browser suites were then serialized and given distinct artifact directories; the real-ML rerun passed. These initial failures are not represented as passing runs or as application defects.

## Actual custom model evidence

The [real browser-worker screenshot](ui-real-model.png) shows the completed 20-step integration test. That deliberately tiny test model produces noise-like pixels; it validates the training/generation path, **not** useful image quality. The separately trained 6,000-step model below is the shape-learning demonstration. Neither screenshot contains account artwork or private settings.

The **fresh reference CPU model** has [sanitized measurements](synthetic-cpu-training.json) and a [generated contact sheet](synthetic-cpu-samples.png). It was trained for 6,000 steps on 307 owned training images, with 73 disjoint held-out images and 266,211 parameters. Actual Torch 2.14.0+cpu training took 444.25 seconds (13.51 steps/second); held-out noise MSE fell from 1.13477 to 0.01299, with EMA 0.00653. Nine 50-step learned generations produced the displayed sheet. The checkpoint was then verified/registered through the running browser UI; a new blue-triangle prompt completed through the worker in 0.403 seconds and its 128×128 image was displayed. Internal learned resolution remains 32 pixels.

The **separate earlier GPU baseline** retains [sanitized measurements](synthetic-training.json) and its [contact sheet](synthetic-samples.png). It used the same owned split size and parameter count, 6,000 steps in 148.42 seconds on a local CUDA device, and held-out noise MSE 0.00808 (EMA 0.00669), versus initialization 1.13190. That report identifies Torch 2.11.0+cu128. The CPU/GPU runs are not a controlled comparative benchmark because the software/device stacks differ. `scripts/publish_evidence.py --prefix synthetic-cpu` preserves the earlier evidence and derives the runtime description from actual measurements rather than a hardcoded GPU label.

These are small 32-pixel learned shape examples displayed larger, not high-resolution photorealistic images. Noise MSE does not establish prompt fidelity, visual safety, generalization to artwork or comparative model superiority. No website artwork, downloaded base model, password or provider token was used for this evidence.

## Hosted verification

The pinned workflow runs six backend OS/Python combinations, a browser lane, real CPU ML/browser integration and unsigned Windows packaging. It uploads test/audit reports as build artifacts, runs on changes and weekly, and does not upload user runtime data. [Initial hosted run 36685719525](https://github.com/JasonStys/personal-image-model-studio/actions/runs/36685719525), source commit `aec719a616e30fa32f70264bf5b42518c736b088`, completed successfully in all **nine jobs**: Windows/macOS/Linux contracts on Python 3.12/3.14, all browser projects, real CPU ML/browser integration and Windows packaging. Latest commit results are available in [GitHub Actions](https://github.com/JasonStys/personal-image-model-studio/actions).

Hosted `pip-audit` cannot resolve official-index `torch==2.14.0+cpu` and `torchvision==0.29.0+cpu` against PyPI. The workflow additionally audits the pinned upstream release versions in `requirements-cpu-audit.txt` without installing packages or exempting advisories. This closes the release-metadata lookup gap; it is not a binary scan or a guarantee that every build-specific vulnerability is represented. All other installed third-party dependency records are audited normally. The unpublished local package remains outside public package-advisory matching.

The continuation's [hosted run 36784162356](https://github.com/JasonStys/personal-image-model-studio/actions/runs/36784162356) completed successfully for source commit `5cc135b252a552898f8581182319d7b89ccf5d89`: **all nine jobs passed**, including all six OS/Python contract combinations, the complete browser suite, actual ML/browser integration with dependency audits, and Windows packaging. This report records an observed completed run, not a prediction for later commits; the workflow badge/latest run is the authority for subsequent changes.

## Remaining boundaries

Live DeviantArt inspection verified signed-in access, public registration, human-approved authorization and authenticated identity. Actual consent advertised Sta.sh management; read-only connector operations do not prove a read-only provider grant. The operator separately confirmed training rights/provider terms for the 24-entry attempt. The browser own-gallery view showed only one application listing, and the API import found no supported images. Its generic empty-result message does not identify item/skip counts, so an exact provider exclusion reason is not inferred. Eligible permitted artwork is still required to validate live account-dataset ingestion/training. Favourites or other artists' work were not substituted. A fresh browser generation using the existing genuinely trained CPU model completed after this empty import; account access is not required for local training/generation. See [sanitized live result](deviantart-live-validation.json).

Signing/distribution, multi-gigabyte ML installation, native macOS/Linux/mobile packaging, semantic vision evaluation, arbitrary pretrained architectures and automated cloud provisioning remain outside this release. See [connector details](../deviantart.md), [requirements](../requirements.md) and [installation](../installation.md).
