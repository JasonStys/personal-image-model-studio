# Architecture and decisions

The browser/native shell talks to the same authenticated loopback API. SQLite stores compact metadata; images, datasets and safe checkpoints remain private filesystem artifacts. One subprocess runs ML work at a time. Provider OAuth runs in a separate fixed-endpoint connector and never becomes a generic credential-bearing crawler.

```text
TypeScript UI / native WebView
        ↓ private bearer + exact Host/Origin
FastAPI → SQLite metadata + separate quarantine database
        ↓ bounded queue, trusted module, no shell
ML worker → reviewed dataset → native model or local SD/LoRA
        ↓ verified terminal artifacts
Image/history/report → human feedback → explicit revision/export
```

## ADR 001: language responsibilities

Python is appropriate for PyTorch/Diffusers training, Pillow image processing, typed API contracts and provider HTTP integration. TypeScript supplies strict browser contracts and portable interaction. HTML/CSS implement semantic, responsive views; SQL provides parameterized local indexing. Additional languages are not added solely to increase the portfolio language count: unnecessary cross-language runtime boundaries would make this application harder to maintain and secure.

The interface is a small vanilla TypeScript application rather than a general frontend framework. Its production bundle is measured by the build, with no CDN scripts or third-party telemetry. A native WebView reuses the interface rather than duplicating its controls. ML dependencies are separate from the lightweight portable shell; this makes updates and CPU/GPU selection explicit but requires a one-time runtime setup.

## ADR 002: fresh native model versus a pretrained adapter

A compact **pixel-space**, text/time-conditioned UNet is initialized from scratch. A vocabulary and embeddings are learned from training captions, with no downloaded base weights. This makes a meaningful offline training demonstration affordable. It is not the older prototype's latent model format and is not a shortcut to broad artistic/photographic knowledge. Checkpoints support 32/64/128 learned resolutions, fixed supported channel counts and a maximum 4,096-word vocabulary. Inference enlargement is resampling, not learned super-resolution.

Classic single-encoder Stable Diffusion is a distinct optional path. It uses an explicitly supplied licensed local safe-tensor export; LoRA trains attention adapters while the VAE/text encoder/base weights stay frozen. Adapters include a full base-file fingerprint. They do not contain the base weights or optimizer-resume state. Random fixture SD components prove API/optimization/reload compatibility, not artistic quality.

## ADR 003: private trusted workers, not arbitrary execution

Workers execute only this repository's modules with bound JSON, a private log and cancellation file. Eight active/queued slots, one worker, compute budgets and a 15-second cancellation grace prevent unbounded job admission. Parent deadlines include 180 seconds for import/loading overhead. A forced stop does not fabricate a checkpoint; cooperative training after at least one optimizer update can publish a recoverable checkpoint. Restart marks unfinished work interrupted; it never silently repeats training.

The worker is **not an OS sandbox**: local model/runtime choices must be trusted. Frozen desktop packages ship worker source separately so an explicitly selected Python runtime can import the app's own modules. No executable pipeline code or pickle weights are accepted.

## Storage and versioning

`studio.sqlite` stores bounded model/dataset/image/job/policy/runtime records and human feedback. `quarantine.sqlite` stores explicit AI-origin metadata separately. Raster examples are normalized PNGs with hashes; dataset fingerprints bind captions, origin and split. Duplicate pixels with conflicting captions/origin abort import instead of allowing the first record to hide AI provenance. Multi-source datasets use one deterministic pixel-hash split.

Native `model.json` and two `.safetensors` files bind fixed architecture, vocabulary, model/EMA, optimizer tensors, RNG, settings, data fingerprint and measurements. Atomic JSON publishes complete metadata last. Integrity hashes detect later changes; they are not a cryptographic assertion that an unknown publisher is trustworthy. Back up the entire private workspace when the app is stopped, not only its SQLite main file while WAL writes are active.
