# Aspirant

Daily current affairs for APPSC Group 1 & Group 2 (Andhra Pradesh) aspirants.

Static site on GitHub Pages. A GitHub Action runs every 30 minutes, gathers headlines from RSS feeds
(`scripts/update.py`), optionally writes exam notes with Claude, and commits `data/affairs.json`.
The page fetches that file on open, every minute, and when you return to the tab.

## Setup
1. Repo → Settings → Pages → Deploy from branch → `main` / root.
2. Settings → Actions → General → Workflow permissions → Read and write.
3. (Recommended) Settings → Secrets → Actions → add `ANTHROPIC_API_KEY` for AI exam notes.
   Without it, items appear as headlines with a link and no detailed notes.
4. Actions tab → "Update current affairs" → Run workflow once to test.

Edit `FEEDS` in `scripts/update.py` to add sources. `MAX_ENRICH` limits AI calls per run (default 10).
