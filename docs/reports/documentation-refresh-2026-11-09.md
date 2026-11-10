# Documentation refresh — 2026-11-09

By Jason Stys.

This documentation-only edition describes source `0d9aa0a6733198325593ffc30cef8358125063d7`. It does not change application behavior, accounts, private data, installers or published releases.

## Published editions and completed review

| File                                                 |  Bytes | SHA-256                                                            | Reviewed scope                                                                                                                      |
| ---------------------------------------------------- | -----: | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| [project-guide.docx](project-guide.docx)             | 230003 | `bf4ef35277c63bd29f8ff8204421a8cd5a487948486705ea029c706188cd30ad` | 5 pages, each viewed individually                                                                                                   |
| [validation-review.docx](validation-review.docx)     |  46835 | `ec85862c9bd441205872d7cc4ae06dfe2917c5b71d14109a6ce5aec59c429c7f` | 7 pages, each viewed individually                                                                                                   |
| [validation-evidence.xlsx](validation-evidence.xlsx) |   7415 | `d1d4d9195d4e6071ca90c2b0ffd3989a9d9adeb9c4317823c26960d81212831e` | Both tab previews; two actual Excel Tables/autoFilters; four formulas; failure-change/restore recalculation and zero formula errors |

Word review checked plain black titles, readable pagination, whole table rows, source references, practical limits and absence of clipping or overflow. Render receipts were matched to the current DOCX digest before approval. Workbook review inspected both tab previews and actual exported Table/autoFilter elements; recalculated success/failure summaries were compared independently with workflow metadata. Static previews do not draw Excel dropdown arrows; the exported workbook contains the actual filters.

## Evidence and change boundary

- Functional baseline: `0d9aa0a6733198325593ffc30cef8358125063d7`.
- Workflow observation: `2026-11-10T07:59:19.060757+00:00`; exact run URLs and source identities remain in [publications.json](publications.json).
- Local document-package validation verifies exact copied bytes, Office ZIP integrity, approved page/tab identities and internal documentation links. Repository-specific documentation and source-policy commands are run separately and recorded in the integration handoff.
- Source/index metadata is regenerated using the repository’s existing tools. Existing privacy, security, coverage and workflow gates are retained.
- PR and later main workflows must pass independently. This record does not claim future or unrun integration CI success.

## Interpretation

The Word files document the cited source; dated source reports retain their original execution scope. A passing workflow is distinct from completed analysis with zero findings, and neither establishes production suitability. The Excel source inventory is not a per-test execution report. Checksums identify exact bytes, not a signature or publisher attestation.

Use the [handbook](../handbook.md) to choose usage, design, security and test documentation. Keep editable Markdown and reviewed editions together; do not replace historical measurements with undated claims.

## Local integration checks

The copied editions passed exact approved-byte/Office ZIP/source/link validation.
Ruff passed across studio/scripts/tests; all 57 generated source maps are current.
Three real metadata-index CLI regressions (missing directory, permission failure and
I/O failure) passed. Strict TypeScript and production Vite build passed; the existing
large-chunk warning remains. These documentation integration checks are separate from
the cited baseline's actual hosted Validate/full-main CodeQL results and do not claim
a fresh training run, installed application acceptance or future PR/main success.
