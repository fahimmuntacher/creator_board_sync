# creator_board_sync

Personal tool that reads my own Pinterest boards, saves the pins locally,
and uses a local Ollama model to draft captions for manual review.

## Setup

1. Copy `.env.example` to `.env` and fill in the Pinterest app ID and secret.
2. Add `http://localhost:8085/` as a redirect URI in the Pinterest app.
3. Pull the vision model: `ollama pull gemma3:4b`

No Python packages are needed (standard library only, Python 3.10+).

## Usage

```
python3 -m pinpost auth                          # log in to Pinterest
python3 -m pinpost boards                        # list boards
python3 -m pinpost sync --board "Name" --limit 5 # download new pins
python3 -m pinpost caption                       # describe + caption with Ollama
python3 -m pinpost list                          # captions waiting for review
```

Downloaded media and the SQLite database live in `data/` (not committed).
