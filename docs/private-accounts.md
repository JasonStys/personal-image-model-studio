# Private local accounts, threat model and API — Jason Stys

## Trust and data flow

Browser → exact loopback account service → account-only workspace → one trusted
ML subprocess. The service is deliberately not a shared public GPU host. The
browser derives a key using PBKDF2-HMAC-SHA256/600,000 with a random 128-bit salt,
then sends the 256-bit key **only to its trusted local service**. The phrase itself
is not sent. This is different from browser-only E2EE: actual Torch computation
needs plaintext pixels/weights on the device. The worker never receives the key.

An idle snapshot streams a ZIP_STORED archive through AES-256-GCM with a fresh
96-bit nonce, 128-bit tag and fixed version/protocol AAD. Decryption authenticates
the whole archive before ZIP parsing/extraction. File count/bytes, link/traversal,
case-duplicate and special Windows names are checked. SQLite online backup copies
provide consistent idle metadata. Temporary files are owner-private and removed
on normal completion; crashes and hardware failure are not secure erasure.

Login passwords are scrypt N=2^17/r=8/p=1 with random 256-bit salts, a two-slot
hash semaphore and constant-time comparison. Missing users use a dummy hash.
Sessions/recovery codes are random 256-bit values stored only as SHA-256 digests.
Sessions expire after eight hours/30 minutes idle, with ten per account. Vault
idle timeout uses human activity, not passive workspace polling: ten minutes by
default, explicit 30-minute/two-hour options. Locking cancels owned active jobs.

HttpOnly/SameSite Strict cookies are scoped to `/private` with port-specific
names to avoid collisions between local instances. Secure-cookie/HTTPS public
hosting is not claimed: literal `127.0.0.1` HTTP is the only supported account
origin. Exact Host/Origin, one Host header, cross-site fetch denial and a custom
same-origin JSON mutation header are enforced before body parsing. CSP disallows
remote scripts/fonts, inline/eval scripts, objects and framing; every response is
no-store/no-referrer. Browser extensions and malicious installed software remain
outside this boundary. No admin plaintext read/backdoor API exists.

## Ownership, operations and limits

The cookie identifies an owner; request bodies never select the owner. Only one
account can unlock the engine at a time. Registered data is confined to that
account, even if another account guesses an image/model/job ID. Browser file
pickers upload only allowed data extensions into generated import batches.
The API cannot change the worker executable. A trusted alternate full runtime
requires a launcher flag/acknowledgement. No executable model code, pickle files,
remote pipelines or silent model downloads are accepted.

The default data directory is outside the repository/installation. POSIX mode
0700 or Windows root ACL grants protect it for its OS owner, SYSTEM/admins.
OS administrators and processes running as that OS user can access plaintext
during ML and memory. A modified app/runtime, weak phrase, device compromise or
crash can defeat privacy. Locked encryption protects passive stored archives,
not a malicious device. Use disk encryption, backups and patched software.

Limits: 8 GiB/20,000 files; metadata databases 32 MiB each; 6 GiB per selected
upload; 4 MiB ordered chunks; 8 MiB HTTP bodies; eight queued/running jobs;
1,000 requests per five minutes; 40 global and ten alias auth attempts per five
minutes; ten unlock attempts per owner per five minutes. No arbitrary filesystem
read routes are exposed. New accounts have no inherited examples; loading owned
synthetic examples/training requires explicit user actions.

Whole-archive save/lock costs O(S) streaming bytes plus O(F) directory metadata.
Unchanged polling scans O(F) metadata and does not re-encrypt weights. Memory is
O(chunk + F ZIP entries), not O(model size). Browser uploads encode only one
4-MiB chunk; encrypted downloads use native attachment streaming. Heavy ML is
serialized. These limits are appropriate for a local workbench, not hosted-scale
multi-tenant load. Queue deadlines, cooperative cancellation and parent PID plus
creation-time monitoring prevent deliberate orphan workers. No credentials are
in the worker's allowlisted environment and hub telemetry/downloads are disabled.

## Account API

All mutations require `Content-Type: application/json` and `X-PIMS-Request: v1`.
Errors do not echo secret input/large base64 bodies. `/health` returns only metadata
(an optional validation nonce correlates disposable tests, not authentication).

| Route | Purpose |
| --- | --- |
| POST `/private/register`, `/login` | Alias/password account creation or authentication. |
| POST `/private/reset` | One-use recovery; rotate login/recovery and revoke sessions, not vault key. |
| GET `/private/account` | Caller-only alias, salt/configured/unlocked state and capabilities. |
| POST `/private/unlock` | Browser-derived key/salt unlock; no persisted raw key. |
| POST `/private/activity` | Human-triggered timeout choice/renewal. |
| POST `/private/save`, `/lock`, `/logout` | Idle snapshot, seal/cancel/clear, or session revocation. |
| POST `/private/delete` | Current-password-confirmed live account/data deletion. |
| GET `/private/backup` | Caller-only encrypted archive attachment. |
| POST `/private/files`, PUT `/private/files/{id}` | Ordered, capacity-reserved account file staging. |
| `/private/api/*` | Existing actual dataset/model/ML/feedback methods, scoped to the unlocked owner. |
| `/oauth/deviantart/callback` | Explicit active connector's one-use state/PKCE flow; no automatic download. |

Login recovery cannot restore a lost vault phrase. Encrypted archive backups need
their account/key configuration; cold-back up the complete protected data root.
Account deletion is not disk secure erase or removal of old backup copies.
Independent penetration/security review, publisher signing, mobile native apps
and a public-hosted privacy architecture remain future gates, not certifications.

## Primary references

[OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html),
[session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
[Cryptography GCM](https://cryptography.io/en/stable/hazmat/primitives/symmetric-encryption/),
[psutil process lifecycle](https://psutil.io/api/),
[Microsoft directory ACLs](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls),
[Diffusers safe model formats](https://huggingface.co/docs/diffusers/main/using-diffusers/other-formats).
