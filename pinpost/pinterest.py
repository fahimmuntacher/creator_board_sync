"""Pinterest API v5: login, list boards and pins, download media."""
import base64
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from . import config

API = "https://api.pinterest.com/v5"
SCOPES = "boards:read,pins:read,user_accounts:read"
USER_AGENT = "pinpost/0.1"


class PinterestError(RuntimeError):
    pass


def _request(url: str, *, headers: dict, data: bytes | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        raise PinterestError(f"Pinterest API {e.code} for {url}: {body}") from e


# ---------- auth ----------

def _token_request(form: dict) -> dict:
    basic = base64.b64encode(
        f"{config.PINTEREST_APP_ID}:{config.PINTEREST_APP_SECRET}".encode()
    ).decode()
    token = _request(
        f"{API}/oauth/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=urllib.parse.urlencode(form).encode(),
    )
    token["expires_at"] = time.time() + token.get("expires_in", 0)
    # A refresh response has no refresh_token; keep the old one.
    if "refresh_token" not in token and config.TOKEN_PATH.exists():
        old = json.loads(config.TOKEN_PATH.read_text())
        token["refresh_token"] = old.get("refresh_token")
    config.TOKEN_PATH.write_text(json.dumps(token))
    config.TOKEN_PATH.chmod(0o600)
    return token


def login() -> None:
    """Browser OAuth flow; saves the token under data/."""
    if not (config.PINTEREST_APP_ID and config.PINTEREST_APP_SECRET):
        raise PinterestError("Set PINTEREST_APP_ID and PINTEREST_APP_SECRET in .env first.")
    state = secrets.token_urlsafe(16)
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h3>pinpost: you can close this tab.</h3>")

        def log_message(self, *args):
            pass

    auth_url = "https://www.pinterest.com/oauth/?" + urllib.parse.urlencode({
        "client_id": config.PINTEREST_APP_ID,
        "redirect_uri": config.PINTEREST_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    })
    server = HTTPServer(("localhost", config.PINTEREST_REDIRECT_PORT), Handler)
    print(f"Open this URL to authorize (trying to open your browser):\n{auth_url}")
    webbrowser.open(auth_url)
    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()

    if result.get("state") != state or "code" not in result:
        raise PinterestError(f"Authorization failed: {result}")
    _token_request({
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": config.PINTEREST_REDIRECT_URI,
    })
    print("Logged in to Pinterest.")


def _access_token() -> str:
    if config.PINTEREST_ACCESS_TOKEN:
        return config.PINTEREST_ACCESS_TOKEN
    if not config.TOKEN_PATH.exists():
        raise PinterestError("Not logged in. Run: python3 -m pinpost auth")
    token = json.loads(config.TOKEN_PATH.read_text())
    if token["expires_at"] < time.time() + 60:
        token = _token_request({
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        })
    return token["access_token"]


# ---------- reading ----------

def _paged(path: str, **params):
    """Yield every item from a paginated endpoint."""
    headers = {"Authorization": f"Bearer {_access_token()}"}
    params = {"page_size": 100, **params}
    while True:
        page = _request(f"{API}{path}?{urllib.parse.urlencode(params)}", headers=headers)
        yield from page.get("items", [])
        if not page.get("bookmark"):
            return
        params["bookmark"] = page["bookmark"]


def boards():
    return _paged("/boards")


def board_pins(board_id: str):
    return _paged(f"/boards/{board_id}/pins")


def best_image_url(pin: dict) -> str | None:
    """Largest image for the pin. For video pins this is the cover frame."""
    media = pin.get("media") or {}
    images = media.get("images") or {}
    if images:
        def width(key: str) -> int:
            try:
                return int(key.split("x")[0])
            except ValueError:
                return 0
        return images[max(images, key=width)]["url"]
    return media.get("cover_image_url")


def download(url: str, pin_id: str) -> Path:
    suffix = Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
    dest = config.MEDIA_DIR / f"{pin_id}{suffix}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())
    return dest
