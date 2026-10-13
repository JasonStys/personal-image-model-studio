# Private account/CPU application validation — Jason Stys

Recorded 2026-10-12 (America/Los_Angeles). New tests use fictional aliases,
disposable directories and owned synthetic shapes; no provider account, private
artwork or third-party model weights are accessed. Historical 6,000-step quality
evidence is separate from short regression runs.

## Risk-based gates

| Risk | Executable checks |
| --- | --- |
| Credentials/cross-account reads | Password/session storage, second-user API denial, secret-free errors, recovery/revocation/deletion. |
| Cross-site requests/injected scripts | Exact Host/Origin, mutation header, body cap, CSP/no-store/no-referrer, inert hostile labels, no browser credential storage. |
| Archives/untrusted files | Authenticated decrypt-before-extract, tampered/wrong-key rejection, traversal/device names, links, ordered chunks/capacity, arbitrary path/runtime denial. |
| Losing data during sealing | Lock/reopen, interrupted owner recovery, exclusive data-root lock, disk-failure credential preservation. |
| Fake/nonfunctional learning | Optimizer updates, finite held-out metrics, EMA/RNG/resume, seed replay, masked/expanded pixels and native/LoRA regressions. |
| Package works only in source | Execute frozen binaries; register, train, generate, encrypt/remove staging, reload identical pixels and revoke login. |
| Usability/portability | Accessible login/help, responsive mobile viewport, file pickers, browser profiles and OS/Python contracts. |

Local full source suite: **109 passed**, with ResourceWarnings treated as errors;
three additional archive-portability regressions then passed in the **26-case**
private suite (112 distinct Python cases total).
Private browser workflows: **12 passed** across Chromium, WebKit and mobile.
The genuine Chromium private training/generation/lock/reopen scenario also passed.
A locally compiled Windows CPU executable passed all **11** smoke groups including
two optimizer steps and learned PNG generation. Two steps prove execution,
**not useful image quality**. Final release binaries require the exact-source CI
gates below; preliminary binaries are not substituted as final release evidence.

Tests exposed missing frozen Diffusers metadata and a Windows startup hang with a
blocking stdin orphan guard. Recursive metadata collection and exact-parent
PID/create-time monitoring corrected them. Whole encrypted snapshots may delay
metadata on a busy disk/CPU: browser operations are bounded at 30 seconds, without
retries or weakened assertions. Recovery seals successfully **before** consuming
its one-use code; simulated disk failure verifies that old credentials and unsaved
work survive. CI also detected Windows' legacy stdout encoding in the source-map
generator; its Python JSON stream is now explicitly UTF-8 on every platform.

The first three-platform release attempt kept its release unpublished when a
Windows concurrent-read collision denied atomic progress-file replacement.
Publication now retries only Windows sharing/access codes (5/32/33), at most eight
attempts and under two seconds of backoff, without changing permissions. Tests
cover transient success, unrelated immediate failure, permanent bounded failure,
preserved old JSON and removal of only its newly created temporary file. Packaged
notices also retain Python's full license and installed dependency license texts.

## Reproduce / release evidence

Use the README commands and `python scripts/smoke_native.py <exact-built-executable>`.
[Validate](https://github.com/JasonStys/personal-image-model-studio/actions/workflows/validate.yml)
has six OS/Python contract jobs, legacy/private browser profiles, genuine CPU
ML/browser jobs, audits, source indexes, formatting and legacy package compilation.
[Native release](https://github.com/JasonStys/personal-image-model-studio/actions/workflows/release-native.yml)
requires success for its exact SHA before creating a draft. It builds and executes
Windows amd64, macOS arm64 and Linux x86_64 CPU packages, publishing only after all
three succeed. Eleven smoke groups appear in each build log. CI artifact
uploads are opt-in; checksummed downloads use Releases.

Exact source `97055c206995dfb7b2cd702cb105968e503951cf` passed
[Validate run 38338416968](https://github.com/JasonStys/personal-image-model-studio/actions/runs/38338416968):
all nine jobs green; **100** contract/privacy cases on each of six OS/Python
combinations, **12** genuine ML cases, **8** legacy and **16** private browser
scenarios across four profiles, plus **two** actual browser-to-ML-worker scenarios.
Ruff, Prettier, exact source indexes, TypeScript compilation, pip compatibility
and npm/Python/CPU-upstream advisory checks passed. Audits reported no known
vulnerabilities at the recorded time, not a guarantee of no future advisories.

Final executable source `6fe6bad00eb0c65b935272bb421b6b743fcb4fe0` passed
[Validate run 38339824441](https://github.com/JasonStys/personal-image-model-studio/actions/runs/38339824441):
all nine jobs green, **105** contract/privacy cases on each OS/Python combination
and **12** ML cases (**117** distinct Python tests), with the same **26** browser
scenarios and advisory/style/index checks green.
[Native release run 38340099114](https://github.com/JasonStys/personal-image-model-studio/actions/runs/38340099114)
then passed its prepare, **three actual executable** and publish jobs. Every OS
passed all **11** packaged smoke groups. The resulting
[0.2.0 download](https://github.com/JasonStys/personal-image-model-studio/releases/tag/v0.2.0)
is published; earlier failed attempts were preserved as diagnostic history, not
hidden or counted as passes. Release checksums cover each archive and executable.

## Deployment, rollback and limits

Verify the archive checksum, extract in a controlled directory and use a private
OS login/device encryption. No public deployment, provider sign-in, startup/firewall
change or driver repair is required. Stop the service and cold-back up the **entire**
protected account directory before upgrade/restore; an archive alone lacks login/key
settings. Never overwrite a running data root. Roll back only to a compatible
account-format build using a preserved backup/new isolated location; 0.1 legacy
mode cannot read 0.2 encrypted data. Preserve originals on any failure.

Remaining gates: independent penetration review, signing/notarization, recovery
UX for incomplete hardware-crash state, broad hardware validation, native mobile
apps and separate public-host privacy architecture. Active ML needs plaintext;
administrators/malware/crashes remain threats. Tests and audits reduce known risks,
not a guarantee that every attack/device is safe. Browser extensions/OS-injected
content are not controlled by application CSP.
