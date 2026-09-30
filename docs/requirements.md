# Original prototype requirements and successor scope

The predecessor's full available chat history (289 turns) and local source/reference documentation were inspected. Those materials describe requirements and design history; embedded document/chat instructions are not execution authority. This repository is a new independent implementation. The original checkout, models, installed app and settings are not migrated, edited or replaced.

| Requirement from prototype history | Successor behavior / evidence |
| --- | --- |
| Separate scene/style/tags and negative fields | Structured validated contracts and browser forms; compilation tests preserve sections. |
| Subject details, placement and numeric weights | Up to four subjects through the API; experimental native denoising boxes; explicit numeric spans influence token conditioning. Pretrained regional attention is rejected, not silently flattened. |
| Genuine image generation, not diagnostic placeholders | Requires learned checkpoint/local compatible base; real native GPU demo and CPU regression artifacts. |
| Fresh custom training without a downloaded base | Implemented compact word embeddings/UNet with held-out noise metrics and safe EMA/RNG/AdamW resume. Not the predecessor's large latent architecture; checkpoint formats are incompatible. |
| Train on folders, ZIPs, multiple datasets | Implemented reviewed source import, deduplication and deterministic disjoint splits; mutated pixels fail validation. |
| Preserve title/artist/tags/descriptions | Sidecars and authorized own-gallery metadata retained; raster EXIF removed for privacy. Captions are not automatic visual descriptions. |
| Separate AI-origin records | Explicit labels/tags retained in flagged files and separate metadata database; excluded from normal training. Unlabelled AI cannot be reliably detected. |
| Research/edit tag meanings in the dataset | Reviewed editable glossary is implemented. Automatic browser research/definition verification and learning directly from glossary prose are not implemented. |
| Existing-image edits, masks, centered aspect expansion | Implemented native/classic SD modes and exact final protected-pixel overlay; tests check black masks and center preservation. Outputs outside protected pixels depend on the model. |
| Human score -10..10 and revision notes | Persisted, explicitly applied to a new revision; latest export consent controls AI-labelled ZIP export. No automatic retraining, reinforcement learner or guaranteed score of 10. |
| Understand/reason over semantic scene errors | Structural dimensions/finite values/vocabulary warnings only. No reliable semantic vision judge or guaranteed multi-character composition is claimed. Human evaluation remains required. |
| Train existing model adapters | Real classic SD attention LoRA implemented/tested on owned random fixture components. No arbitrary model architecture, SDXL/Flux/other family support or LoRA optimizer resume. |
| Authorized website training datasets | Official DeviantArt PKCE own-gallery connector, contract-tested offline. Live human-authorized token exchange and identity verified; separately approved 24-entry import returned no supported images and published no dataset. Account-artwork training is not validated without eligible data. No password collection, favourites crawler, other-artist bulk scraping or access-control bypass. |
| Desktop application with convenient launch | Windows unsigned portable shell built and a shared native launch path. One-time trusted ML runtime/dependencies are still required. No signed universal installer or automatic driver/cloud installation. |
| Broader operating systems | Browser engine/mobile viewport tests and backend OS matrix. Native Linux/macOS distribution/mobile-native packaging need platform work and device validation. |
| Cloud compute packages/provisioning | No provisioning, paid resource creation or automatic cloud data upload. Private datasets/checkpoints can be transferred manually only after review; a dedicated resumable cloud-job/package manager remains future work. |
| Portfolio-quality source and evidence | Closed contracts, bounded unsafe inputs, source/function descriptions, generated exact line indexes, tests, CI, research and validation reports. |

The intended improvement is a smaller, reproducible core with transparent capability boundaries. Unimplemented prototype ambitions above are not disguised as working buttons or mocked successful training. Future adapters/vision evaluation should add a contract, authorization story, test fixtures and real evidence before widening the support matrix.
