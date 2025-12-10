from typing import Annotated
from functools import lru_cache

from fastapi import Depends, HTTPException, APIRouter, status
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes, HTTPBearer
import jwt
from keycloak import KeycloakOpenID
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED

from cctracker.server.config import config

api_router = APIRouter(prefix="/auth")
security = HTTPBearer()

keycloak_openid = KeycloakOpenID(
    server_url=str(config.keycloak_server),
    client_id=config.keycloak_client,
    realm_name=config.keycloak_realm,
    client_secret_key=config.keycloak_key,
)

class VerifyResults(BaseModel):
    user: dict[str, str]

class AuthConfig(BaseModel):
    server_url: str = "/auth/"
    realm: str = config.keycloak_realm
    client_id: str = config.keycloak_client


@lru_cache(maxsize=1)
def get_keycloak_pubkey():
    return keycloak_openid.public_key()


def decode_jwt(token: str) -> dict[str, str]:
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
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid Token")

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


@api_router.get("/config")
async def get_keycloak_config() -> AuthConfig:
    """Returns the Keycloak config for the frontend, or any other services that needs it."""
    return AuthConfig()



@api_router.post("/verify")
async def verify_token(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    """Verify JWT token and return the results"""
    try:
        # Verify token with Keycloak
        token_info: dict[str, str] = keycloak_openid.introspect(token.credentials)
        if not token_info.get("active"):
            raise HTTPException(status_code=401, detail="Invalid token")
        return VerifyResults(user=token_info)
    except Exception:
        raise HTTPException(status_code=401, detail="Token verification failed")
