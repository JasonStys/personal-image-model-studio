# ADR-001: local authenticated image accounts and encrypted locked workspaces

Status: accepted for local-only 0.2. Date: 2026-10-12. Author: Jason Stys.

## Context

Real diffusion training/inference needs pixels and weights in the ML worker.
Sending those to a shared host conflicts with the request to keep them private
from the website operator. Hosting is explicitly deferred. Existing developer
mode has one global plaintext workspace and a tab bearer token; it is not an
account system and must not be exposed publicly.

## Decision

Provide a distinct loopback-only account service, browser sign-in/help, scrypt
login hashes, HttpOnly cookies, exact Host/Origin/CSRF checks and a separate vault
phrase. Derive the vault key with browser WebCrypto and send the key only to the
user's trusted local worker service while unlocked. Encrypt locked workspace
archives with AES-256-GCM, authenticate before extraction, and never save keys.
Only one account can unlock the local ML engine at a time. Other signed-in
accounts cannot read its records or images. Browser-selected uploads are staged
within the active account; arbitrary filesystem paths and browser-selected
executables are forbidden in account mode. Explicit provider authorization stays
optional, account-scoped and memory-only; locking disconnects it.

The existing developer API/CLI and its old data remain separate and opt-in.
Do not silently migrate old workspaces, artwork, provider tokens or models.

## Options considered and trade-offs

Browser-only ML would remove a trusted local service but would not preserve the
Torch training, safe-tensor checkpoints and LoRA functions. A hosted GPU worker
would need plaintext and introduce operator access, hosting costs and additional
consent. Local per-account compute preserves actual ML with no hosting costs,
but cannot hide data from a compromised device or OS administrator.

Unlocked computations temporarily use plaintext files. An unexpected process/OS
crash may leave a protected recovery workspace until its owner unlocks and locks
again. Never erase an interrupted workspace merely to make the UI look clean.
OS disk encryption and a separate OS login remain important. File deletion is
not secure erasure. Crypto cannot prevent malicious application/runtime code.

Snapshot encryption costs O(S) bytes at an explicit save/lock or idle completed
operation; unchanged polling scans O(F) file metadata and does not re-encrypt
weights. Memory is bounded by streaming chunks, not model size. One unlocked
account and one serialized ML queue are intentional, not a scalable hosted SaaS.

## Validation and remaining gates

Test account recovery, expiry, CSRF/origin/body limits, two-account isolation,
wrong-key/tampered archives, safe ZIP paths, import confinement, interrupted
recovery, deletion, real training/generation, accessibility and packaged workers.
Document portable package signatures, CPU versus optional full ML runtimes,
backup limitations and creator contact. Public hosting needs a new architecture,
explicit approval and security/privacy review; no deployment is implied.
