# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub Security Advisories. Do not open a public issue for an uncoordinated vulnerability.

## Repository hygiene

Never commit API keys, access tokens, passwords, private keys, Home Assistant credentials, `.env`, `secrets.yaml`, `.storage`, private endpoints or personal data.

If a real secret is committed, revoke or rotate it before history remediation.

## Release security

Release candidates are subject to secret/history scanning, dependency vulnerability checks, built-artifact hygiene checks and CycloneDX SBOM generation.

## Disclosure and response

Enable GitHub private vulnerability reporting under Settings > Security. Keep advisories private until a fix is available and disclosure is coordinated. For reported vulnerabilities, assess exploitability and impact, patch the affected release, and publish a security advisory when appropriate.

Do not place secrets in workflow YAML, repository variables, PR bodies or CI artifacts. Minimize the default `GITHUB_TOKEN` permissions to `contents: read`; require separate protected environments and short-lived OIDC tokens only for authorized publishing.
