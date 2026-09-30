# Installation and packaging

## Browser/developer setup

Use Python 3.12 and Node 24. Create a **new** `.venv` for this repository; do not reuse/upgrade an unrelated application's runtime. Install `.[dev,ml,desktop]`, run `npm ci` and `npm run build`, then `python -m studio.cli --port 8016`. The private token link printed by the CLI authorizes one local session. Tokens are not model/API credentials and must not be published. Closing the browser does not stop a separately launched server; stop its own terminal/server when finished.

CPU is the portable default and is used by hosted CI. The reference patched ML stack is Torch 2.14.0 / Torchvision 0.29.0 / Diffusers 0.38.0 / Transformers 5.12.1 / PEFT 0.21.1 / Accelerate 1.15.0. Install matching GPU wheels from the official PyTorch index if available for your OS/driver, then verify `torch.cuda.is_available()` and `python -m pip check`. Never assume a GPU index carrying an older release also carries the pinned version. No Docker repair or driver changes are needed for the CPU workflow.

## Windows portable shell

`python scripts/build_desktop.py` produces `artifacts/desktop/PersonalImageModelStudio/PersonalImageModelStudio.exe` plus its `_internal` dependencies. Copy the **whole directory**; do not copy only the executable. CI exposes the unsigned shell as a build artifact. The first launch needs an available WebView2 runtime; the app does not install it or bypass security warnings.

Double-click the executable to open the app. Under Method & limits, select your installed trusted ML environment's `python.exe`, acknowledge that you trust it, and save while no job is active. Only future jobs use this interpreter; changing it cannot splice runtimes into a running job. The selected path is private local configuration, not an argument-bearing shell command. The default packaged workspace is inside the user's local application-data directory; `--data` can select an explicit alternative.

The shell bundles UI/API/Python runtime support, not multi-gigabyte ML packages, model weights or graphics drivers. Therefore it is a portable application with a one-time ML setup, **not** a self-contained universal installer. The repository does not claim signed Windows packages or native installers for every OS/mobile device. Linux/macOS native WebView launch needs that platform's pywebview prerequisites; only browser compatibility and API portability are CI-verified on those systems.

## Original project isolation

Do not import the predecessor's native model as a new native checkpoint. The versioned model schemas/architectures differ. Use a reviewed image/sidecar export to migrate datasets; retain original backups. Never point package installation commands at the original application's environment. Local validation reused some existing libraries read-only initially; final dependency upgrades were installed only into the new environment. GPU baseline evidence identifies the earlier library versions instead of pretending it used the newer CPU reference stack.

## Troubleshooting

Port occupied: stop only the server you own or select another port. Different OAuth ports need an exactly matching provider whitelist entry. No model: train an owned synthetic dataset first or register a compatible local export. Missing Torch/PEFT: select/install the documented ML extras in the chosen runtime. Bad model/shard/pickle: re-export supported classes to safe tensors rather than relaxing validation. Interrupted job: read its report, then explicitly resume the verified native checkpoint if one was published. A shutdown/cancelled job without a checkpoint is not a successful training run.
