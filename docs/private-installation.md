# Install Personal Image Model Studio 0.2 — Jason Stys

## Portable application

Download the OS/architecture archive and matching `.sha256` from the official
[GitHub releases](https://github.com/JasonStys/personal-image-model-studio/releases).
Verify the **whole checksum before launch**: Windows `Get-FileHash -Algorithm SHA256`,
Linux `sha256sum`, macOS `shasum -a 256`. Extract into a folder you control and launch
`PersonalImageModelStudio` (Windows `.exe`). Keep its console/process running.
It opens your default browser at an automatically allocated `127.0.0.1` port.
This is not a public URL. No firewall, startup, registry, GPU-driver or browser
extension change is made. Closing the application stops its local account service.

The one-file CPU application includes Python, UI, encryption and actual native
diffusion training/inference. No Python, npm, IntelliJ, external model API or model
download is needed for that native workflow. It is a large ML executable and may
take time to extract/start. Supplied compact models learn limited caption domains;
they are not general or photorealistic generators. No pretrained weights ship.

Packages are **unsigned**. Checksums check integrity, not independent publisher
identity. Do not blindly defeat OS/antivirus warnings. macOS is a command-line
arm64 executable, not a notarized `.app`; Linux is an x86_64 executable, not a
distribution package. Supported architecture/runtime compatibility is tested,
not every device. Native iOS/Android installers and public mobile hosting are
not provided. The interface itself is responsive and browser-tested.

## Private account and image workflow

1. Create a non-identifying alias and unique **15–128 character login password**.
   Save the once-shown recovery code in your password manager.
2. Choose a **different 20–256 character vault phrase**, preferably six random
   words. There is no developer/admin recovery backdoor for a forgotten phrase.
3. Open Datasets → Create owned synthetic test dataset. Or choose files/directories
   with images and matching UTF-8 captions (or ZIPs), review rights, then import.
4. In Train, select the dataset. Start with native mode, 32 pixels, CPU, a small
   step/batch budget. Watch reports and finite held-out metrics. Small regression
   runs prove execution, not visual quality. Longer runs must still be evaluated.
5. Select the learned model, use captions it has learned, generate, then open
   History to preview/download, record feedback or explicitly revise/edit.

Only one account may unlock the local ML engine at a time. Account mode cannot
read arbitrary typed PC paths or select an executable through the browser.
File pickers stage data only inside the unlocked account. Executable models,
pickle/`.pt`/`.pth`, links and traversal paths are rejected; native/classic model
formats are explicitly limited. The built-in CPU package supports **native**
models, not classic SD/LoRA. Those preserved features require source mode/full
ML extras and an explicitly trusted operator-configured runtime.

## Runtime privacy, keys and shutdown

Default data is **outside Git and installation files**:

- Windows: `%LOCALAPPDATA%\PersonalImageModelStudioAccounts`
- macOS: `~/Library/Application Support/PersonalImageModelStudioAccounts`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/PersonalImageModelStudioAccounts`

The directory has owner-only POSIX permissions or restricted Windows inherited
ACL grants for the current OS user, SYSTEM and administrators. Administrators and
compromised processes remain a threat. The database stores aliases, scrypt hashes,
random session/recovery digests and encrypted-key configuration, **not passwords,
vault phrases or saved plaintext keys**. Locked archives contain encrypted images,
datasets, models, prompts, job logs and feedback.

Browser key derivation uses PBKDF2-HMAC-SHA256/600,000 and gives its 256-bit key to
the trusted **local** service while unlocked. Genuine ML needs temporary plaintext
files. Lock/sign out/graceful shutdown cancels owned jobs, encrypts idle state,
disconnects providers and removes that staging directory. An OS/process crash may
leave plaintext recovery files; the same owner must unlock/lock to recover/clean
them. Do not delete the data directory to "repair" the app. Use device encryption
and a separate OS login. The app cannot hide active data from your OS administrator.

Human-idle lock defaults to ten minutes and **cancels active jobs**. Select a longer
30-minute/two-hour limit explicitly for slow training; polling does not renew it.
The ML subprocess exits when its exact parent process exits; it does not intentionally
continue as an orphaned trainer. Save/lock failures preserve recoverable files.

## Backups, exports and removal

Save snapshot only when uploads/jobs finish. The encrypted archive download must
be kept with its account/key settings: back up the **entire protected account data
directory after stopping the app**. An archive alone does not restore credentials
in 0.2. Restore that directory to an empty dedicated data location on the same
compatible installation and sign in/unlock; stored paths are rebased. Keep a
separate verified copy before any restore. Do not overwrite an active data root.

PNG/report/feedback ZIP exports are plaintext and require separate protection.
Login recovery revokes sessions and rotates login/recovery credentials; it cannot
recover the independent vault phrase. Delete account needs its current password
and explicit confirmation. It removes live records/files, not old backups or disk
sectors. To remove the portable app, stop it and remove its executable. Private
data stays separate until you explicitly delete it; preserve a usable backup.

## Creator, help and optional provider

Built-in Help explains features, rights, hardware/quality limits, recovery, privacy
and installation. [Jason Stys on GitHub](https://github.com/JasonStys) and
[LinkedIn contact](https://www.linkedin.com/in/jason-stys-31b30b351/).
Do not send credentials/private art in an issue. There is no telemetry, external
font, ad SDK, tracking or automatic model/artwork download. Optional DeviantArt
access needs your explicit authorization, registered public client/callback,
rights and provider-terms review. Its token stays in memory and is forgotten on
lock. New random ports require a matching registered callback; use a chosen fixed
port via source launcher when needed. No provider account is used in default tests.
