# Threat model, complexity and performance

## Scope

This is a private single-user loopback application, not a public multi-tenant service or an OS sandbox. Threats considered: hostile ZIP/JSON/raster/model inputs, accidental private-data publication, cross-site requests, unsafe executable model loaders, queue/compute exhaustion, misleading ML validation and credential leakage. A compromised local machine, hostile selected Python executable, concurrent filesystem attacker or unknown model bias is outside the protection offered here.

Exact Host/Origin checks, per-process bearer authorization before parsing and an 8 MiB request cap protect API inputs. Responses use no-store, CSP, no-referrer, frame denial and nosniff. User/provider text enters the UI through text nodes, never interpolated remote HTML. Only an ephemeral session token is kept in tab session storage; it is removed from the URL fragment after entry. The provider callback instead requires one-use OAuth state. No OAuth password/secret/token is accepted in the UI or committed to disk.

Import validates all ZIP entries before extraction, rejects raw/canonical traversal and links, bounds expanded size/count/compression, limits decoded pixels/bytes and strips EXIF. Atomic staging preserves original sources and refuses existing output directories. AI-origin labels stay separate; conflicting duplicates cannot bypass quarantine. Fingerprints and hashes catch later dataset/checkpoint/base changes.

Model classes are fixed; safe tensors are required, arbitrary executable/pickle files forbidden. Safe tensors reduce deserialization risk but do not imply honest weights, correct output or immunity to resource exhaustion. Model file/architecture budgets and job deadlines supplement format checks. Shard paths and file types require explicit confinement. The CLI cannot bind publicly; selected worker arguments never become shell text. Workers omit common secret-bearing environment names, but this is best-effort hygiene, not a full process capability sandbox.

Dependency advisories are audited without blanket exclusions. During development PEFT 0.17 was incompatible with Transformers 5; PEFT 0.21.1 was tested instead. The initial Torch 2.11 CUDA environment required an older setuptools version, conflicting with a published packaging advisory. The new reference stack uses Torch 2.14 and patched setuptools, and Accelerate was upgraded to 1.15 to move beyond the affected versions in the published shard-loading advisory. The predecessor's environment was not modified. Exact audit results/versions belong in the validation report; no claim of permanent vulnerability freedom is made.

## Complexity and bounds

The DeviantArt connector only issues read operations after token exchange, but this does not restrict the token's provider-side capabilities. Live prompts advertised Sta.sh management even without an explicit `stash` scope. The UI warns about this wider permission boundary; account registration, account-access consent and training rights are separate approvals. See [connector setup](deviantart.md).

| Operation | Dominant work / memory |
| --- | --- |
| Directory/ZIP ingestion | O(total source bytes + N log N) with sorted fingerprint; one bounded raster at a time plus O(N) metadata. N ≤ 10,000 unique images; folder traversal ≤ 40,000 entries per source. |
| Pixel deduplication | Hash set/dictionary O(1) average lookup per image; pixel hashing O(decoded pixel bytes). |
| Batch training | O(S × model forward/backward work at B × H × W); only a batch plus at most 16 held-out tensors, parameters/optimizer/EMA retained. Max 10,000 steps, batch 32, resolution 128 and explicit wall budget. |
| Native inference | Roughly O(S × (2 + 2R) × A × C²) for fixed convolution kernels; R ≤ 4 regions. Internal dimensions are capped to learned-scale work, then output is resampled. Masks do not create semantic understanding. |
| Checkpoint/base verification | Streaming O(file bytes); base fingerprint sorts bounded filenames and does not retain all model weights in a byte buffer. |
| SQLite list/lookup | Exact composite-key indexed lookup; newest-first result sets bounded to 100. Connections commit/rollback and close promptly. |
| Website sample import | O(entries + downloaded bytes), ≤96 inspected entries, pages≤24 entries, 1 MiB decoded API JSON, 20 MiB/4,194,304 pixels per raster, five-minute overall budget. |

Big-O describes scaling, not measured latency, quality or peak GPU allocator reservations. Report actual elapsed time, throughput, image counts, learned resolution, parameter count and **peak allocated** CUDA bytes where available. Allocated bytes are not total GPU process memory/reserved VRAM. Compare measurements only with matching hardware/version/batch/resolution/seeds. CI's small native and LoRA tests validate mechanics; a noise-MSE reduction is not an FID score, evidence of broad prompt adherence or fairness/safety evaluation.

## Release checklist

Run contract/property/queue/provider tests, real native/resume/edit/LoRA tests, strict UI build, source-index check, browser accessibility/mobile tests, real browser-worker scenario, dependency compatibility/audits and native package build. Inspect real synthetic outputs and screenshots. Confirm Git excludes runtime/data/credentials/models and stage only reviewed source/docs/public evidence. Check every required GitHub job at the final commit. Live website authentication and native platforms not actually exercised remain explicitly unverified.
