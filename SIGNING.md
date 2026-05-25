# Release Signing Policy

> *"Trust but verify."*

## Overview

All CCC-OS releases are signed to ensure integrity and authenticity.

## Signing Method

- **Git commit signing**: Every release tag is a signed Git commit
- **GitHub infrastructure**: Commits are signed via GitHub's Web Flow signing key
- **Verification**: Users can verify any commit with `git verify-commit`

## Key Management

| Key | Type | Purpose | Location |
|-----|------|---------|----------|
| GitHub Web Flow | RSA 4096 | Commit signing | GitHub infrastructure |

## Verification

```bash
# Verify the latest release commit
git verify-commit $(git rev-list -n 1 HEAD)

# Verify a specific tag
git tag -v v1.0.0
```

## Policy

1. Every release tag must be a signed commit
2. Force pushes to main are prohibited
3. Release notes include the signed commit hash

## Contact

For key rotation or security issues, contact `#fleet-ops` on Matrix.
