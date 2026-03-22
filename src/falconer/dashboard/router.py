"""Dashboard web UI router for Falconer."""

from __future__ import annotations

import asyncio
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..logging import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Project root = 4 parents up from this file (dashboard/ → falconer/ → src/ → Falconer/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

_sessions: Dict[str, datetime] = {}
SESSION_COOKIE = "falconer_session"
SESSION_TTL = timedelta(hours=8)
DEFAULT_USER = "admin"
DEFAULT_PASS = "falconer"


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _is_authenticated(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    expiry = _sessions.get(token)
    if not expiry or datetime.utcnow() > expiry:
        _sessions.pop(token, None)
        return False
    return True


# ── .env helpers ──────────────────────────────────────────────────────────────

def _read_env() -> Dict[str, str]:
    """Parse the project .env file into a dict."""
    result: Dict[str, str] = {}
    if not ENV_PATH.exists():
        return result
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        result[key.strip()] = val.strip()
    return result


def _write_env(updates: Dict[str, str]) -> None:
    """Merge updates into the project .env file, preserving comments/ordering."""
    existing_lines: List[str] = []
    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    written_keys: set = set()
    new_lines: List[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            written_keys.add(key)
        else:
            new_lines.append(line)

    # Append any keys not already present
    remaining = {k: v for k, v in updates.items() if k not in written_keys}
    if remaining:
        new_lines.append("")
        new_lines.append("# Added by Falconer Setup Wizard")
        for k, v in remaining.items():
            new_lines.append(f"{k}={v}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _is_setup_complete() -> bool:
    """Return True if .env exists and SETUP_COMPLETE=true is set."""
    env = _read_env()
    return env.get("SETUP_COMPLETE", "").lower() == "true"


# ── Connection testers ────────────────────────────────────────────────────────

async def _test_bitcoin(
    scheme: str,
    host: str,
    port: Optional[int],
    user: str,
    password: str,
    use_tor: bool = False,
    socks5_proxy: str = "socks5://127.0.0.1:9050",
) -> Tuple[bool, str]:
    url = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
    is_onion = host.endswith(".onion")
    via_tor = use_tor or is_onion
    try:
        client_kwargs: Dict[str, Any] = {"timeout": 20 if via_tor else 10, "verify": False}
        if via_tor:
            client_kwargs["proxy"] = socks5_proxy
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.post(
                url,
                json={"jsonrpc": "1.0", "id": "falconer-test", "method": "getblockchaininfo", "params": []},
                auth=(user, password),
            )
        if resp.status_code == 200:
            r = resp.json().get("result", {})
            chain = r.get("chain", "?")
            blocks = r.get("blocks", "?")
            synced = r.get("blocks") == r.get("headers")
            sync_str = "synced ✔" if synced else "syncing…"
            tor_str = " via Tor" if via_tor else ""
            return True, f"Connected{tor_str} — chain: {chain}, block: {blocks:,} ({sync_str})"
        if resp.status_code == 401:
            return False, "Authentication failed — check RPC username and password"
        return False, f"Unexpected HTTP {resp.status_code}"
    except httpx.ConnectError:
        if via_tor:
            return False, f"Cannot reach Tor proxy at {socks5_proxy} — is Tor running?"
        return False, f"Connection refused at {url} — is Bitcoin Core running?"
    except httpx.TimeoutException:
        if host.endswith(".local"):
            return False, (
                f"Timed out connecting to {url} — mDNS (.local) addresses can be "
                "unreachable from some hosts. Try Tor mode if your node has a "
                ".onion address, or enter the raw IP address (e.g. 192.168.x.x) instead."
            )
        return False, f"Timed out connecting to {url}"
    except Exception as exc:
        err = str(exc)
        if "socksio" in err or "SOCKS" in err.upper():
            return False, "SOCKS5 support missing — run: pip install socksio"
        return False, err


def _is_html(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("<!") or stripped.lower().startswith("<html")


async def _test_electrs(
    scheme: str,
    host: str,
    port: int,
    use_tor: bool = False,
    socks5_proxy: str = "socks5://127.0.0.1:9050",
    api_prefix: str = "",
) -> Tuple[bool, str]:
    via_tor = use_tor or host.endswith(".onion")
    esplora_mode = api_prefix == "/api"
    base = f"{scheme}://{host}:{port}"

    client_kwargs: Dict[str, Any] = {
        "timeout": 25 if via_tor else 10,
        "follow_redirects": True,
        "verify": False,
    }
    if via_tor:
        client_kwargs["proxy"] = socks5_proxy

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            if esplora_mode:
                # Use the JSON fees endpoint as the primary check — it can't be confused
                # with the Mempool HTML frontend (which returns 200 + HTML for all paths).
                fees_url = f"{base}/api/v1/fees/recommended"
                resp = await client.get(fees_url)
                if resp.status_code == 200:
                    body = resp.text.strip()
                    if _is_html(body):
                        return False, (
                            "Got an HTML page instead of JSON — the URL is pointing at the "
                            "Mempool web frontend rather than the API. "
                            "Check that the host/port/scheme are correct and the Mempool "
                            "service is running."
                        )
                    try:
                        data = resp.json()
                    except Exception:
                        return False, f"Non-JSON response from {fees_url} — is this a Mempool/Esplora endpoint?"
                    fastest = data.get("fastestFee")
                    if fastest is None:
                        return False, f"Unexpected JSON shape from {fees_url} — expected fastestFee key, got: {list(data.keys())}"
                    label = "via Tor " if via_tor else ""
                    return True, f"Connected (Esplora/Mempool) {label}— fastest fee: {fastest} sat/vB"
                return False, f"HTTP {resp.status_code} from {fees_url} — is Mempool API reachable on port {port}?"
            else:
                # Standard Electrs REST mode: tip height is a plain integer
                tip_url = f"{base}/blocks/tip/height"
                resp = await client.get(tip_url)
                if resp.status_code == 200:
                    body = resp.text.strip()
                    if _is_html(body):
                        return False, (
                            "Got an HTML page instead of a block height. "
                            "The server at this address is a web frontend, not the Electrs REST API."
                        )
                    try:
                        height = int(body)
                    except ValueError:
                        return False, f"Expected a block height integer, got: {body[:80]}"
                    label = "via Tor " if via_tor else ""
                    return True, f"Connected {label}— tip height: {height:,}"
                return False, f"HTTP {resp.status_code} — is Electrs REST API running on port {port}?"

    except httpx.RemoteProtocolError:
        if esplora_mode:
            return False, "Non-HTTP response — check that the host/port is a Mempool or Esplora HTTP endpoint."
        return False, (
            f"Port {port} returned a non-HTTP response — "
            "this looks like the Electrum TCP port (50001). "
            "Enter the Electrs HTTP REST port instead (usually 3002 or 80)."
        )
    except httpx.ConnectError as exc:
        err = str(exc)
        if "socksio" in err or "SOCKS" in err.upper() or "No module" in err:
            return False, "SOCKS5 support missing — run: pip install socksio"
        if via_tor:
            return False, (
                f"Cannot connect via Tor. "
                f"Check: (1) Tor daemon running at {socks5_proxy}, "
                f"(2) .onion address is correct, (3) port {port} is correct."
            )
        return False, f"Connection refused at {base}"
    except httpx.TimeoutException:
        if via_tor:
            return False, f"Timed out after 25 s — .onion may be unreachable or port {port} is wrong"
        return False, "Timed out — check host/port"
    except Exception as exc:
        err = str(exc)
        if "socksio" in err or "SOCKS" in err.upper() or "No module" in err:
            return False, "SOCKS5 support missing — run: pip install socksio"
        return False, f"Error: {err}"


async def _test_lnbits(
    scheme: str, host: str, port: Optional[int], api_key: str
) -> Tuple[bool, str]:
    base = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
    url = f"{base}/api/v1/wallet"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, verify=False) as client:
            resp = await client.get(url, headers={"X-Api-Key": api_key})

        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            try:
                data = resp.json()
            except Exception:
                # 200 but body isn't JSON — usually means HTTP redirected to HTTPS
                # and the HTTPS page returned HTML, or the host serves a web UI
                preview = resp.text[:80].replace("\n", " ").strip()
                if scheme == "http":
                    return False, (
                        f"Server returned 200 but non-JSON body. "
                        f"Try switching to https:// — Start9/.local services usually require HTTPS. "
                        f"Response starts: {preview!r}"
                    )
                return False, f"Server returned 200 but non-JSON body: {preview!r}"
            balance = data.get("balance", 0)
            name = data.get("name", "wallet")
            return True, f"Connected — wallet '{name}', balance: {balance // 1000:,} sats"

        if resp.status_code == 401:
            return False, "Authentication failed — check API key"
        if resp.status_code == 307 or resp.status_code == 301 or resp.status_code == 302:
            loc = resp.headers.get("location", "")
            return False, f"Redirect to {loc!r} — try changing scheme to https://"
        return False, f"HTTP {resp.status_code} at {url}"
    except httpx.ConnectError as exc:
        err = str(exc)
        if scheme == "http":
            return False, (
                f"Connection refused at {base}. "
                "If this is a Start9/.local node try using https:// instead of http://."
            )
        return False, f"Connection refused at {base}: {err}"
    except httpx.TimeoutException:
        return False, f"Timed out connecting to {base}"
    except Exception as exc:
        return False, str(exc)


async def _test_mempool(
    base_url: str,
    use_tor: bool = False,
    socks5_proxy: str = "socks5://127.0.0.1:9050",
) -> Tuple[bool, str]:
    url = base_url.rstrip("/") + "/api/v1/fees/recommended"
    is_onion = ".onion" in base_url
    via_tor = use_tor or is_onion
    try:
        client_kwargs: Dict[str, Any] = {"timeout": 20 if via_tor else 8, "follow_redirects": True, "verify": False}
        if via_tor:
            client_kwargs["proxy"] = socks5_proxy
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            fastest = data.get("fastestFee", "?")
            half = data.get("halfHourFee", "?")
            tor_str = " via Tor" if via_tor else ""
            return True, f"Connected{tor_str} — fastest: {fastest} sat/vB, 30 min: {half} sat/vB"
        return False, f"HTTP {resp.status_code} from {base_url}"
    except httpx.ConnectError:
        if via_tor:
            return False, f"Cannot reach Tor proxy at {socks5_proxy} — is Tor running?"
        return False, f"Connection refused at {base_url}"
    except httpx.TimeoutException:
        return False, f"Timed out connecting to {base_url}"
    except Exception as exc:
        err = str(exc)
        if "socksio" in err or "SOCKS" in err.upper():
            return False, "SOCKS5 support missing — run: pip install socksio"
        return False, err


async def _test_vllm(base_url: str, model: str, api_key: str = "") -> Tuple[bool, str]:
    base = base_url.rstrip("/")
    models_url = (base + "/models") if base.endswith("/v1") else (base + "/v1/models")
    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=10, headers=headers, verify=False) as client:
            resp = await client.get(models_url)
        if resp.status_code == 401:
            return False, "Authentication failed — check API key"
        if resp.status_code == 200:
            ids = [m["id"] for m in resp.json().get("data", [])]
            if model in ids:
                return True, f"Connected — model '{model}' available ✔"
            if ids:
                return True, f"Connected — model '{model}' not found. Available: {', '.join(ids[:4])}"
            return True, "Connected — model list empty (server may still be loading)"
        return False, f"HTTP {resp.status_code} at {models_url}"
    except httpx.ConnectError:
        return False, f"Connection refused at {base_url}"
    except httpx.TimeoutException:
        return False, "Timed out — is the endpoint running?"
    except Exception as exc:
        return False, str(exc)


async def _test_n8n(
    webhook_url: str = "",
    base_url: str = "",
    api_key: str = "",
) -> Tuple[bool, str]:
    # Prefer REST API test when base URL + API key are provided
    if base_url and api_key:
        api_url = base_url.rstrip("/") + "/api/v1/workflows"
        try:
            async with httpx.AsyncClient(timeout=8, headers={"X-N8N-API-KEY": api_key}, verify=False) as client:
                resp = await client.get(api_url)
            if resp.status_code == 200:
                data = resp.json()
                count = len(data.get("data", []))
                return True, f"Connected — {count} workflow(s) accessible with this API key"
            if resp.status_code == 401:
                return False, "Authentication failed — check n8n API key"
            if resp.status_code == 403:
                return False, "Forbidden — API key may lack workflow:read permission"
            return False, f"HTTP {resp.status_code} at {api_url}"
        except httpx.ConnectError:
            return False, f"Connection refused at {base_url} — is n8n running?"
        except httpx.TimeoutException:
            return False, "Timed out"
        except Exception as exc:
            return False, str(exc)

    # Fall back to probing the webhook URL
    if webhook_url:
        try:
            async with httpx.AsyncClient(timeout=8, verify=False) as client:
                resp = await client.head(webhook_url)
            # n8n webhooks often return 404 on HEAD — that still means reachable
            if resp.status_code < 500:
                return True, f"n8n reachable (HTTP {resp.status_code}) — enter API key for richer test"
            return False, f"n8n server error: HTTP {resp.status_code}"
        except httpx.ConnectError:
            return False, "Connection refused — is n8n running?"
        except httpx.TimeoutException:
            return False, "Timed out"
        except Exception as exc:
            return False, str(exc)

    return False, "No URL provided"


# ── Router factory ────────────────────────────────────────────────────────────

def create_dashboard_router(config: Any) -> APIRouter:
    """Create the dashboard router with the given config."""
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])

    dash_user: str = getattr(config, "dashboard_user", DEFAULT_USER)
    dash_pass: str = getattr(config, "dashboard_password", DEFAULT_PASS)

    # ── Setup wizard ──────────────────────────────────────────────────────────

    @router.get("/setup", response_class=HTMLResponse)
    async def setup_page(request: Request) -> Any:
        env = _read_env()
        return templates.TemplateResponse("setup.html", {
            "request": request,
            "env": env,
            "setup_complete": _is_setup_complete(),
        })

    @router.post("/setup/test")
    async def test_connection(request: Request) -> JSONResponse:
        """Live connection test called by the setup wizard JS."""
        body: Dict[str, Any] = await request.json()
        service: str = body.get("service", "")

        ok: bool
        detail: str

        if service == "bitcoin":
            raw_port = body.get("port")
            port_val: Optional[int] = int(raw_port) if raw_port else None
            ok, detail = await _test_bitcoin(
                scheme=body.get("scheme", "http"),
                host=body.get("host", "127.0.0.1"),
                port=port_val,
                user=body.get("user", ""),
                password=body.get("password", ""),
                use_tor=bool(body.get("use_tor", False)),
                socks5_proxy=body.get("socks5_proxy", "socks5://127.0.0.1:9050"),
            )
        elif service == "electrs":
            ok, detail = await _test_electrs(
                scheme=body.get("scheme", "http"),
                host=body.get("host", "127.0.0.1"),
                port=int(body.get("port", 3002)),
                use_tor=bool(body.get("use_tor", False)),
                socks5_proxy=body.get("socks5_proxy", "socks5://127.0.0.1:9050"),
                api_prefix=body.get("api_prefix", ""),
            )
        elif service == "mempool":
            ok, detail = await _test_mempool(
                base_url=body.get("base_url", "https://mempool.space"),
                use_tor=bool(body.get("use_tor", False)),
                socks5_proxy=body.get("socks5_proxy", "socks5://127.0.0.1:9050"),
            )
        elif service == "lnbits":
            raw_port = body.get("port")
            ln_port: Optional[int] = int(raw_port) if raw_port else None
            ok, detail = await _test_lnbits(
                scheme=body.get("scheme", "http"),
                host=body.get("host", "127.0.0.1"),
                port=ln_port,
                api_key=body.get("api_key", ""),
            )
        elif service == "vllm":
            ok, detail = await _test_vllm(
                base_url=body.get("base_url", "http://localhost:8000/v1"),
                model=body.get("model", "llama3.1:8b"),
                api_key=body.get("api_key", ""),
            )
        elif service == "n8n":
            ok, detail = await _test_n8n(
                webhook_url=body.get("webhook_url", ""),
                base_url=body.get("base_url", ""),
                api_key=body.get("api_key", ""),
            )
        else:
            return JSONResponse(status_code=400, content={"ok": False, "detail": f"Unknown service: {service}"})

        return JSONResponse(content={"ok": ok, "detail": detail})

    @router.post("/setup/save")
    async def save_setup(request: Request) -> JSONResponse:
        """Write validated config values to the project .env file."""
        body: Dict[str, Any] = await request.json()

        updates: Dict[str, str] = {}

        def _set_secret(key: str, val: Any) -> None:
            """Only write a secret env key if the caller actually provided a value."""
            if val and str(val).strip():
                updates[key] = str(val)

        # Bitcoin
        if body.get("bitcoind_host"):
            updates["BITCOIND_SCHEME"] = body.get("bitcoind_scheme", "http")
            updates["BITCOIND_HOST_IP"] = body["bitcoind_host"]
            updates["BITCOIND_HOST_LOCAL"] = body["bitcoind_host"]
            no_port = bool(body.get("bitcoind_no_port", False))
            updates["BITCOIND_NO_PORT"] = "true" if no_port else "false"
            if not no_port:
                updates["BITCOIND_PORT"] = str(body.get("bitcoind_port", 8332))
            updates["BITCOIND_RPC_USER"] = body.get("bitcoind_user", "bitcoin")
            _set_secret("BITCOIND_RPC_PASS", body.get("bitcoind_pass"))
            btc_tor = bool(body.get("bitcoind_use_tor", False)) or body["bitcoind_host"].endswith(".onion")
            updates["BITCOIND_USE_TOR"] = "true" if btc_tor else "false"
            if btc_tor:
                updates["TOR_SOCKS_PROXY"] = body.get("socks5_proxy", "socks5://127.0.0.1:9050")

        # Electrs
        if body.get("electrs_host"):
            updates["ELECTRS_SCHEME"] = body.get("electrs_scheme", "http")
            updates["ELECTRS_HOST_IP"] = body["electrs_host"]
            updates["ELECTRS_HOST_LOCAL"] = body["electrs_host"]
            updates["ELECTRS_PORT"] = str(body.get("electrs_port", 3002))
            updates["ELECTRS_USE_TOR"] = "true" if body.get("electrs_use_tor") else "false"
            updates["ELECTRS_API_PREFIX"] = body.get("electrs_api_prefix", "")
            if body.get("electrs_use_tor"):
                updates["TOR_SOCKS_PROXY"] = body.get("tor_socks_proxy", "socks5://127.0.0.1:9050")

        # Mempool
        if body.get("mempool_base_url"):
            updates["MEMPOOL_BASE_URL"] = body["mempool_base_url"]
            mempool_tor = bool(body.get("mempool_use_tor", False)) or ".onion" in body["mempool_base_url"]
            updates["MEMPOOL_USE_TOR"] = "true" if mempool_tor else "false"
            if mempool_tor:
                updates.setdefault("TOR_SOCKS_PROXY", body.get("socks5_proxy", "socks5://127.0.0.1:9050"))

        # LNbits
        if body.get("lnbits_host"):
            updates["LNBITS_SCHEME"] = body.get("lnbits_scheme", "http")
            updates["LNBITS_HOST_IP"] = body["lnbits_host"]
            updates["LNBITS_HOST_LOCAL"] = body["lnbits_host"]
            ln_no_port = bool(body.get("lnbits_no_port", False))
            updates["LNBITS_NO_PORT"] = "true" if ln_no_port else "false"
            if not ln_no_port:
                updates["LNBITS_PORT"] = str(body.get("lnbits_port", 5000))
            _set_secret("LNBITS_API_KEY", body.get("lnbits_api_key"))
            if body.get("lnbits_wallet_id"):
                updates["LNBITS_WALLET_ID"] = body["lnbits_wallet_id"]

        # vLLM
        if body.get("vllm_base_url"):
            updates["VLLM_BASE_URL"] = body["vllm_base_url"]
            updates["VLLM_MODEL"] = body.get("vllm_model", "llama3.1:8b")
            _set_secret("VLLM_API_KEY", body.get("vllm_api_key"))

        # n8n
        if body.get("n8n_base_url") or body.get("n8n_webhook_url"):
            if body.get("n8n_base_url"):
                updates["N8N_BASE_URL"] = body["n8n_base_url"]
            _set_secret("N8N_API_KEY", body.get("n8n_api_key"))
            if body.get("n8n_webhook_url"):
                updates["N8N_WEBHOOK_URL"] = body["n8n_webhook_url"]
            _set_secret("N8N_WEBHOOK_SECRET", body.get("n8n_webhook_secret"))
            updates["FUNDING_PROPOSAL_ENABLED"] = "true"

        # Dashboard credentials
        if body.get("dashboard_user"):
            updates["DASHBOARD_USER"] = body["dashboard_user"]
        _set_secret("DASHBOARD_PASSWORD", body.get("dashboard_password"))

        # Mark setup as complete
        updates["SETUP_COMPLETE"] = "true"

        try:
            _write_env(updates)
            logger.info("Setup wizard saved configuration", keys=list(updates.keys()))
            return JSONResponse(content={"ok": True, "detail": "Configuration saved to .env"})
        except Exception as exc:
            logger.error("Setup save failed", error=str(exc))
            return JSONResponse(status_code=500, content={"ok": False, "detail": str(exc)})

    # ── Auth ──────────────────────────────────────────────────────────────────

    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request) -> Any:
        if _is_authenticated(request):
            return RedirectResponse(url="/dashboard/", status_code=303)
        if not _is_setup_complete():
            return RedirectResponse(url="/dashboard/setup", status_code=303)
        return templates.TemplateResponse("login.html", {"request": request})

    @router.post("/login")
    async def do_login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
    ) -> Any:
        # Re-read credentials from .env at login time so setup changes take effect
        env = _read_env()
        real_user = env.get("DASHBOARD_USER", dash_user)
        real_pass = env.get("DASHBOARD_PASSWORD", dash_pass)

        if username == real_user and password == real_pass:
            token = secrets.token_urlsafe(32)
            _sessions[token] = datetime.utcnow() + SESSION_TTL
            resp: Any = RedirectResponse(url="/dashboard/", status_code=303)
            resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=28800)
            return resp
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials. Try again."},
            status_code=401,
        )

    @router.post("/logout")
    async def logout(request: Request) -> Any:
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            _sessions.pop(token, None)
        resp: Any = RedirectResponse(url="/dashboard/login", status_code=303)
        resp.delete_cookie(SESSION_COOKIE)
        return resp

    # ── Main dashboard ────────────────────────────────────────────────────────

    @router.get("/", response_class=HTMLResponse)
    async def dashboard_home(request: Request) -> Any:
        if not _is_authenticated(request):
            return RedirectResponse(url="/dashboard/login", status_code=303)
        try:
            from .. import __version__ as _version
            version: str = _version
        except Exception:
            version = "0.2.0"
        return templates.TemplateResponse(
            "dashboard.html",
            {"request": request, "version": version},
        )

    @router.get("/reconfigure", response_class=HTMLResponse)
    async def reconfigure(request: Request) -> Any:
        if not _is_authenticated(request):
            return RedirectResponse(url="/dashboard/login", status_code=303)
        env = _read_env()
        return templates.TemplateResponse("setup.html", {
            "request": request,
            "env": env,
            "setup_complete": True,  # already set up, this is a re-run
        })

    # ── Dashboard Data API (authenticated, consumed by frontend JS) ───────────

    @router.get("/api/health")
    async def dashboard_health(request: Request) -> JSONResponse:
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        # Each check runs in a thread (blocking sync adapters) with a hard 20-second
        # deadline so offline services never stall the dashboard.
        # We create a fresh Config() in each thread so that wizard-saved .env changes
        # are picked up immediately without restarting the app.
        CHECK_TIMEOUT = 20.0

        def _fresh_config() -> Any:
            from ..config import Config as _Config
            return _Config()

        def _check_bitcoin() -> Dict[str, Any]:
            from ..adapters.bitcoind import BitcoinAdapter
            btc = BitcoinAdapter(_fresh_config())
            try:
                info = btc.get_blockchain_info()
                return {
                    "bitcoin_node": "online",
                    "block_height": info.get("blocks", 0),
                    "chain": info.get("chain", "unknown"),
                    "synced": info.get("blocks", 0) == info.get("headers", 0),
                    "difficulty": info.get("difficulty", 0),
                }
            finally:
                btc.close()

        def _check_electrs() -> Dict[str, Any]:
            from ..adapters.electrs import ElectrsAdapter
            elec = ElectrsAdapter(_fresh_config())
            try:
                tip = elec.get_tip_height()
                return {"electrs": "online", "electrs_tip": tip}
            finally:
                elec.close()

        def _check_mempool() -> Dict[str, Any]:
            from ..adapters.mempool import MempoolAdapter
            mem = MempoolAdapter()
            try:
                fee_data = mem.get_fee_estimates()
                return {
                    "mempool": "online",
                    "fee_fastest": fee_data.get("fastestFee", 0),
                    "fee_half_hour": fee_data.get("halfHourFee", 0),
                    "fee_hour": fee_data.get("hourFee", 0),
                }
            finally:
                mem.close()

        def _check_lnbits() -> Dict[str, Any]:
            from ..adapters.lnbits import LNbitsAdapter
            ln = LNbitsAdapter(_fresh_config())
            try:
                balance = ln.get_wallet_balance()
                return {"lnbits": "online", "ln_balance_sats": balance}
            finally:
                ln.close()

        async def _run(fn: Any, error_key: str, status_key: str) -> Dict[str, Any]:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(fn), timeout=CHECK_TIMEOUT
                )
                return result
            except asyncio.TimeoutError:
                return {status_key: "offline", error_key: f"Timed out after {CHECK_TIMEOUT:.0f}s"}
            except Exception as exc:
                return {status_key: "offline", error_key: str(exc)}

        btc_r, elec_r, mem_r, ln_r = await asyncio.gather(
            _run(_check_bitcoin, "bitcoin_node_error", "bitcoin_node"),
            _run(_check_electrs, "electrs_error",      "electrs"),
            _run(_check_mempool, "mempool_error",       "mempool"),
            _run(_check_lnbits,  "lnbits_error",        "lnbits"),
        )

        services: Dict[str, Any] = {"api": "online"}
        for chunk in (btc_r, elec_r, mem_r, ln_r):
            services.update(chunk)

        return JSONResponse(
            content={"services": services, "timestamp": datetime.utcnow().isoformat()}
        )

    @router.get("/api/proposals")
    async def list_proposals(request: Request) -> JSONResponse:
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        try:
            from ..funding.manager import FundingProposalManager
            mgr = FundingProposalManager(config)  # type: ignore[arg-type]
            raw = mgr.list_proposals()
            proposals = [
                p.model_dump() if hasattr(p, "model_dump") else (p.dict() if hasattr(p, "dict") else p)
                for p in raw
            ]
            return JSONResponse(content={"proposals": proposals, "count": len(proposals)})
        except Exception as exc:
            return JSONResponse(content={"proposals": [], "count": 0, "error": str(exc)})

    @router.post("/api/agent/start")
    async def start_agent(request: Request) -> JSONResponse:
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return JSONResponse(content={
            "status": "requested",
            "message": "Agent start queued. Use `falconer ai-start` for persistent operation.",
        })

    @router.post("/api/agent/stop")
    async def stop_agent(request: Request) -> JSONResponse:
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return JSONResponse(content={"status": "requested", "message": "Agent stop queued."})

    @router.get("/api/config")
    async def get_config(request: Request) -> JSONResponse:
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        def _mask(val: Any) -> str:
            if not val:
                return ""
            s = str(val)
            return s[:4] + "****" if len(s) > 4 else "****"

        cfg: Dict[str, Any] = {}
        for field in ["bitcoin_rpc_host", "bitcoin_rpc_port", "bitcoin_rpc_user",
                      "electrs_url", "mempool_url", "lnbits_url",
                      "llm_base_url", "llm_model", "openclaw_enabled", "log_level"]:
            val = getattr(config, field, None)
            cfg[field] = _mask(val) if field == "bitcoin_rpc_user" else val
        return JSONResponse(content={"config": cfg})

    @router.get("/api/config/editable")
    async def get_editable_config(request: Request) -> JSONResponse:
        """Return current .env values for the editable config form.
        Secret fields are returned empty — the user must retype to change them."""
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        env = _read_env()
        return JSONResponse(content={
            "bitcoind_scheme":    env.get("BITCOIND_SCHEME",    "http"),
            "bitcoind_host":      env.get("BITCOIND_HOST_IP",   ""),
            "bitcoind_port":      env.get("BITCOIND_PORT",      "8332"),
            "bitcoind_no_port":   env.get("BITCOIND_NO_PORT",   "false"),
            "bitcoind_user":      env.get("BITCOIND_RPC_USER",  ""),
            "bitcoind_use_tor":   env.get("BITCOIND_USE_TOR",   "false"),
            "electrs_scheme":      env.get("ELECTRS_SCHEME",      "http"),
            "electrs_host":        env.get("ELECTRS_HOST_IP",     ""),
            "electrs_port":        env.get("ELECTRS_PORT",        "3002"),
            "electrs_use_tor":     env.get("ELECTRS_USE_TOR",     "false"),
            "electrs_api_prefix":  env.get("ELECTRS_API_PREFIX",  ""),
            "tor_socks_proxy":    env.get("TOR_SOCKS_PROXY",    "socks5://127.0.0.1:9050"),
            "mempool_base_url":   env.get("MEMPOOL_BASE_URL",   "https://mempool.space"),
            "mempool_use_tor":    env.get("MEMPOOL_USE_TOR",    "false"),
            "lnbits_scheme":      env.get("LNBITS_SCHEME",      "http"),
            "lnbits_host":        env.get("LNBITS_HOST_IP",     ""),
            "lnbits_port":        env.get("LNBITS_PORT",        "5000"),
            "lnbits_no_port":     env.get("LNBITS_NO_PORT",     "false"),
            "lnbits_wallet_id":   env.get("LNBITS_WALLET_ID",   ""),
            "vllm_base_url":      env.get("VLLM_BASE_URL",      ""),
            "vllm_model":         env.get("VLLM_MODEL",         ""),
            "n8n_base_url":       env.get("N8N_BASE_URL",       ""),
            "n8n_webhook_url":    env.get("N8N_WEBHOOK_URL",    ""),
            "log_level":          env.get("LOG_LEVEL",           "INFO"),
            "dashboard_user":     env.get("DASHBOARD_USER",     "admin"),
            "funding_proposal_enabled": env.get("FUNDING_PROPOSAL_ENABLED", "false"),
            # Secrets: return empty — user retypes to update
            "bitcoind_pass":      "",
            "lnbits_api_key":     "",
            "vllm_api_key":       "",
            "n8n_api_key":        "",
            "n8n_webhook_secret": "",
            "dashboard_password": "",
        })

    @router.post("/api/save-config")
    async def save_config(request: Request) -> JSONResponse:
        """Write edited config values to the project .env file."""
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        body: Dict[str, Any] = await request.json()

        # Map form field → env key(s)
        SAFE: Dict[str, Any] = {
            "bitcoind_scheme":  "BITCOIND_SCHEME",
            "bitcoind_host":    ["BITCOIND_HOST_IP", "BITCOIND_HOST_LOCAL"],
            "bitcoind_port":    "BITCOIND_PORT",
            "bitcoind_user":    "BITCOIND_RPC_USER",
            "electrs_scheme":      "ELECTRS_SCHEME",
            "electrs_host":        ["ELECTRS_HOST_IP", "ELECTRS_HOST_LOCAL"],
            "electrs_port":        "ELECTRS_PORT",
            "electrs_use_tor":     "ELECTRS_USE_TOR",
            "electrs_api_prefix":  "ELECTRS_API_PREFIX",
            "tor_socks_proxy":  "TOR_SOCKS_PROXY",
            "lnbits_scheme":    "LNBITS_SCHEME",
            "lnbits_host":      ["LNBITS_HOST_IP", "LNBITS_HOST_LOCAL"],
            "lnbits_port":      "LNBITS_PORT",
            "lnbits_wallet_id": "LNBITS_WALLET_ID",
            "vllm_base_url":    "VLLM_BASE_URL",
            "vllm_model":       "VLLM_MODEL",
            "log_level":        "LOG_LEVEL",
            "dashboard_user":   "DASHBOARD_USER",
            "n8n_webhook_url":  "N8N_WEBHOOK_URL",
            "funding_proposal_enabled": "FUNDING_PROPOSAL_ENABLED",
        }
        SECRET: Dict[str, str] = {
            "bitcoind_pass":      "BITCOIND_RPC_PASS",
            "lnbits_api_key":     "LNBITS_API_KEY",
            "vllm_api_key":       "VLLM_API_KEY",
            "n8n_webhook_secret": "N8N_WEBHOOK_SECRET",
            "dashboard_password": "DASHBOARD_PASSWORD",
        }

        updates: Dict[str, str] = {}
        for field, env_key in SAFE.items():
            val = body.get(field)
            if val is not None:
                str_val = str(val)
                if isinstance(env_key, list):
                    for k in env_key:
                        updates[k] = str_val
                else:
                    updates[env_key] = str_val

        for field, env_key in SECRET.items():
            val = body.get(field, "")
            if val and str(val).strip():  # only write if user typed something
                updates[env_key] = str(val)

        if not updates:
            return JSONResponse(content={"ok": False, "detail": "Nothing to save."})

        try:
            _write_env(updates)
            logger.info("Dashboard config saved", keys=list(updates.keys()))
            return JSONResponse(content={"ok": True, "detail": f"Saved {len(updates)} value(s) to .env"})
        except Exception as exc:
            logger.error("Config save failed", error=str(exc))
            return JSONResponse(status_code=500, content={"ok": False, "detail": str(exc)})

    @router.get("/api/fee-brief")
    async def fee_brief(request: Request) -> JSONResponse:
        if not _is_authenticated(request):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        try:
            from ..tasks.fee_brief import FeeBriefTask
            task = FeeBriefTask(config)  # type: ignore[arg-type]
            brief = task.run()
            return JSONResponse(content=brief if isinstance(brief, dict) else {"brief": str(brief)})
        except Exception as exc:
            return JSONResponse(content={"error": str(exc)})

    return router
