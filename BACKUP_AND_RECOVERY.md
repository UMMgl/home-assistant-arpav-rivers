# Backup and recovery policy

The ARPAV River Level integration has a separate private backup location controlled by the project owner. Backups must never import the development repository's private history into the public project.

## Release backup contract

1. Before publishing a release or creating its public tag, freeze the exact public candidate commit SHA.
2. Materialize an immutable, version-labeled **private snapshot branch** containing the complete public source tree, plus a `.backup/manifest.json`. The manifest must record the originating repository, source commit SHA, release tag/version, originating file paths and Git blob SHA values, timestamp, and backup destination.
3. Independently read the snapshot back through GitHub and compare its file paths and Git blob SHA values with the frozen source tree. Only the additional `.backup/manifest.json` is permitted. Record the backup branch and source SHA as release evidence.
4. If the snapshot or verification fails, **block release**, even if all code tests pass. Do not weaken this requirement by accepting a missing backup.
5. Run a daily release watcher to detect any new tags/releases that lack verified backup snapshots, create missing snapshots when permissions allow, and notify on failures. This is delayed detection, not a pre-release gate.
6. Keep backup branches immutable by policy. A private backup branch ruleset that blocks deletion and non-fast-forward updates is recommended. Do not rotate or overwrite the only recoverable copy.
7. Periodically rehearse a restore in an isolated repository, including integrity checks and HACS installation, before relying on a snapshot for disaster recovery.

## Backup boundaries

- A tree snapshot preserves the exact content of tracked files at one commit. It is **not** a full Git history mirror and does not preserve pull request discussions, release attachments, issues, secrets, GitHub settings or branch rulesets.
- The backup described here is on the same GitHub platform as the source. It protects against an individual repository deletion but not a provider-wide outage, loss of both accounts or malicious deletion across both. Keep a separately encrypted, versioned and restorable off-provider copy as an additional control.
- Public restoration must use a clean public history with only approved content, never mirror a private development history.
- The snapshot service is deliberately independent of GitHub Actions to avoid consuming private runner minutes. Periodic verification does not authorize release, deployment or merge.

## Recovery

Select the private snapshot whose recorded source SHA matches the intended release. Verify the manifest and blobs, recover the approved file tree into a newly provisioned public repository/branch, restore branch protections and code-scanning/security settings, rerun all release gates, and obtain separate approval for restoring production. Maintain the prior release in parallel until smoke tests pass.
