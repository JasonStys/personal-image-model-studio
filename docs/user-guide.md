# A complete local workflow

1. Connect to the private local session. Open Datasets & glossary and create the owned synthetic dataset. Inspect its total/flagged counts.
2. Select that dataset under Train & models. Start a native model at 32 learned pixels, batch 16, learning rate 0.001 and a bounded step/time budget. Tiny CPU/CI runs validate mechanics; thousands of GPU steps are more useful for the limited shape domain.
3. Watch job progress or cancel explicitly. A completed model displays measured train/held-out image counts, before/after denoising loss and throughput. Noise-prediction MSE is not a semantic quality score.
4. Select the model under Compose & generate. Try `red circle on white background`, seed 2026, 50 DDIM steps, guidance 2. A 128/256px display is enlarged from the learned resolution, not a high-resolution model.
5. Experiment with `(red:1.8)` or independent negative/style/tag fields. Unknown words and truncation are reported. Native vocabulary comes from your captions, so a shape-only model will not understand a broad photographic prompt.
6. Upload a source and a same-size grayscale mask. White pixels allow edits; black pixels preserve the fitted source. Use Expand with dimensions at least as large as the source to preserve its original-size center. Image-to-image Edit intentionally changes source pixels; it is not a conservation mode.
7. In History & feedback, assign a human score and notes. Save feedback separately from generating a revision. Use notes to populate an explicit revision, review the prompt and press Generate yourself. Latest opt-in allows a feedback ZIP; a later opt-out blocks export. Generated images remain AI-origin and ordinary training still excludes them.
8. Download a private job report. Reports may contain prompts/private paths; do not upload them automatically. Public validation evidence uses only owned synthetic data.

## Your datasets

Directories/ZIPs may contain PNG/JPEG/WebP/BMP, same-stem UTF-8 `.txt` captions and optional JSON metadata. JSON fields: `caption`, `tags` (list), `origin` (`human`, `synthetic_procedural`, `ai_generated`, `ai_assisted`, `unknown`), `name`, `artist`, `license`. Captions override a metadata caption when a `.txt` exists. The operator must confirm rights; this checkbox is not a substitute for reviewing the source licenses.

Empty captions are retained but not trained. AI-origin labels/tags quarantine records. Conflicting duplicate pixel captions/origin abort the entire import, leaving original sources untouched. At least eight unique captioned training images and two held-out images are required. Large ZIPs, links, encrypted members, traversal, executable content, extreme compression, oversized rasters and malformed metadata fail before publication.

Glossary definitions include `definition`, `source`, `reviewed`. They are editable dataset-local notes, not automatically researched facts or a second language model. Keep definitions short, cite your reference and review them yourself.

## Pretrained and LoRA

Register a local exported **classic StableDiffusionPipeline** directory with safe tensors and an authorization/license note. No downloads occur during worker loading. Fixed components/schedulers are validated, custom Python/pickle files rejected and unsupported architectures reported. Supplied safety-checker flags prevent publication. A model without a checker is not advertised as safe for unrestricted use.

Select LoRA mode, its registered base and approved datasets. The worker optimizes attention adapters, saves safe weights, metrics and a base-file fingerprint, then registers the adapter. It requires the unchanged original base directory for generation. Adapter training does not include semantic held-out evaluation or optimizer-resume state; inspect generated samples yourself before accepting it.
