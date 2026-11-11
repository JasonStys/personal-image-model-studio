# Native 0.3.1 development validation — 11 November 2026

Author: Jason Stys. **Development evidence:** final clean-source hosted checks,
independent installation, publication and a current illustrated guide remain pending.
No installed ordinary account or provider store was opened.

| Validation | Observed result |
| --- | --- |
| Original full source + ML | 238 current-tree tests passed, including actual native learning, classic model/LoRA, dataset review, accounts/recovery, native controls and final release/archive helpers. No source tests were skipped in this Windows full-ML run. |
| Ownership/profile/privacy/notices | 25 passed: real OS locking, four Windows junction placements, hardlink sentinels, exceptional listener cleanup, held HTTP draining and actual vendor opt-out ordering. The notice wrapper requires all 13 isolated cases. |
| Actual native controls | Five passed: Open fallback, Help reuse, notices, Quit, OS Close, scoped stdin Quit, retained real held request and released profile lock. |
| Compiled CPU candidate | All 12 original checks passed: real optimization, learned PNG, encrypted lock/reopen, actual normal exit 0 and closed listener. |
| Compiled browser candidate | All six original private/ML Chromium journeys passed, including real 20-step training, account isolation, browser vault-key derivation, unsafe ZIP/inert text handling, recovery/deletion, exact dataset review/export and stale selections. |
| Extracted complete archive | Exact five-member extraction, sidecar, CArchive identity and all 12 CPU/six browser journeys passed. The candidate is explicitly dirty and cannot authorize release. |
| Archive/draft boundaries | 66 passed for exact-source metadata, raw SARIF findings, immutable draft IDs, literal JSON notes, six-platform-asset identity, malformed ZIP/tar and ambiguous checksums. |

The current full run completed in 128.92 seconds with branch coverage recorded. The locked npm graph reported zero known advisories. Ruff, Prettier, TypeScript/Vite, all three original code-index regressions and exact AST maps passed. Hosted results remain pending.

## Failures investigated

- Five optional ML modules were absent in the first environment. A genuine Windows
  profile guard defect also appeared: cached `DirEntry.stat()` gives zero link-count
  metadata there. Each admitted member now uses actual path `lstat()`. Original
  interrupted recovery and the full suite passed after the fix and isolated full-ML
  installation. No recovery data was reset.
- A first notice build began before its dependency install completed. Mandatory
  PyInstaller metadata discovery failed and produced no package. After installation,
  `pip check`, all notice cases and the subsequent build passed.
- A browser attempt selected a cache for a different locked Playwright version;
  no browser launched. The exact 1.63 cache passed all six original journeys with
  no app change or deadline increase.
- The full suite also caught the previous release’s hard-coded 0.3.0 delivery assertion. It now requires coherent 0.3.1 metadata, retained historical notes and the new immutable draft guard, forbidding clobber and automatic publication.
- New native test fixtures initially had an incorrectly decoded expected title,
  a test route correctly rejected by private middleware, and an unsupported lock
  context-manager call. UTF-8 fixtures, an owned outer test handler retaining the
  actual account-manager lifespan, and explicit real lock close corrected those
  fixtures. Product access control was retained.

Failed and passing logs, SDK/package hashes, actual embedded identity and original
consumer hashes remain in private runtime evidence. The development binary predates
later test/documentation changes and is not relabeled as a final clean commit.
Two-step/20-step shape models establish learning execution and persistence rather
than general-purpose image quality. Full source LoRA tests do not imply a bundled
LoRA CPU engine. No password, vault phrase, token or ordinary user data is committed.

References: [Python directory metadata](https://docs.python.org/3/library/os.html#os.DirEntry.stat),
[Hugging Face environment settings](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables),
and [native architecture](../native-application.md).
