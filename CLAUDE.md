# LangCon

Shared project instructions:

@AGENTS.md

## Claude Code notes

- `AGENTS.md` is the source of truth for project facts. Update it there (not here) when behavior changes, so other agents stay in sync. Keep this section for Claude-specific workflow only.
- Use the existing virtual environment: `.venv/bin/python` (Python 3.13). Run commands from the repository root.
- Never read, print, or edit `.env`; use `.env.example` for configuration shape. Keep student data, database files, and `tmp_emails/` contents out of tool output.
- Verify Python changes with, scoped to touched files:
  - `.venv/bin/python -m black --check <paths>`
  - `.venv/bin/python -m ruff check --no-fix <paths>` (Ruff auto-fixes by default in this repo)
  - `.venv/bin/python -m pytest <relevant test paths>`
- For model changes, also run `.venv/bin/python src/manage.py makemigrations --check --dry-run`.
- For template/style changes, run `npm run tw:build`.
- Mock OpenAI calls (`src/assessments/services/`) in tests; never make live API calls.
