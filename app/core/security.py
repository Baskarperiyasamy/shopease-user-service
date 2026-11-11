from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    id: int
    role: str


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_locally(token: str) -> AuthUser:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token has expired")
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token")

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise unauthorized("Invalid token")
    return AuthUser(id=user_id, role=payload.get("role", "customer"))


def verify_remotely(token: str) -> AuthUser:
    url = f"{settings.auth_service_url.rstrip('/')}/api/auth/verify-token"
    try:
        response = httpx.post(url, json={"token": token}, timeout=settings.auth_request_timeout)
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable",
        )

    if response.status_code == 200:
        data = response.json()
        return AuthUser(id=int(data["user_id"]), role=data["role"])
    if response.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive in the authentication service",
        )
    if response.status_code == 401:
        detail = "Invalid token"
        try:
            detail = response.json().get("detail", detail)
        except ValueError:
            pass
        raise unauthorized(detail)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication service returned an unexpected response",
    )


def get_auth_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> AuthUser:
    if credentials is None:
        raise unauthorized("Not authenticated")
    if settings.token_verification_mode == "remote":
        return verify_remotely(credentials.credentials)
    return verify_locally(credentials.credentials)
