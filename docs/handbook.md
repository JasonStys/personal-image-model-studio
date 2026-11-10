# Personal Image Model Studio handbook

By Jason Stys.

Review authorized datasets for caption, provenance, split and integrity evidence; inspect bounded cross-split similarity candidates with private thumbnails and export exact reports before training.

Helps users investigate training inputs without treating similarity, declared rights or sample counts as proof of data or model quality.

## Read the documentation

| Edition                                                      | Audience and contents                                                                                              |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| [project-guide.docx](reports/project-guide.docx)             | User and developer guide: purpose, current usage, design, boundaries and source references.                        |
| [validation-review.docx](reports/validation-review.docx)     | Reviewer edition: exact tested baseline, observed workflows, dated local results and remaining limits.             |
| [validation-evidence.xlsx](reports/validation-evidence.xlsx) | Two filterable Excel Tables for observed workflows and test-source inventory, with recalculating outcome formulas. |

The editable Markdown remains the maintenance source. The Word files are readable editions, and the workbook is an evidence index rather than a test runner. See [publication identities and review](reports/publications.json) and the [documentation refresh record](reports/documentation-refresh-2026-11-09.md).

## Current usage and help

[README quick start](../README.md) is the entry point. Use the project-specific guides below before changing inputs, operating modes or deployment assumptions.

### Usage and operations

- [dataset review](dataset-review.md)
- [releases/v0.2.0](releases/v0.2.0.md)
- [releases/v0.3.0](releases/v0.3.0.md)
- [user guide](user-guide.md)

### Design and contracts

- [adr private local](adr-private-local.md)
- [architecture](architecture.md)
- [research](research.md)

### Security and validation

- [security and performance](security-and-performance.md)

## Historical results and reproduction

The reviewed source is [`0d9aa0a6733198325593ffc30cef8358125063d7`](https://github.com/JasonStys/personal-image-model-studio/tree/0d9aa0a6733198325593ffc30cef8358125063d7). The observed functional workflow baseline is `0d9aa0a6733198325593ffc30cef8358125063d7`; those observations are recorded at `2026-11-10T07:59:19.060757+00:00`. They do not certify an unrun later revision.

- [Detailed recorded validation](reports/practical-workflows-2026-11-09.md)
- [Current Actions](https://github.com/JasonStys/personal-image-model-studio/actions) records later integration checks separately.
- Preserve dated measurements and follow the existing testing guide to reproduce them; a test-source inventory alone does not establish execution.

## Practical boundaries

- Integrity and similarity inspect at most 64 eligible images, 32 MiB encoded bytes and 16,777,216 decoded pixels; only 32 candidate pairs are shown, with omissions explicit.
- Grayscale hash matches are candidates, not proof of leakage, semantic quality or AI origin. Rights and provenance labels are operator declarations, not legal verification.
- The compact native model is not a general photorealistic generator. CPU downloads support native models only; compatible Stable Diffusion/LoRA imports need the explicitly configured full source/runtime.
- One unlocked local engine trusts the OS and active service. CPU downloads are unsigned portable applications, not a public hosted service or native mobile installation.

## Maintaining these editions

Update the editable usage/design/test documents first. Rebuild and visually review every Word page and workbook tab before replacing an edition; verify the exact binary digests and evidence source in publications.json. Keep account data, logs with secrets, installed-app state and private test stores out of documentation. Source and release assets retain their existing security and licensing boundaries.
