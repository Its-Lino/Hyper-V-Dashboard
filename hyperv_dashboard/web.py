import asyncio
import logging

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import config
from .auth import (
    auth_enabled,
    auth_setup_required,
    csrf_token_is_valid,
    clear_auth_cookie,
    get_or_create_csrf_token,
    parse_urlencoded_form,
    password_is_configured,
    request_is_authenticated,
    require_auth,
    require_csrf,
    save_auth_password,
    set_csrf_cookie,
    set_auth_cookie,
    validate_session_token,
    verify_password,
)
from .constants import (
    APP_CREATOR,
    APP_NAME,
    APP_REPOSITORY_URL,
    APP_VERSION,
)
from .hyperv import list_vms, run_vm_action
from .icons import favicon_response
from .paths import resource_path
from .versioning import check_for_updates

app = FastAPI(title=APP_NAME, version=APP_VERSION)
templates = Jinja2Templates(directory=resource_path("templates"))

DISCORD_WEBHOOK_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
)


def discord_webhook_is_valid(webhook_url: str) -> bool:
    return webhook_url.startswith(DISCORD_WEBHOOK_PREFIXES)


def save_setup_discord_webhook(webhook_url: str) -> None:
    webhook_url = webhook_url.strip()
    if not webhook_url:
        return

    with config.config_lock:
        discord_config = config.config.setdefault("discord", {})
        webhooks = list(discord_config.get("webhooks", []))
        if webhook_url not in webhooks:
            webhooks.append(webhook_url)
        discord_config["webhooks"] = webhooks
        config.DISCORD_WEBHOOKS = webhooks
        config.save_config_file(config.config)


def render_auth_template(
    request: Request,
    mode: str,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    csrf_token = get_or_create_csrf_token(request)
    response = templates.TemplateResponse(
        request=request,
        name="auth.html",
        context={
            "title": APP_NAME,
            "version": APP_VERSION,
            "creator": APP_CREATOR,
            "repository_url": APP_REPOSITORY_URL,
            "mode": mode,
            "error": error,
            "csrf_token": csrf_token,
        },
        status_code=status_code,
    )
    set_csrf_cookie(response, csrf_token)
    return response


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> Response:
    if auth_setup_required():
        return RedirectResponse("/setup", status_code=303)

    if not request_is_authenticated(request):
        return RedirectResponse("/login", status_code=303)

    vms = await asyncio.to_thread(list_vms)
    csrf_token = get_or_create_csrf_token(request)

    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": APP_NAME,
            "version": APP_VERSION,
            "creator": APP_CREATOR,
            "repository_url": APP_REPOSITORY_URL,
            "csrf_token": csrf_token,
            "vms": vms,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@app.get("/setup", response_class=HTMLResponse)
def get_setup(request: Request) -> Response:
    if not auth_enabled() or not auth_setup_required():
        return RedirectResponse("/", status_code=303)

    return render_auth_template(request, mode="setup")


@app.post("/setup")
async def post_setup(request: Request) -> Response:
    if not auth_enabled() or not auth_setup_required():
        return RedirectResponse("/", status_code=303)

    form = await parse_urlencoded_form(request)
    if not csrf_token_is_valid(request, form.get("csrf_token")):
        return render_auth_template(
            request,
            mode="setup",
            error="Security token expired. Please try again.",
            status_code=403,
        )

    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")
    remember_device = form.get("session_mode") == "remember"
    discord_webhook = form.get("discord_webhook", "").strip()

    if len(password) < 8:
        return render_auth_template(
            request,
            mode="setup",
            error="Password must be at least 8 characters.",
            status_code=400,
        )

    if password != confirm_password:
        return render_auth_template(
            request,
            mode="setup",
            error="Passwords do not match.",
            status_code=400,
        )

    if discord_webhook and not discord_webhook_is_valid(discord_webhook):
        return render_auth_template(
            request,
            mode="setup",
            error="Discord webhook must start with https://discord.com/api/webhooks/.",
            status_code=400,
        )

    save_auth_password(password)
    save_setup_discord_webhook(discord_webhook)
    response = RedirectResponse("/", status_code=303)
    set_auth_cookie(response, remember_device)
    return response


@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request) -> Response:
    if not auth_enabled() or request_is_authenticated(request):
        return RedirectResponse("/", status_code=303)

    if auth_setup_required():
        return RedirectResponse("/setup", status_code=303)

    return render_auth_template(request, mode="login")


@app.post("/login")
async def post_login(request: Request) -> Response:
    if not auth_enabled():
        return RedirectResponse("/", status_code=303)

    if auth_setup_required():
        return RedirectResponse("/setup", status_code=303)

    form = await parse_urlencoded_form(request)
    if not csrf_token_is_valid(request, form.get("csrf_token")):
        return render_auth_template(
            request,
            mode="login",
            error="Security token expired. Please try again.",
            status_code=403,
        )

    password = form.get("password", "")
    remember_device = form.get("session_mode") == "remember"

    with config.config_lock:
        password_hash = config.AUTH_PASSWORD_HASH

    if not password_is_configured() or not verify_password(password, password_hash):
        logging.warning("Failed login attempt")
        return render_auth_template(
            request,
            mode="login",
            error="Invalid password.",
            status_code=401,
        )

    response = RedirectResponse("/", status_code=303)
    set_auth_cookie(response, remember_device)
    return response


@app.post("/logout")
def post_logout(_: None = Depends(require_csrf)) -> Response:
    response = RedirectResponse("/login", status_code=303)
    clear_auth_cookie(response)
    return response


@app.get("/favicon.ico", include_in_schema=False)
def get_favicon() -> Response:
    return favicon_response()


@app.get("/version")
def get_version() -> dict[str, str]:
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
    }


@app.get("/version/check")
def get_version_check() -> dict[str, object]:
    return check_for_updates()


@app.get("/vms")
def get_vms(_: None = Depends(require_auth)) -> list[dict[str, object]]:
    return list_vms()


@app.post("/vm/start/{name:path}")
def start_vm(
    name: str,
    _: None = Depends(require_auth),
    __: None = Depends(require_csrf),
) -> dict[str, str]:
    return run_vm_action(name, "Start-VM", "started")


@app.post("/vm/stop/{name:path}")
def stop_vm(
    name: str,
    _: None = Depends(require_auth),
    __: None = Depends(require_csrf),
) -> dict[str, str]:
    return run_vm_action(name, "Stop-VM", "stopped", force=True)


@app.post("/vm/restart/{name:path}")
def restart_vm(
    name: str,
    _: None = Depends(require_auth),
    __: None = Depends(require_csrf),
) -> dict[str, str]:
    return run_vm_action(name, "Restart-VM", "restarted", force=True)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    if not validate_session_token(websocket.cookies.get(config.AUTH_COOKIE_NAME)):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    logging.info("WebSocket connected")

    try:
        while True:
            vms = await asyncio.to_thread(list_vms)
            await websocket.send_json(vms)
            await asyncio.sleep(config.REFRESH_INTERVAL)
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    except Exception as exc:
        logging.error("WebSocket error: %s", exc)
