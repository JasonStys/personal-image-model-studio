# Verify a created draft by its returned identity

By Jason Stys. Observed 11 November 2026.

The exact-main source, ML, native application and three processed CodeQL lanes
passed before release workflow 43078476593. Its prepare job successfully created
an empty unpublished draft for source `7fc2349013bac9a9e47f785d5e58a26daae51c1d`,
then failed because its immediate release collection read did not include that
draft. A later independent read confirmed the exact source and zero assets.
This is an observed create/readback consistency failure, not a model or native
application failure and not evidence of a global service outage.

The creation path now validates the structured POST response and reads that
exact returned release ID. It independently rechecks the ID, unpublished state,
stable version and source. Resuming an existing draft uses the same ID verifier.
There are no retries, ignored responses, retarget operations, asset replacements
or automatic publication. A malformed ID, changed source or published state is
still a hard failure before an upload can begin.

The focused regression keeps the release collection empty after successful
creation, proving that the returned ID is used instead of repeating the stale
collection lookup. Further negative cases reject malformed IDs before metadata
I/O and reject changed or published records on the exact-ID readback. Existing
source, draft, portable-package and all six asset guards remain mandatory.

The held empty preflight and actual failed job evidence are preserved separately.
This correction changes only release tooling and its tests/documentation; the
service, encrypted vault format, account paths, model code and Docker are unchanged.
Its exact-source hosted checks and fresh guarded packaging are still required.

## Packaged browser completion checks

The subsequent exact-head Windows and macOS packaged checks passed. Linux
passed all twelve original CPU checks and the actual training browser journey,
then the five account journeys could not unlock. The training journey ended
with a click on Lock without waiting for its encrypted operation to complete.
That is an incomplete test boundary; it is a candidate explanation for the
cross-account failure, not a confirmed diagnosis from the retained log alone.

The same final lock now holds the real request before sending it, verifies that
the account is still unlocked after the click, releases the unchanged request,
and waits for both the locked interface and the actual unlocked false status.
All original six journeys, assertions, deadlines and zero-retry gates remain.
Failed account tests also emit only boolean diagnostic classifications, never
credentials, keys, cookies, aliases or input contents. Service and vault code
are unchanged. Fresh complete packaged checks must establish whether this
completion correction resolves Linux or exposes another cause.

Local verification used the previously hash-verified clean compiled fd4
candidate, a fresh synthetic profile and the six original browser journeys.
All six passed in 2.8 minutes, including the real held-lock boundary, training,
generation, account isolation, encrypted reopen and recovery. The owned compiled
process exited normally with code zero. This establishes the stronger test on
that candidate; it does not replace new exact-head Linux or release validation.
