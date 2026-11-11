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
