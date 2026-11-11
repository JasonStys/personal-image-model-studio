# Native application ownership and delivery

Personal Image Model Studio is authored by [Jason Stys](https://github.com/JasonStys).
The native application owns the original private account service and opens the
complete TypeScript interface in a browser. Its window provides **Open application**,
**Help and privacy**, **Runtime notices** and **Quit application**. Closing a browser
tab leaves the application running. Quit and window Close request normal draining;
the window and exclusive profile ownership remain until the service thread completes.
No HTTP shutdown endpoint is added.

## Accounts and compatibility

Existing account paths, SQLite schema and authenticated vault format are retained.
Keep a complete stopped-data-directory backup and the old app before upgrading.
Do not delete recovery files to repair startup. The native app refuses redirected
profile ancestors, junctions, symbolic links, multiply linked fixed files and
profiles inside program resources before opening accounts or changing permissions.
Ordinary SQLite journal/WAL/shared-memory files remain permitted. Active and
encrypted recovery trees are checked with bounded iteration; refused data is preserved.

The profile lock binds an actual regular-file descriptor and nonblocking OS lock.
A competing instance does not append to or rewrite it. These static layout and
concurrency checks assume a trusted OS owner. They do not isolate an unlocked
workspace from malicious software running as that user or administrator.

The CPU build retains real native diffusion training, sampling, encrypted persistence
and dataset-quality review. Classic Stable Diffusion and LoRA remain available in
the full source ML environment with an explicitly trusted runtime; they are not
bundled CPU engines. No pretrained weights, artwork, provider credentials or personal
data enter a package. Small synthetic runs establish execution, not image quality.

## Runtime and package identity

Native builds require final CPython **3.14.10**, coherent Python/UI versions and
clean source. Local dirty candidates are labeled and forbidden in CI. The Windows
Python DLL is pinned to the reviewed SDK digest. Actual Tcl/Tk patch levels, the
processed Python library and complete bounded UI/license/notice inventory are
bound to embedded `NATIVE_SOURCE.json`. macOS load-path repair is measured in a
second packaging pass while retaining the SDK digest; identity checks are not waived.

The five-member archive contains the executable, authored license, installation
guide, source manifest and actual runtime/dependency notices. Its sidecar covers
both archive and executable. Notice collection requires all 13 isolated cases,
including actual Tcl/Tk terms and missing/ambiguous/mismatched-notice failures.
Python/TypeScript ASTs generate source headers and `docs/code-map.json`.

`requirements-native.lock` pins the CPU/freezer graph and allowed distribution
hashes. The universal resolver compares only official PyPI and PyTorch CPU indexes
to select pinned platform versions. Installation requires a listed hash. CUDA and
global runtime installation are excluded. Vendor telemetry is disabled in this
app process before Hugging Face imports, including embedded workers. No system-wide
setting or explicitly consented provider capability is changed.

## Acceptance and release

1. Preserve original source, full ML/LoRA, browser, accessibility, dependency and
   desktop checks; add current native gates.
2. Build clean native packages on Windows, Linux and macOS. Use actual displays,
   including Xvfb for Linux native controls.
3. Extract only the five exact regular members with byte/type/permission/checksum
   bounds. Compare actual CArchive embedded identity with the archive sidecar.
4. Run all **12 original compiled CPU checks**, including real optimization, learned
   PNGs and encrypted reopening, and all **six original private/ML Chromium journeys**
   against the extracted executable. Original assertions and deadlines remain;
   only startup and screenshot destinations are rebound. Skips, retries and forced
   cleanup cannot authorize release.
5. Require successful exact-current-main source/native/CodeQL runs, processed
   analyses for all three configured languages, empty raw findings and no open
   alerts. Create/resume only that immutable unpublished draft; verify numeric
   release identity and provider asset hashes. There is no clobber or automatic
   publication operation.
6. Independently download and validate installed bytes before publication. Ordinary
   profiles and provider stores remain separate from synthetic acceptance.

No automatic full-package Actions upload is added. Existing optional small artifacts
remain owner-controlled. Unsigned portable packages are not code signing, notarization
or universal device certification.

## File responsibilities

| File | Responsibility |
| --- | --- |
| `studio/native_desktop.py` | Verify resources and construct the owner around the original private app. |
| `studio/native_host.py` | Prebound socket, non-daemon service thread, visible controls and completion gate. |
| `studio/native_profile.py` | Bound profile admission and refuse aliases before account initialization. |
| `studio/native_identity.py` | Check source/runtime, complete UI and actual terms before profile access. |
| `studio/native_privacy.py` | Process-only vendor opt-out before imports. |
| `scripts/native_package.py` / `native_notices.py` | Clean packaging and actual dependency/runtime terms. |
| `scripts/native_distribution.py` | Strict archive and checksum contracts. |
| `scripts/native_acceptance.py` | Full extracted-package validation. |
| `scripts/test_native_browser.py` | Original browser journeys against the compiled app. |
| `scripts/native_release_guard.py` | Exact-main security and immutable draft upload gates. |

Profile validation is linear in bounded entry count. Hashing is linear in admitted
bytes; archive copying streams bounded chunks. ML uses the existing bounded worker
process, and service work does not manipulate native widgets from background threads.


The Runtime notices window includes original crypto/Rust third-party terms.
At build time `scripts/runtime_terms.py` checks the actual installed cryptography
wheel's complete normalized provider inventory and compiler marker separately
on every OS, then retains the captured original 62 crate terms and Rust library
copyright document. It does not fetch code or terms during a build. An unknown
wheel inventory/compiler stops packaging for review; the Windows binary hash
does not authorize another platform. This conservative notice inventory is not
a legal certification or a claim that every provider component is linked.
