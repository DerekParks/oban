# Oban

Web dashboard for [Obsidian](https://obsidian.md/) [Kanban](https://github.com/mgmeyers/obsidian-kanban) boards.

View in-progress tasks across all boards, drag tasks between boards, quick-add from the dashboard, and click through to full board views. Live updates via WebSocket when files change on disk.

**Vibe coded** with Claude Code.

## Setup

```bash
cp .env.example .env        # edit with your paths
cp oban.boards.example.json oban.boards.json  # optional per-board column config
```

## Run

```bash
# Docker
docker compose up -d

# Dev
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
cd frontend && npm install && npm run dev
```

## Config

| Variable | Description |
|---|---|
| `OBAN_VAULT_DIR` | Path to Obsidian vault |
| `OBAN_KANBAN_DIR` | Path to Kanbans folder within vault |
| `OBAN_OBSIDIAN_VAULT` | Vault name (for `obsidian://` links) |
| `OBAN_PINNED_BOARD` | Board pinned to top of dashboard |
| `OBAN_STRIP_SUFFIX` | Suffix stripped from filenames |
| `OBAN_DEFAULT_COLUMN` | Default dashboard column index (default: 1) |

See `docker-compose.example.yml` for deployment reference.
