from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from functools import lru_cache

from fastapi import Depends, HTTPException, APIRouter, status
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes, HTTPBearer
import jwt
from itsdangerous.url_safe import URLSafeSerializer
from keycloak import KeycloakOpenID
from pydantic import BaseModel

from cctracker.server.config import config
from cctracker.log import get_logger

_log = get_logger(__name__)

security = HTTPBearer()

keycloak_openid = KeycloakOpenID(
    server_url=str(config.keycloak_server),
    client_id=config.keycloak_client,
    realm_name=config.keycloak_realm,
    client_secret_key=config.keycloak_key,
)

dangerous_cookies = URLSafeSerializer(config.signing_key)


class VerifyResults(BaseModel):
    user: dict[str, str | int]


class AuthConfig(BaseModel):
    server_url: str = "/auth/"
    realm: str = config.keycloak_realm
    client_id: str = config.keycloak_client


class DevTokenRequest(BaseModel):
    username: str = "dev_mode_user"
    scopes: list[str] = ["event:create", "admin"]


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_dev_token(username: str, scopes: list[str]) -> str:
    """Create a development JWT token"""
    _log.debug(f"Creating dev token for user '{username}' with scopes: {scopes}")
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": username,
        "scopes": " ".join(scopes),
        "aud": "DEV_TOKEN",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "dev-mode",
    }
    return jwt.encode(payload, "DEV_MODE_KEY", algorithm="HS256")


def decode_dev_jwt(token: str) -> dict[str, str]:
    """Decode development JWT token"""
    if not config.dev_mode:
        _log.warning("Dev token decode attempted but dev_mode is disabled")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Dev Mode Not Enabled"
        )
    try:
        payload = jwt.decode(
            token, "DEV_MODE_KEY", algorithms=["HS256"], audience="DEV_TOKEN"
        )
        _log.debug(f"Successfully decoded dev token for user: {payload.get('sub')}")
        return payload
    except jwt.ExpiredSignatureError:
        _log.warning("Dev token decode failed: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Expired"
        )
    except jwt.InvalidTokenError as e:
        _log.warning(f"Dev token decode failed: invalid token - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token"
        )


def sign(data: dict[str, str], salt: str | None = None):
    return dangerous_cookies.dumps(data, salt)


def verify(data: str, salt: str | None = None) -> dict[str, str]:
    return dangerous_cookies.loads(data, salt=salt)


@lru_cache(maxsize=1)
def get_keycloak_pubkey():
    _log.debug("Fetching Keycloak public key")
    pubkey = keycloak_openid.public_key()
    _log.info("Keycloak public key retrieved and cached")
    return pubkey


def decode_jwt(token: str) -> dict[str, str]:
    if config.dev_mode:
        _log.debug("Attempting dev token decode (dev_mode enabled)")
        try:
            return decode_dev_jwt(token)
        except HTTPException:
            _log.debug("Dev token decode failed, falling back to Keycloak")
            pass  # Fall through to keycloak

    _log.debug("Decoding JWT token with Keycloak public key")
    public_key = (
        f"-----BEGIN PUBLIC KEY-----\n{get_keycloak_pubkey()}\n-----END PUBLIC KEY-----"
    )

    try:
        payload = jwt.decode(
            token, public_key, ["RS256"], audience=config.keycloak_client
        )
        _log.debug(
            f"Successfully decoded Keycloak token for user: {payload.get('sub')}"
        )

    except jwt.ExpiredSignatureError:
        _log.warning("JWT decode failed: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Expired"
        )
    except jwt.InvalidTokenError as e:
        _log.warning(f"JWT decode failed: invalid token - {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token"
        )

    return payload


async def get_current_user(
    wanted_scopes: SecurityScopes,
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    _log.debug(f"Getting current user, wanted scopes: {wanted_scopes.scopes}")
    payload = decode_jwt(token.credentials)
    _log.debug(f"JWT payload: {payload}")
    username = payload.get("sub", "unknown")

    if wanted_scopes.scopes:
        token_scopes = payload.get("scopes", "").split()
        _log.debug(f"User '{username}' requesting access with scopes: {token_scopes}, ")
        _log.debug(f"required: {wanted_scopes.scopes}")
        for scope in token_scopes:
            if scope in wanted_scopes.scopes:
                _log.debug(f"User '{username}' authorized with scope '{scope}'")
                return payload
        _log.warning(
            f"User '{username}' denied: missing required scopes {wanted_scopes.scope_str}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing Permissions: {wanted_scopes.scope_str}",
        )

    _log.debug(f"User '{username}' authenticated (no specific scopes required)")
    return payload


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
