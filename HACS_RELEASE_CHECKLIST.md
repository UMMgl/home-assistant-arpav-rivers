# HACS release checklist

HA ARPAV River Level is prepared in a private staging repository. A green private
run proves preparation only. It does not authorize publication or deployment.

1. Validate the exact validated source SHA/tag in private staging. All runtime,
   unit, coverage, lint, typing, repository-history and artifact hygiene checks
   must pass. Retain wheel, sdist, HACS zip, dependency audit, file hashes and
   schema-validated CycloneDX 1.7 SBOMs for the library and integration.
2. Obtain explicit approval for the publisher identity and public repository,
   separate from the private development repository. Export only the allowlist
   into a new repository; do not mirror the private history. Verify exported hashes.
3. Activate and read back the public repository controls in PUBLIC_REPO_RULESET.md
   before any release: required checks, review, branch/tag restrictions and
   protected publishing environments. Any unavailable protection remains a gate.
4. Merge and validate the standalone transport library correction. Configure its
   approved PyPI publisher, publish veneto-hydro-client 0.1.0 and verify the exact
   wheel/sdist hashes and attestations. The integration manifest requires that
   exact version; editable/private library installs do not prove public readiness.
5. Repeat all evidence on the exact public candidate SHA. Run HACS validation
   with no ignored checks and Home Assistant hassfest. Run the public workflow's
   dependency/security, coverage, typing, hygiene and artifact jobs. Both validators
   use pinned container digests; record any intentional validator update.
6. Perform clean-install and upgrade smoke tests from the published library and
   exported integration on HA 2026.8.2 and 2026.9.4. Confirm flow, entity identity,
   data recovery and stale/error visibility. Record the rollback path and rehearse
   restoring the prior artifact/config backup in an isolated environment. CI import
   compatibility and current-version runtime tests do not substitute for these tests.
7. BEFORE creating any public release tag, verify a matching immutable private
   snapshot of the exact public candidate SHA. Compare every tracked file path
   and Git blob SHA against the snapshot; retain a backup manifest and a link to
   the private backup ref. Treat absent or unverified backups as a blocking
   release condition. The daily post-release watch is only a safety net.
8. Obtain fresh, separate human approval for release and any production deployment.
   Keep the PR draft until all applicable gates have evidence on the public candidate.

No runtime Supabase/H2 dependency is part of this integration. The internal quality
benchmark is not an official Home Assistant quality-tier award. The elected CRA
controls stay blocking throughout preparation and release.
