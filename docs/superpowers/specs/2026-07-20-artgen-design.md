# ArtGen: Automated Article Generator — Design Spec

**Date**: 2026-07-20
**Status**: Approved

---

## Overview

A 5-step AI pipeline local web app that turns a topic into a fully illustrated, styled article. Each step is an independent panel with its own route, data store, and API calls. The user can jump between steps freely, inspect/edit/re-run any step in isolation.

**Tech stack**: Python FastAPI backend + vanilla HTML/CSS/JS frontend, served locally. Cross-platform (Windows/Linux).

---

## Architecture

```
artgen/
├── main.py              # FastAPI entry point, serves static files + API routes
├── requirements.txt     # fastapi, uvicorn, httpx, pydantic
├── static/
│   ├── css/style.css
│   ├── js/
│   │   ├── api.js       # Shared fetch wrapper for backend API calls
│   │   ├── settings.js  # API key management UI
│   │   ├── log.js       # System log panel (persistent, user-visible)
│   │   ├── step1.js     # Subtopic Planning
│   │   ├── step2.js     # Subtopic Research
│   │   ├── step3.js     # Article Draft
│   │   ├── step4.js     # Style Rewrite
│   │   └── step5.js     # Image Generation (later)
│   ├── step1.html       # One page per step (separate routes)
│   ├── step2.html
│   ├── step3.html
│   ├── step4.html
│   ├── step5.html
│   └── settings.html    # API keys + global config
├── data/                # JSON persistence directory
│   └── <project-name>/
│       ├── project.json # Project metadata + current state
│       ├── step1.json   # Topic + subtopics
│       ├── step2.json   # Research results per subtopic
│       ├── step3.json   # Draft article
│       ├── step4.json   # Styled article
│       └── step5.json   # Illustrated article (future)
└── log/                 # System log files
    └── <project-name>.log
```

### Navigation

Left sidebar with links to each step + Settings + System Log. Each step is its own route:
- `/step/1` — Subtopic Planning
- `/step/2` — Subtopic Research
- `/step/3` — Article Draft
- `/step/4` — Style Rewrite
- `/step/5` — Image Generation (later)
- `/settings` — API keys + global config
- `/log` — Full system log view

A mini log widget is visible in the bottom bar from every page.

---

## Backend API Endpoints

### Settings
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Get current settings (API keys masked) |
| PUT | `/api/settings` | Update settings |
| POST | `/api/settings/validate/anthropic` | Test Anthropic API key with a minimal call |
| POST | `/api/settings/validate/gemini` | Test Gemini API key with a minimal call |

### Project Management
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/project` | Get current project metadata + all step statuses |
| POST | `/api/project/new` | Create a new project |
| POST | `/api/project/save` | Persist all project state to disk |
| GET | `/api/project/load` | Load last project on startup |

### Step Data (N = 1-5)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/step/{N}/data` | Get step N's stored data (input + output) |
| PUT | `/api/step/{N}/data` | Update step N's data (manual edit) |
| POST | `/api/step/{N}/run` | Execute step N's API call(s) |

### Step Params (per-step model/parameter config)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/step/{N}/params` | Get step N's model, temperature, max_tokens, system prompt |
| PUT | `/api/step/{N}/params` | Update step N's parameters |

