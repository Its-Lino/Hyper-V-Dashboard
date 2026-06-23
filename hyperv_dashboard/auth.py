import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from urllib.parse import parse_qs

from fastapi import HTTPException, Request
from fastapi.responses import Response

from . import config

CSRF_COOKIE_NAME = "hvd_csrf"
CSRF_HEADER_NAME = "x-csrf-token"


def auth_enabled() -> bool:
    with config.config_lock:
        return bool(config.AUTH_ENABLED)


def auth_setup_required() -> bool:
    with config.config_lock:
        return bool(
            config.AUTH_ENABLED
            and config.AUTH_SETUP_ALLOWED
            and not config.AUTH_PASSWORD_HASH
        )


def password_is_configured() -> bool:
    with config.config_lock:
        return bool(config.AUTH_PASSWORD_HASH)


def hash_password(password: str) -> str:
    iterations = 260_000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    )
    return hmac.compare_digest(digest.hex(), expected_digest)


def encode_session_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(encoded).decode().rstrip("=")


def decode_session_payload(encoded_payload: str) -> dict[str, Any] | None:
    padding = "=" * (-len(encoded_payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(encoded_payload + padding)
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def sign_session_payload(encoded_payload: str) -> str:
    with config.config_lock:
        secret_key = config.AUTH_SECRET_KEY

    signature = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def create_session_token(remember_device: bool) -> str:
    with config.config_lock:
        remember_days = config.AUTH_REMEMBER_DAYS
        session_hours = config.AUTH_SESSION_HOURS

    ttl_seconds = (
        remember_days * 24 * 60 * 60
        if remember_device
        else session_hours * 60 * 60
    )
    payload = {
        "sub": "admin",
        "exp": int(time.time() + ttl_seconds),
        "mode": "remember" if remember_device else "session",
        "nonce": secrets.token_urlsafe(16),
    }
    encoded_payload = encode_session_payload(payload)
    return f"{encoded_payload}.{sign_session_payload(encoded_payload)}"


def validate_session_token(token: str | None) -> bool:
    if not auth_enabled():
        return True

    if not token or "." not in token:
        return False

    encoded_payload, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(sign_session_payload(encoded_payload), signature):
        return False

    payload = decode_session_payload(encoded_payload)
    if not payload:
        return False

    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return False

    return payload.get("sub") == "admin" and expires_at > int(time.time())


def request_is_authenticated(request: Request) -> bool:
    return validate_session_token(request.cookies.get(config.AUTH_COOKIE_NAME))


async def require_auth(request: Request) -> None:
    if not request_is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_or_create_csrf_token(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE_NAME) or create_csrf_token()


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=False,
        samesite="lax",
    )


def csrf_token_is_valid(request: Request, submitted_token: str | None) -> bool:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    return bool(
        cookie_token
        and submitted_token
        and hmac.compare_digest(cookie_token, submitted_token)
    )


async def require_csrf(request: Request) -> None:
    submitted_token = request.headers.get(CSRF_HEADER_NAME)

    if not submitted_token:
        form = await parse_urlencoded_form(request)
        submitted_token = form.get("csrf_token")

    if not csrf_token_is_valid(request, submitted_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def set_auth_cookie(response: Response, remember_device: bool) -> None:
    token = create_session_token(remember_device)
    with config.config_lock:
        remember_days = config.AUTH_REMEMBER_DAYS

    max_age = remember_days * 24 * 60 * 60 if remember_device else None
    response.set_cookie(
        config.AUTH_COOKIE_NAME,
        token,
        httponly=True,
        max_age=max_age,
        samesite="lax",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(config.AUTH_COOKIE_NAME)


async def parse_urlencoded_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def save_auth_password(password: str) -> None:
    password_hash = hash_password(password)
    with config.config_lock:
        config.AUTH_PASSWORD_HASH = password_hash
        config.config.setdefault("auth", {})["password_hash"] = password_hash
        config.save_config_file(config.config)
