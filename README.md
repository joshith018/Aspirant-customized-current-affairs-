# Aspirant

Daily current affairs for APPSC Group 1 & Group 2 (Andhra Pradesh) aspirants.

Static site on GitHub Pages. A GitHub Action runs every 30 minutes, gathers headlines from RSS feeds
(`scripts/update.py`), optionally writes exam notes with Claude, and commits `data/affairs.json`.
The page fetches that file on open, every minute, and when you return to the tab.
