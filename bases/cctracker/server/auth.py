from dataclasses import dataclass
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

security = HTTPBearer(auto_error=False)

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


@dataclass(frozen=True, slots=True)
class Principal:
    sub: str
    scopes: set[str]
    claims: dict[str, Any]
    token: str | None = None


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    optional: bool = False
    include_token: bool = False

    async def __call__(
        self,
        wanted_scopes: SecurityScopes,
        token: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    ) -> Principal | None:
        if token is None:
            if self.optional:
                return None
            raise HTTPException(status_code=401, detail="Not authenticated")

        token_str = token.credentials
        try:
            claims = decode_jwt(token_str)
        except Exception:
            if self.optional:
                return None
            raise HTTPException(status_code=401, detail="Invalid token")

        sub = claims.get("sub", "unknown")
        token_scopes = set(claims.get("scopes", "").split())

        if wanted_scopes.scopes:
            required = set(wanted_scopes.scopes)
            # ALL required scopes:
            if not required.issubset(token_scopes):
                if self.optional:
                    return None
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing Permissions: {wanted_scopes.scope_str}",
                )

        return Principal(
            sub=sub,
            scopes=token_scopes,
            claims=claims,
            token=(token_str if self.include_token else None),
        )
