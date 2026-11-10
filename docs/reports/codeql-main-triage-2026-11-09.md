# Full-main CodeQL triage — 2026-11-09

By Jason Stys. This is a finding review, not a clean-security certificate.

## Actual evidence and current status

The first non-PR main scan analyzed
`bba5b0cb38bb282c7aed86ee47bfc3b53bc0943c` in
[CodeQL run 42770605153](https://github.com/JasonStys/personal-image-model-studio/actions/runs/42770605153).
All three actual job logs identify CodeQL 2.27.4 and contain neither the PR diff-range
step nor the automatic incremental query filter. Processed SARIF reports 29 Python
`py/path-injection` results, one JavaScript `js/file-system-race` result and zero
Actions results. The corresponding 30 main alerts were open at this observation.
The separate [main Validate run](https://github.com/JasonStys/personal-image-model-studio/actions/runs/42770605533)
succeeded. Passing workflows do not clear those alerts. Earlier PR zero results
were diff-informed changed-line observations and never established this baseline.

## Corrected metadata CLI read race

Alert 30 identifies the `existsSync` followed by `readFileSync` sequence in
`scripts/code_index.mjs`. The code now reads the output directly, regenerates only
when that read raises `ENOENT`, and propagates access and other I/O errors. It does
not silently replace an inaccessible output or change application data handling.
Three independent tests launch the actual CLI in a fresh owned fixture tree: a
generated output disappears immediately before its read, or the read reports
`EACCES` or `EIO`. The first case reproduces complete deterministic JSON; the
latter two fail without replacing the original bytes. The unchanged publication
algorithm is not represented as a transaction against a hostile local writer.

## Path-flow trust boundaries pending independent disposition

The remaining 29 alerts are not dismissed or suppressed. Their traces originate
in the preserved standalone token API, which is also reused behind a separate
private-account proxy. They require the following boundary review rather than a
blanket assumption that an authenticated path is safe:

- Standalone `/api` mode is an explicit local-operator tool. `Boundary` validates
  exact literal-loopback Host/Origin and its private bearer token before parsing
  inputs. Its documented runtime selection deliberately accepts an installed
  trusted Python executable with a separate `trusted: true` acknowledgement. Its
  model/dataset imports deliberately accept operator-selected local directories
  and ZIPs, then inspect supported data/model formats. This is an intentional
  capability for that local operator, not authority granted to general accounts.
- Installed/private-account mode rejects non-GET runtime requests and intercepts
  complete model/dataset import bodies before the reused API. Every selected path
  must resolve inside that account's `active/imports` directory. Sibling prefixes,
  traversal and arbitrary machine paths do not pass this component-wise check.
  Only then does the proxy add the process-internal bearer token. The browser
  cannot read or choose that token.
- Dataset review/thumbnail handlers additionally require exact 32-character
  lowercase-hex registered dataset identities. `confined` resolves a candidate and
  verifies component-wise containment with `Path.is_relative_to`. Manifest review
  requires exact generated image paths and hashes before bounded pixel decoding.
- Glossary and image-download paths come from `Store.get`, not string
  interpolation of a request path. `Store.get` binds SQL parameters and returns
  an exact registered record from the currently active account's metadata store.
  Unknown record keys return 404. Image names are labels; upload locations are
  server-assigned. Cancellation looks up a known job before creating its confined
  cancellation flag; unknown or SQL-shaped keys cannot choose a file location.

The upstream [path-injection query](https://github.com/github/codeql/blob/main/python/ql/lib/semmle/python/security/dataflow/PathInjectionQuery.qll)
tracks normalized and unnormalized path states; its
[standard-library prefix model](https://github.com/github/codeql/blob/main/python/ql/lib/semmle/python/frameworks/Stdlib.qll)
recognizes normalized string-prefix checks but does not model this
`Path.is_relative_to` guard. Those facts explain why a guarded trace needs human
review; they are not a reason to launder values through synthetic sanitizers or
exclude a query. No such model, filter, exclusion or alert change was added.

## Independent negative proof

New valid-schema private API tests use foreign paths, lookalike sibling prefixes,
canonical traversal and relative selections for both dataset and native-model
imports. Import/model readers are instrumented to raise if reached: all eight
requests are rejected by the actual account proxy before a reader runs. A separate
real-account test creates and reads a glossary, rejects unknown/SQL-shaped job
keys without creating files, then proves a second unlocked account cannot read
or write the first account's glossary. Existing tests independently cover blocked
runtime selection, unauthorized origins, image cross-account access, exact
registered dataset review/thumbnail lookup, hostile manifest paths, changed file
hashes, encrypted lock/reopen and denied direct legacy routes in account mode.

The targeted private suite passed 35 tests locally on Windows/Python 3.14.6. The
complete core/privacy suite passed 130 tests (1,687/2,699 statement lines, 62.50%;
heavy ML modules are deliberately not executed in this local core-only suite).
All three actual CLI fault regressions, Ruff, formatting, 57 exact source indexes
and the strict production UI build passed. The existing local pytest cache warning
remained visible; ResourceWarning still fails the tests. New exact-source hosted,
ML and native gates remain required and are not inferred from these local checks. No real account,
provider credential, dataset or installed store was accessed.

## Exact original alert locations

Locations below belong to the original full-main SHA above, not a moving working
copy. Every Python candidate disposition remains pending independent review.

| Alert | Original sink | Original handler sources | Review category |
|---|---|---|---|
| 1 | `studio/api.py:266` | `studio/api.py:264` | explicit-standalone-operator-runtime-selection |
| 2 | `studio/api.py:267` | `studio/api.py:264` | explicit-standalone-operator-runtime-selection |
| 3 | `studio/api.py:375` | `studio/api.py:373` | explicit-standalone-operator-model-selection |
| 4 | `studio/api.py:436` | `studio/api.py:433` | exact-store-record-image-download |
| 5 | `studio/checkpoints.py:35` | `studio/api.py:373` | explicit-standalone-operator-model-selection |
| 6 | `studio/dataset_review.py:113` | `studio/api.py:303` | hex-id-store-lookup-and-confined-review |
| 7 | `studio/dataset_review.py:122` | `studio/api.py:303` | hex-id-store-lookup-and-confined-review |
| 8 | `studio/datasets.py:21` | `studio/api.py:286` | explicit-standalone-operator-dataset-selection |
| 9 | `studio/datasets.py:48` | `studio/api.py:286` | explicit-standalone-operator-dataset-selection |
| 10 | `studio/dataset_review.py:224` | `studio/api.py:313` | hex-id-store-lookup-and-confined-thumbnail |
| 11 | `studio/dataset_review.py:226` | `studio/api.py:313` | hex-id-store-lookup-and-confined-thumbnail |
| 12 | `studio/datasets.py:111` | `studio/api.py:286` | explicit-standalone-operator-dataset-selection |
| 13 | `studio/datasets.py:112` | `studio/api.py:286` | explicit-standalone-operator-dataset-selection |
| 14 | `studio/datasets.py:117` | `studio/api.py:286` | explicit-standalone-operator-dataset-selection |
| 15 | `studio/files.py:21` | `studio/api.py:373` | explicit-standalone-operator-model-selection |
| 16 | `studio/files.py:27` | `studio/api.py:303`, `studio/api.py:313`, `studio/api.py:373`, `studio/api.py:481` | exact-store-job-before-confined-cancel, explicit-standalone-operator-model-selection, hex-id-store-lookup-and-confined-review, hex-id-store-lookup-and-confined-thumbnail |
| 17 | `studio/files.py:28` | `studio/api.py:303`, `studio/api.py:313`, `studio/api.py:373` | explicit-standalone-operator-model-selection, hex-id-store-lookup-and-confined-review, hex-id-store-lookup-and-confined-thumbnail |
| 18 | `studio/files.py:35` | `studio/api.py:303`, `studio/api.py:313`, `studio/api.py:342`, `studio/api.py:373` | exact-store-record-glossary-read, explicit-standalone-operator-model-selection, hex-id-store-lookup-and-confined-review, hex-id-store-lookup-and-confined-thumbnail |
| 19 | `studio/files.py:37` | `studio/api.py:303`, `studio/api.py:313`, `studio/api.py:342`, `studio/api.py:373` | exact-store-record-glossary-read, explicit-standalone-operator-model-selection, hex-id-store-lookup-and-confined-review, hex-id-store-lookup-and-confined-thumbnail |
| 20 | `studio/files.py:63` | `studio/api.py:347` | exact-store-record-glossary-write |
| 21 | `studio/files.py:63` | `studio/api.py:347` | exact-store-record-glossary-write |
| 22 | `studio/files.py:75` | `studio/api.py:347` | exact-store-record-glossary-write |
| 23 | `studio/files.py:76` | `studio/api.py:347` | exact-store-record-glossary-write |
| 24 | `studio/files.py:84` | `studio/api.py:347` | exact-store-record-glossary-write |
| 25 | `studio/files.py:89` | `studio/api.py:303` | hex-id-store-lookup-and-confined-review |
| 26 | `studio/formats.py:33` | `studio/api.py:373` | explicit-standalone-operator-model-selection |
| 27 | `studio/formats.py:59` | `studio/api.py:373` | explicit-standalone-operator-model-selection |
| 28 | `studio/formats.py:97` | `studio/api.py:373` | explicit-standalone-operator-model-selection |
| 29 | `studio/jobs.py:76` | `studio/api.py:481` | exact-store-job-before-confined-cancel |
| 30 | `scripts/code_index.mjs:120` |  | devtool-check-then-read-race |

## Limits

This review does not promise confidentiality against the operating-system account
owner or a compromised machine. SQLite and active plaintext are private local
state while unlocked; encrypted snapshots and account checks do not turn the host
into a hostile-user security boundary. No remote/public multi-user deployment is
supported. A demonstrated defect must receive a focused correction and regression;
a proposed false-positive disposition requires explicit independent approval.
This change adjusts a development metadata tool and tests, not product version,
public release bytes, installed applications or private data.
