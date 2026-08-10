"""Exact active and legacy GitHub identities used by release verification.

Minting a release identity and accepting one are different decisions.  The
``CUNA_*`` names below are *asserting* surfaces: they declare who is allowed to
sign a new release, so they name the organisation this project actually
controls.  The ``LEGACY_*`` names and the ``*_EVIDENCE_IDENTITIES`` maps are
*accepting* surfaces: they exist only so evidence signed before the
organisation rename keeps verifying.  Never narrow an accepting surface --
removing one retroactively invalidates already-signed evidence.
"""

from __future__ import annotations

GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"

CUNA_SDK_REPOSITORY = "Cuna-Labs/cuna-lib-py"
LEGACY_SDK_REPOSITORY = "Runa-Laboratories/runa-lib-py"

CUNA_AUTHORITY_REPOSITORY = "Cuna-Labs/cuna-release-authority"
LEGACY_AUTHORITY_REPOSITORY = "Runa-Laboratories/runa-release-authority"


def workflow_certificate_identity(repository: str, workflow: str) -> str:
    """Return the exact GitHub Actions keyless certificate identity."""

    return f"https://github.com/{repository}/.github/workflows/{workflow}@refs/heads/main"


CUNA_RELEASE_CERTIFICATE_IDENTITY = workflow_certificate_identity(
    CUNA_SDK_REPOSITORY, "release.yml"
)
CUNA_EVIDENCE_CERTIFICATE_IDENTITY = workflow_certificate_identity(
    CUNA_SDK_REPOSITORY, "release-evidence.yml"
)
CUNA_PERFORMANCE_CERTIFICATE_IDENTITY = workflow_certificate_identity(
    CUNA_SDK_REPOSITORY, "performance-baseline.yml"
)
LEGACY_PERFORMANCE_CERTIFICATE_IDENTITY = workflow_certificate_identity(
    LEGACY_SDK_REPOSITORY, "performance-baseline.yml"
)

CUNA_AUTHORITY_CERTIFICATE_IDENTITY = workflow_certificate_identity(
    CUNA_AUTHORITY_REPOSITORY, "release-authority.yml"
)
LEGACY_AUTHORITY_CERTIFICATE_IDENTITY = workflow_certificate_identity(
    LEGACY_AUTHORITY_REPOSITORY, "release-authority.yml"
)

# Historical evidence remains verifiable only against these exact former identities.
# This mapping is intentionally not used to admit a new release or trusted publisher.
AUTHORITY_EVIDENCE_IDENTITIES = {
    CUNA_AUTHORITY_CERTIFICATE_IDENTITY: CUNA_AUTHORITY_REPOSITORY,
    LEGACY_AUTHORITY_CERTIFICATE_IDENTITY: LEGACY_AUTHORITY_REPOSITORY,
}
PERFORMANCE_EVIDENCE_IDENTITIES = {
    CUNA_PERFORMANCE_CERTIFICATE_IDENTITY: CUNA_SDK_REPOSITORY,
    LEGACY_PERFORMANCE_CERTIFICATE_IDENTITY: LEGACY_SDK_REPOSITORY,
}
