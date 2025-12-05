from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import SecurityScopes
from keycloak import KeycloakOpenID

from cctracker.event.core import oauth2_scheme
from cctracker.server.config import config

keycloak_openid = KeycloakOpenID(
    server_url=str(config.keycloak_server),
    client_id=config.keycloak_client,
    realm_name=config.keycloak_realm,
    client_secret_key=config.keycloak_key,
)


async def get_current_user(
    wanted_scopes: SecurityScopes, token: Annotated[str, Depends(oauth2_scheme)]
):
    try:
        decoded_token = keycloak_openid.decode_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Token") from e

    scopes: set[str] = set()
    if "scope" in decoded_token:
        scopes |= set(decoded_token["scope"].split())

    # Keycloak realm roles
    scopes |= set(decoded_token.get("realm_access", {}).get("roles", []))

    # Keycloak client roles
    client_roles = decoded_token.get("resource_access", {}).get("my-api-client", {}).get("roles", [])
    scopes |= set(client_roles)


async def get_current_user():
    pass
