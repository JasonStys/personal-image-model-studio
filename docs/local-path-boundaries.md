# Local path selection and artifact boundaries

Authored by Jason Stys. The normal installed app uses private accounts. This document also describes the deliberately privileged historical developer launcher.

## Private account mode

Uploaded files remain in the unlocked account's `imports` tree. The account proxy checks the resolved complete directory boundary before forwarding model/dataset requests; the underlying API independently receives only that import root as its selection grant. Browser JSON cannot add grants. Runtime mutation remains forbidden in account mode; a trusted ML runtime is selected by the owner at launch. Generated datasets, images, job results and glossaries use server-generated lowercase UUID32 identities under the active workspace. A malformed ID is rejected before database lookup. A valid but missing or other-account ID does not grant filesystem access.

The idle vault encryption, account authentication, original database schema, snapshot/rebase format and existing profile admission are unchanged. Existing generated UUID identities remain valid. Record bodies can retain absolute paths for compatibility and display, but a glossary write or image download derives its fixed artifact layout from the trusted workspace and validated ID, never that arbitrary saved text. Imported models still require a currently approved local source; generated models have a separate fixed job layout.

## Privileged legacy developer mode

The single-user bearer-token API intentionally allows the trusted OS owner to select local dataset/model inputs and a trusted Python executable. That is a stronger capability than private browser accounts. Its default independent approved roots are the workspace, the OS-owner home and the real configured interpreter directory. Normalization follows links before a complete component/separator boundary comparison; a sibling directory with a shared textual prefix does not qualify.

For an authorized export on another local volume, explicitly supply its directory at launch:

```text
python -m studio.cli --allow-local-root D:/ApprovedImageExports
```

The flag is repeatable and only the trusted launcher supplies it. A whole filesystem root, UNC/network/device path or a grant in HTTP JSON is refused. Copy authorized model/dataset exports into ordinary dedicated files; links and multiply linked files are not supported ingestion sources. An older registered external model outside current grants needs the owner to approve its actual directory explicitly. Existing files are preserved; the app does not silently broaden a grant, move them or reset data.

The runtime checkbox and Python filename check do not authenticate an executable. Only select an installed runtime you trust; this is not a sandbox for arbitrary executables or model code. Classic SD remains restricted to the existing known component classes and safe-tensor exports. Private account mode does not gain these legacy runtime capabilities.

## Files and limits

JSON, image, checkpoint-hash, ZIP and caption reads admit a regular single-link file, then validate the actual opened descriptor. Nonblocking/no-follow flags are used where supported; a POSIX FIFO swapped at open cannot wait for a writer. Actual byte accounting remains capped even if a file grows after metadata inspection. Images decode the already-read bounded bytes rather than reopening the pathname after hashing. Existing encoded-image, pixel, JSON, ZIP/member, checkpoint and model-tree limits remain in force.

Existing alias/reparse/hardlink checks are static admission and accidental-redirection safeguards. They do not provide an atomic filesystem snapshot or protection from an actively racing same-OS user/administrator. Exports, running model data and unlocked files remain sensitive plaintext on the trusted local computer. No scanner suppression, custom query barrier or universal-security claim is part of this design.

## Validation

`tests/test_local_paths.py` drives actual authenticated HTTP imports, runtime selection, fixed glossary/image layouts and denied-before-reader cases. It includes canonical IDs, sibling prefixes, normalized escapes, explicit approved external sources and forged saved absolute path text. `tests/test_local_files.py` uses actual descriptors, growth, NTFS/POSIX hardlinks and a bounded POSIX FIFO child. Windows can deny replacement while a descriptor is open; that native refusal and POSIX descriptor stability are both retained outcomes. Original CPU training, checkpoint resume, private vault/reopen, workers, browser and compiled native journeys remain separate required gates.
