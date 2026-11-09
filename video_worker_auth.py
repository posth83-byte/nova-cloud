"""Authenticate the isolated GitHub Actions video worker using GitHub OIDC."""
from functools import lru_cache
import os

import jwt
from jwt import PyJWKClient

OIDC_ISSUER = "https://token.actions.githubusercontent.com"
OIDC_JWKS_URL = OIDC_ISSUER + "/.well-known/jwks"
OIDC_AUDIENCE = "https://nova-cloud-c4t9.onrender.com"


@lru_cache(maxsize=1)
def _jwks_client():
    return PyJWKClient(OIDC_JWKS_URL, cache_keys=True, lifespan=3600, timeout=15)


def validate_worker_claims(claims, repository=None):
    repository = repository or os.getenv("GITHUB_REPOSITORY", "posth83-byte/nova-cloud")
    expected_workflow = (
        f"{repository}/.github/workflows/video-render-worker.yml@refs/heads/main"
    )
    if claims.get("repository") != repository:
        raise PermissionError("OIDC-token kommer från fel GitHub-repository.")
    if claims.get("ref") != "refs/heads/main":
        raise PermissionError("Videorenderaren får bara köras från main.")
    if claims.get("event_name") != "repository_dispatch":
        raise PermissionError("Fel GitHub-event för videorenderaren.")
    if claims.get("workflow_ref") != expected_workflow:
        raise PermissionError("OIDC-token kommer från fel workflow.")
    return claims


def verify_video_worker_token(token):
    if not token or len(token) > 12000:
        raise PermissionError("GitHub OIDC-token saknas eller är ogiltig.")
    signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        audience=OIDC_AUDIENCE,
        issuer=OIDC_ISSUER,
        leeway=30,
        options={"require": ["exp", "iat", "iss", "aud"]},
    )
    return validate_worker_claims(claims)
