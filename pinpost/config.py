"""Settings, read from the .env file in the project root (plus real env vars)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "pinpost.db"
TOKEN_PATH = DATA_DIR / "pinterest_token.json"


def _load_env_file() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_env_file()

PINTEREST_APP_ID = os.environ.get("PINTEREST_APP_ID", "")
PINTEREST_APP_SECRET = os.environ.get("PINTEREST_APP_SECRET", "")
# Optional shortcut: a token generated in the Pinterest developer dashboard.
PINTEREST_ACCESS_TOKEN = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_REDIRECT_PORT = int(os.environ.get("PINTEREST_REDIRECT_PORT", "8085"))
PINTEREST_REDIRECT_URI = f"http://localhost:{PINTEREST_REDIRECT_PORT}/"

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
VISION_MODEL = os.environ.get("VISION_MODEL", "gemma3:4b")
CAPTION_MODEL = os.environ.get("CAPTION_MODEL", "llama3.1:8b")
CAPTION_STYLE = os.environ.get(
    "CAPTION_STYLE", "friendly, short, natural; no clickbait, at most one emoji"
)

DATA_DIR.mkdir(exist_ok=True)
MEDIA_DIR.mkdir(exist_ok=True)
