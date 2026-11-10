"""SQLite store: one row per pin, tracking it from fetch to post."""
import sqlite3

from . import config

# status: fetched -> captioned -> approved / skipped -> posted
SCHEMA = """
CREATE TABLE IF NOT EXISTS pins (
    id            TEXT PRIMARY KEY,
    board_id      TEXT,
    board_name    TEXT,
    title         TEXT,
    description   TEXT,
    source_link   TEXT,
    pin_url       TEXT,
    media_type    TEXT,
    media_url     TEXT,
    local_path    TEXT,
    vision_notes  TEXT,
    caption_ig    TEXT,
    caption_fb    TEXT,
    hashtags      TEXT,
    status        TEXT NOT NULL DEFAULT 'fetched',
    error         TEXT,
    fetched_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    posted_at     TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def has_pin(conn, pin_id: str) -> bool:
    return conn.execute("SELECT 1 FROM pins WHERE id = ?", (pin_id,)).fetchone() is not None


def insert_pin(conn, pin: dict) -> None:
    cols = ", ".join(pin)
    marks = ", ".join("?" for _ in pin)
    conn.execute(f"INSERT INTO pins ({cols}) VALUES ({marks})", tuple(pin.values()))
    conn.commit()


def update_pin(conn, pin_id: str, **fields) -> None:
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE pins SET {sets} WHERE id = ?", (*fields.values(), pin_id))
    conn.commit()


def pins_by_status(conn, status: str, limit: int | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM pins WHERE status = ? ORDER BY fetched_at"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, (status,)).fetchall()
