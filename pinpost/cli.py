"""Command line: python3 -m pinpost <command>"""
import argparse
import sys

from . import brain, db, pinterest


def cmd_auth(args) -> None:
    pinterest.login()


def cmd_boards(args) -> None:
    for board in pinterest.boards():
        print(f"{board['id']:>20}  {board.get('pin_count', '?'):>5} pins  {board['name']}")


def cmd_sync(args) -> None:
    """Download new pins from one board (or all boards)."""
    conn = db.connect()
    wanted = args.board.lower() if args.board else None
    boards = [
        b for b in pinterest.boards()
        if not wanted or wanted in (b["name"].lower(), b["id"])
    ]
    if not boards:
        sys.exit(f"No board matches {args.board!r}. Run 'boards' to see names.")

    added = 0
    for board in boards:
        for pin in pinterest.board_pins(board["id"]):
            if args.limit and added >= args.limit:
                break
            if db.has_pin(conn, pin["id"]):
                continue
            url = pinterest.best_image_url(pin)
            if not url:
                print(f"  skip {pin['id']}: no image available")
                continue
            try:
                path = pinterest.download(url, pin["id"])
            except OSError as e:
                print(f"  skip {pin['id']}: download failed ({e})")
                continue
            db.insert_pin(conn, {
                "id": pin["id"],
                "board_id": board["id"],
                "board_name": board["name"],
                "title": pin.get("title") or "",
                "description": pin.get("description") or "",
                "source_link": pin.get("link") or "",
                "pin_url": f"https://www.pinterest.com/pin/{pin['id']}/",
                "media_type": (pin.get("media") or {}).get("media_type", "image"),
                "media_url": url,
                "local_path": str(path),
            })
            added += 1
            print(f"  + {pin['id']}  [{board['name']}]  {(pin.get('title') or '')[:50]}")
    print(f"{added} new pin(s) downloaded.")


def cmd_caption(args) -> None:
    """Describe and caption fetched pins. Two passes so each model loads once."""
    conn = db.connect()
    pins = db.pins_by_status(conn, "fetched", args.limit)
    if not pins:
        print("Nothing to caption. Run 'sync' first.")
        return

    for pin in pins:
        if pin["vision_notes"]:
            continue
        try:
            notes = brain.describe_image(pin["local_path"])
            db.update_pin(conn, pin["id"], vision_notes=notes, error=None)
            print(f"  seen {pin['id']}: {notes[:80]}")
        except Exception as e:
            db.update_pin(conn, pin["id"], error=f"vision: {e}")
            print(f"  FAILED vision {pin['id']}: {e}")

    done = 0
    for pin in db.pins_by_status(conn, "fetched", args.limit):
        if not pin["vision_notes"]:
            continue
        try:
            caps = brain.write_captions(pin["vision_notes"], pin["title"], pin["description"])
            db.update_pin(
                conn, pin["id"],
                caption_ig=caps["caption_instagram"],
                caption_fb=caps["caption_facebook"],
                hashtags=" ".join("#" + t for t in caps["hashtags"]),
                status="captioned",
                error=None,
            )
            done += 1
            print(f"  captioned {pin['id']}: {caps['caption_instagram'][:80]}")
        except Exception as e:
            db.update_pin(conn, pin["id"], error=f"caption: {e}")
            print(f"  FAILED caption {pin['id']}: {e}")
    print(f"{done} pin(s) captioned and waiting for review.")


def cmd_list(args) -> None:
    conn = db.connect()
    pins = db.pins_by_status(conn, args.status)
    for pin in pins:
        print(f"\n[{pin['id']}] {pin['board_name']} - {pin['media_type']}")
        print(f"  file:     {pin['local_path']}")
        print(f"  source:   {pin['source_link'] or pin['pin_url']}")
        if pin["caption_ig"]:
            print(f"  IG:       {pin['caption_ig']}")
            print(f"  FB:       {pin['caption_fb']}")
            print(f"  tags:     {pin['hashtags']}")
        if pin["error"]:
            print(f"  error:    {pin['error']}")
    print(f"\n{len(pins)} pin(s) with status '{args.status}'.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="pinpost")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth", help="log in to Pinterest").set_defaults(func=cmd_auth)
    sub.add_parser("boards", help="list your boards").set_defaults(func=cmd_boards)

    p = sub.add_parser("sync", help="download new pins")
    p.add_argument("--board", help="board name or id (default: all boards)")
    p.add_argument("--limit", type=int, help="max new pins to download")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("caption", help="describe and caption fetched pins with Ollama")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_caption)

    p = sub.add_parser("list", help="show pins by status")
    p.add_argument("--status", default="captioned",
                   choices=["fetched", "captioned", "approved", "skipped", "posted"])
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    try:
        args.func(args)
    except pinterest.PinterestError as e:
        sys.exit(str(e))
