"""Ollama: look at the image, then write captions."""
import base64
import json
import urllib.request
from pathlib import Path

from . import config

CAPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "caption_instagram": {"type": "string"},
        "caption_facebook": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["caption_instagram", "caption_facebook", "hashtags"],
}


def _chat(model: str, message: dict, fmt: dict | None = None) -> str:
    body = {"model": model, "messages": [message], "stream": False}
    if fmt:
        body["format"] = fmt
    req = urllib.request.Request(
        f"{config.OLLAMA_URL}/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    # First call loads the model into VRAM, which can be slow.
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())["message"]["content"]


def describe_image(path: str | Path) -> str:
    image = base64.b64encode(Path(path).read_bytes()).decode()
    return _chat(config.VISION_MODEL, {
        "role": "user",
        "content": (
            "Describe this image in 2-3 factual sentences: the subject, setting, "
            "mood and colors. Mention any visible text. No opinions."
        ),
        "images": [image],
    }).strip()


def write_captions(vision_notes: str, title: str = "", description: str = "") -> dict:
    prompt = f"""Write social media captions for an image.

What the image shows: {vision_notes}
Original title: {title or "(none)"}
Original description: {description or "(none)"}

Style: {config.CAPTION_STYLE}
- caption_instagram: 1-2 sentences.
- caption_facebook: 1-3 sentences, slightly more conversational.
- hashtags: 5-8 relevant tags, lowercase, without the # sign.
Do not claim the image is yours. Do not put hashtags inside the captions."""
    raw = _chat(config.CAPTION_MODEL, {"role": "user", "content": prompt}, CAPTION_SCHEMA)
    data = json.loads(raw)
    data["hashtags"] = [t.lstrip("#").replace(" ", "") for t in data["hashtags"] if t.strip()]
    return data
