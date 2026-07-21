# ArtGen

AI-powered illustrated article pipeline — FastAPI backend + vanilla HTML/CSS/JS frontend.

## How I work
- I commit and push to GitHub (`origin main`) freely — no need to ask permission for pushes
- I keep the server running while developing (`python main.py`)
- I test changes in the browser before claiming they work

## Project structure
- `main.py` — entire FastAPI backend (routes, state, API calls)
- `static/` — frontend (vanilla HTML/CSS/JS, no framework)
- `data/` — runtime project data (gitignored)
- `log/` — runtime logs (gitignored)
- `artg/` — Python virtualenv (gitignored)
- `docs/` — design specs and plans
- `reference docs/` — API documentation for Anthropic and Gemini

## Key patterns
- Backend state per-project under `data/<dir_name>/`
- Project index at `data/projects.json`
- API keys stored in project settings, configurable via Settings page
- Step pages gated behind project existence (redirect to `/` if no project)