### System Log
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/log` | Get full log for current project |
| GET | `/api/log/stream` | SSE stream of live log entries |

---

## Data Models

### Step 1 Data (`step1.json`)
```json
{
  "topic": "",
  "subtopic_count": 5,
  "subtopics": [
    {"id": 1, "title": ""},
    {"id": 2, "title": ""}
  ],
  "status": "idle",       // idle | running | completed | failed
  "last_run": null,       // ISO timestamp
  "error": null           // error message if failed
}
```

### Step 2 Data (`step2.json`)
```json
{
  "research_results": [
    {
      "subtopic_id": 1,
      "subtopic_title": "",
      "summary": "",
      "sources": [{"title": "", "url": ""}],
      "status": "idle",    // per-subtopic status
      "error": null
    }
  ],
  "status": "idle",
  "last_run": null,
  "error": null
}
```

### Step 3 Data (`step3.json`)
```json
{
  "draft_article": "",
  "status": "idle",
  "last_run": null,
  "error": null
}
```

### Step 4 Data (`step4.json`)
```json
{
  "styled_article": "",
  "status": "idle",
  "last_run": null,
  "error": null
}
```

### Step Params (per step)
```json
{
  "model": "claude-haiku-4-5",
  "temperature": 1.0,
  "max_tokens": 4096,
  "system_prompt": "You are a content planner...",
  "custom_params": {}
}
```

---

## Step Details

### Step 1 — Subtopic Planning
- **Model**: Anthropic (default: `claude-haiku-4-5`, user-selectable)
- **Input**: Topic string + subtopic count from user
- **API call**: 1 call to Anthropic `/v1/messages` with structured output (JSON schema)
- **System prompt**: instructs the model to generate exactly N subtopics
- **Output**: List of N subtopic titles as JSON
- **UI**: Topic text input + number input + model selector + params panel + "Go" button + output list (editable)

### Step 2 — Subtopic Research
- **Model**: Gemini with Google Search grounding (user-selectable Gemini model)
- **Input**: Subtopic list from Step 1
- **API calls**: One per subtopic, sequential (user can trigger individually)
- **Behavior**: Uses Gemini Interactions API with `google_search` tool for grounded research
- **Error handling**: Failed subtopics surface clearly, logged to system log, user manually re-triggers
- **Output**: Research summary per subtopic with source citations
- **UI**: List of subtopics with individual "Research" buttons, status per subtopic, expandable results with citations

### Step 3 — Article Draft
- **Model**: Anthropic (default: `claude-sonnet-5`, user-selectable)
- **Input**: All Step 2 research results
- **API call**: 1 call synthesizing all research into a draft article
- **Output**: Draft article text
- **UI**: Research preview + "Generate Draft" button + editable article textarea

### Step 4 — Style Rewrite
- **Model**: Anthropic (default: `claude-sonnet-5`, user-selectable)
- **Input**: Draft article from Step 3
- **API call**: 1 call rewriting in Cracked.com style
- **System prompt**: Pre-loaded with detailed Cracked.com style instructions (irreverent, funny, listicle-friendly, conversational)
- **Output**: Styled article
- **UI**: Draft preview + "Rewrite" button + styled article display + edit capability

### Step 5 — Image Generation (FUTURE — DO NOT BUILD YET)
- Will use Gemini image generation
- Input: styled article from Step 4
- Output: illustrated article with images inserted at model-determined positions

---

## Cross-Cutting Features

### API Key Management
- Stored in `data/settings.json` (Anthropic API key, Gemini API key)
- Keys are masked in UI after entry
- Validate button for each key (sends a minimal test call)
- Keys persist across sessions

### System Log
- Appends to `log/<project-name>.log`
- Entries are timestamped JSON: `{"timestamp": "...", "level": "INFO|ERROR|WARN", "step": 1, "message": "..."}`
- Live SSE stream available to the frontend
- Mini log widget in bottom bar shows last N entries
- Full log view at `/log`

### Prompt & Parameter Transparency
- Every step has a collapsible "Parameters" panel showing:
  - Current system prompt (editable textarea)
  - Model selector (dropdown)
  - Temperature slider (0.0–1.0)
  - Max tokens input
- Before running, the user can inspect and modify all params

### Project Persistence
- Save: manual save button + auto-save on step completion
- Load: on startup, auto-opens the last project from `data/last_project.txt`
- Each step's data is its own JSON file for independent reading/writing

### Error Handling
- No automatic model fallback — ever
- Failed API calls return error to UI and log to system log
- User decides whether to edit params and re-run

---

## Build Order

1. **Step 1 only** — Subtopic Planning. Stop and wait for testing.
2. **Step 2** — Subtopic Research. Stop and wait.
3. **Step 3** — Article Draft. Stop and wait.
4. **Step 4** — Style Rewrite. Stop and wait.
5. **Step 5** — Image Generation. Only on explicit instruction.

---

## First Launch & Project Management

### First Launch
On first launch (no `data/last_project.txt`), the app redirects to a new-project page:
- User enters a project name
- A new project directory is created under `data/<project-name>/`
- Settings are checked — if API keys are missing, redirect to `/settings` with a prompt

### Project Creation/Switching
- New project: POST `/api/project/new` with `{"name": "..."}` creates the project directory + empty step files
- Save: POST `/api/project/save` writes all in-memory step data to disk
- Auto-save: triggered after every successful step run
- On launch: auto-opens last project via `data/last_project.txt`
- Project switcher available in the sidebar header

## Future Work

- Step 5 (Image Generation) — will be specced separately when ready
