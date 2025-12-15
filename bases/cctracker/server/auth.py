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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Dev Mode Not Enabled"
        )
    try:
        return jwt.decode(
            token,
            "DEV_MODE_KEY",
            algorithms=["HS256"],
            audience="DEV_TOKEN"
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token"
        )


def sign(data: dict[str, str], salt: str | None = None):
    return dangerous_cookies.dumps(data, salt)


def verify(data: str, salt: str | None = None) -> dict[str, str]:
    return dangerous_cookies.loads(data, salt=salt)


@lru_cache(maxsize=1)
def get_keycloak_pubkey():
    return keycloak_openid.public_key()


def decode_jwt(token: str) -> dict[str, str]:
    if config.dev_mode:
        try:
            return decode_dev_jwt(token)
        except HTTPException:
            pass  # Fall through to keycloak

    public_key = (
        f"-----BEGIN PUBLIC KEY-----\n{get_keycloak_pubkey()}\n-----END PUBLIC KEY-----"
    )

    try:
        payload = jwt.decode(
            token, public_key, ["RS256"], audience=config.keycloak_client
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token"
        )

    return payload


async def get_current_user(
    wanted_scopes: SecurityScopes,
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    payload = decode_jwt(token.credentials)

    if wanted_scopes.scopes:
        token_scopes = payload.get("scopes", "").split()
        for scope in token_scopes:
            if scope in wanted_scopes.scopes:
                return payload
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing Permissions: {wanted_scopes.scope_str}",
        )

    return payload


# Auth Routes

api_router = APIRouter(prefix="/auth", tags=["auth"])


@api_router.get("/config")
async def get_keycloak_config() -> AuthConfig:
    """Returns the Keycloak config for the frontend, or any other services that needs it."""
    return AuthConfig()


@api_router.post("/verify")
async def verify_token(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    """Verify JWT token and return the results"""
    if config.dev_mode:
        try:
            token_info = decode_dev_jwt(token.credentials)
            return VerifyResults(user=token_info)
        except HTTPException:
            pass
    try:
        # Verify token with Keycloak
        token_info: dict[str, str] = keycloak_openid.introspect(token.credentials)
        if not token_info.get("active"):
            raise HTTPException(status_code=401, detail="Invalid token")
        return VerifyResults(user=token_info)
    except Exception:
        raise HTTPException(status_code=401, detail="Token verification failed")


@api_router.post("/dev-token", response_model=DevTokenResponse)
async def generate_dev_token(token_details: DevTokenRequest):
    """Generate a development token (only available in dev_mode)"""
    if not config.dev_mode:
        raise HTTPException(status_code=404, detail="Not found")

    token = create_dev_token(token_details.username, token_details.scopes)
    return DevTokenResponse(access_token=token)
