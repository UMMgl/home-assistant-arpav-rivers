# Public repository protections

## Required settings (must be verified on GitHub, not satisfied by this file)

Use **Settings > Rules > Rulesets** and configure an active branch ruleset targeting `main`:
- Require pull requests before merging, at least one independent approval and conversation resolution.
- Require passing checks: `hygiene`, `static-security`, `hassfest`, `unit`, `runtime`, compatibility matrix, `artifacts` and `hacs` when the public default-branch HACS validator is applicable. Set required check names only after observing them and confirming the check can pass before merge.
- Block force pushes and deletion. Restrict bypass privileges. Require up-to-date branches as appropriate.
- Enable **Settings > Security > Code security and analysis**: Dependabot alerts and security updates, secret scanning / push protection where available, and CodeQL default setup (Python) if supported.
- Set Actions default token permission to **read-only**, disallow unapproved third-party Actions and prefer immutable SHA pins.
- Configure a protected release environment, tag/release policy and OIDC trusted publishing. Do not create long-lived PyPI credentials.

## Publication gates

- No merge, tag, GitHub release or HACS production deployment until source and public SHA evidence is complete.
- Public workflow checks are incomplete while `veneto-hydro-client==0.1.0` is unpublished.
- HACS validation of the default branch may remain blocked until the package is safely merged. Do not silently waive this control. Use an approved bootstrap strategy with separate pre/post-merge validation and explicit evidence.
- Require a verified, content-addressed private backup snapshot of the exact public candidate SHA **before** a release tag is created. Check file paths, Git blob hashes and provenance manifest. No backup means no release. The daily release watcher is not a substitute for this gate.
- Require explicit human approval for public release and for deployment separately.
- Source provenance: `Indirizzopermailing/Home-Assistant` commit `d83bbf5a0374f0b97b82fd2273f74710b50e92d0` (only allowlisted files exported).

This document is not evidence that GitHub protection settings are active.
