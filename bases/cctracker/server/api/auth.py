from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from cctracker.server.config import config
from cctracker.server.auth import AuthConfig, DevTokenRequest, DevTokenResponse, VerifyResults, create_dev_token, decode_dev_jwt, security, keycloak_openid
from cctracker.log import get_logger

_log = get_logger(__name__)

# Auth Routes
api_router = APIRouter(prefix="/auth", tags=["auth"])


@api_router.get("/config")
async def get_keycloak_config() -> AuthConfig:
    """Returns the Keycloak config for the frontend, or any other services that needs it."""
    _log.debug("Auth config requested")
    return AuthConfig()


@api_router.post("/verify")
async def verify_token(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    """Verify JWT token and return the results"""
    _log.debug("Token verification requested")

    if config.dev_mode:
        try:
            token_info = decode_dev_jwt(token.credentials)
            _log.info(f"Dev token verified for user: {token_info.get('sub')}")
            return VerifyResults(user=token_info)
        except HTTPException:
            _log.debug("Dev token verification failed, trying Keycloak")
            pass
    try:
        # Verify token with Keycloak
        _log.debug("Verifying token with Keycloak introspection")
        token_info: dict[str, str] = keycloak_openid.introspect(token.credentials)
        if not token_info.get("active"):
            _log.warning("Token verification failed: token not active")
            raise HTTPException(status_code=401, detail="Invalid token")
        _log.info(
            f"Token verified via Keycloak for user: {token_info.get('sub', 'unknown')}"
        )
        return VerifyResults(user=token_info)
    except HTTPException:
        raise
    except Exception as e:
        _log.error(f"Token verification failed with exception: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")


@api_router.post("/dev-token", response_model=DevTokenResponse)
async def generate_dev_token(token_details: DevTokenRequest):
    """Generate a development token (only available in dev_mode)"""
    if not config.dev_mode:
        _log.warning("Dev token generation attempted but dev_mode is disabled")
        raise HTTPException(status_code=404, detail="Not found")

    _log.info(f"Generating dev token for user '{token_details.username}' ")
    _log.info(f"with scopes: {token_details.scopes}")

    token = create_dev_token(token_details.username, token_details.scopes)
    return DevTokenResponse(access_token=token)
