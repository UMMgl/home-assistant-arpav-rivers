# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub Security Advisories. Do not open a public issue for an uncoordinated vulnerability.

## Repository hygiene

Never commit API keys, access tokens, passwords, private keys, Home Assistant credentials, `.env`, `secrets.yaml`, `.storage`, private endpoints or personal data.

If a real secret is committed, revoke or rotate it before history remediation.

## Release security

Release candidates are subject to secret/history scanning, dependency vulnerability checks, built-artifact hygiene checks and CycloneDX SBOM generation.
