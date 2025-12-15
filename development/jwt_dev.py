from datetime import datetime, timedelta
from typing import Any
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status, Security, Request
from fastapi.security import (
    HTTPBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from pydantic import BaseModel
import jwt

import logging

logging.basicConfig(format=logging.BASIC_FORMAT, level=logging.INFO)

log = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # -------------------------------------------------------
        # Read request body safely (must buffer for later use)
        # -------------------------------------------------------
        body_bytes = await request.body()

        # Log request details
        log.info("\n---- Incoming Request ----")
        log.info(f"{request.method} {request.url}")
        log.info(f"Headers: {dict(request.headers)}")
        try:
            log.info(f"Body: {body_bytes.decode() or '<empty>'}")
        except UnicodeDecodeError:
            log.info("Body: <binary data>")

        # -------------------------------------------------------
        # Replace the request stream with the buffered body
        # so FastAPI can read it again
        # -------------------------------------------------------
        async def bodygen():
            yield body_bytes

        request._receive = lambda: {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

        # -------------------------------------------------------
        # Process the request, capture the response
        # -------------------------------------------------------
        response: Response = await call_next(request)

        # -------------------------------------------------------
        # Read and log response body
        # -------------------------------------------------------
        resp_body = b""
        async for chunk in response.body_iterator:
            resp_body += chunk

        # Log response details
        log.info("---- Response ----")
        log.info(f"Status: {response.status_code}")
        try:
            log.info(f"Body: {resp_body.decode() or '<empty>'}")
        except UnicodeDecodeError:
            log.info("Body: <binary data>")

        # -------------------------------------------------------
        # Return a new Response with the captured body
        # (since once we read it, we must recreate it)
        # -------------------------------------------------------
        new_response = Response(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        return new_response


app = FastAPI(title="OAuth2 Scope Playground (JWT + Annotated)")
app.add_middleware(LoggingMiddleware)
# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
SECRET_KEY = "CHANGE_ME_SUPER_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# ---------------------------------------------------------------------
# Fake database
# ---------------------------------------------------------------------
fake_users_db: dict[str, dict[str, Any]] = {
    "alice": {"username": "alice", "password": "secret", "scopes": ["read"]},
    "bob": {"username": "bob", "password": "secret", "scopes": ["read", "write"]},
    "admin": {
        "username": "admin",
        "password": "secret",
        "scopes": ["read", "write", "admin"],
    },
}


# ---------------------------------------------------------------------
# OAuth2 config
# ---------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "read": "Read your data.",
        "write": "Write or modify data.",
        "admin": "Administrative operations.",
    },
)


# ---------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str
    scopes: list[str]


class User(BaseModel):
    username: str
    scopes: list[str]


# ---------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------
def authenticate_user(username: str, password: str):
    user = fake_users_db.get(username)
    if not user or user["password"] != password:
        return None
    return user


def create_access_token(
    subject: str,
    scopes: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta

    encoded = jwt.encode(
        {"sub": subject, "scopes": scopes, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    if isinstance(encoded, bytes):
        encoded = encoded.decode()
    return encoded


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------
# Dependency using Annotated + SecurityScopes
# ---------------------------------------------------------------------
async def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    payload = decode_access_token(token)

    username = payload.get("sub")
    token_scopes = payload.get("scopes", [])

    if username is None:
        raise HTTPException(status_code=401, detail="Token missing subject")

    user = fake_users_db.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_scopes_set = set(token_scopes)
    required_scopes = set(security_scopes.scopes)

    if not required_scopes.issubset(token_scopes_set):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Not enough permissions",
                "required": list(required_scopes),
                "token_scopes": token_scopes,
            },
        )

    return User(username=username, scopes=token_scopes)


async def get_current_user_v2(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(HTTPBearer())],
) -> User:
    payload = decode_access_token(token)

    username = payload.get("sub")
    token_scopes = payload.get("scopes", [])

    if username is None:
        raise HTTPException(status_code=401, detail="Token missing subject")

    user = fake_users_db.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_scopes_set = set(token_scopes)
    required_scopes = set(security_scopes.scopes)

    if not required_scopes.issubset(token_scopes_set):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Not enough permissions",
                "required": list(required_scopes),
                "token_scopes": token_scopes,
            },
        )

    return User(username=username, scopes=token_scopes)


# ---------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------
@app.post("/token", response_model=Token)
async def issue_token(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(401, detail="Incorrect username or password")

    allowed_scopes = set(user["scopes"])
    requested_scopes = set(form.scopes)
    granted_scopes = list(allowed_scopes.intersection(requested_scopes))

    jwt_token = create_access_token(subject=form.username, scopes=granted_scopes)

    return Token(access_token=jwt_token, token_type="bearer", scopes=granted_scopes)


# ---------------------------------------------------------------------
# Protected endpoints using Annotated
# ---------------------------------------------------------------------
@app.get("/me", response_model=User)
async def read_me(
    current_user: Annotated[User, Security(get_current_user, scopes=["read"])],
):
    return current_user


@app.get("/me2", response_model=User)
async def read_me2(
    current_user: Annotated[User, Security(get_current_user_v2, scopes=["read"])],
):
    return current_user


@app.post("/items", response_model=User)
async def create_item(
    current_user: Annotated[User, Security(get_current_user, scopes=["write"])],
):
    return current_user


@app.get("/admin", response_model=User)
async def admin_only(
    current_user: Annotated[User, Security(get_current_user, scopes=["admin"])],
):
    return current_user


@app.get("/combo", response_model=User)
async def combo(
    current_user: Annotated[User, Security(get_current_user, scopes=["read", "write"])],
):
    return current_user


@app.get("/")
async def root():
    return {"message": "OAuth2 JWT Scopes with Annotated"}
