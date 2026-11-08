# Public repository protection

Before the first release:

- protect the default branch;
- require pull requests and at least one approval;
- block force-push and branch deletion;
- require conversation resolution;
- require CI, secret/history, SBOM and security checks;
- use a protected publication environment;
- use PyPI Trusted Publishing OIDC rather than a long-lived token;
- bind release evidence to the exact public SHA/tag.
