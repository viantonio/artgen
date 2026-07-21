# ArtGen Step 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ArtGen shared infrastructure + Step 1 (Subtopic Planning) — a local web app where the user enters a topic + subtopic count, configures Anthropic model/params, and generates a structured list of subtopics via the Anthropic API.

**Architecture:** Python FastAPI backend serving a REST API and static HTML/CSS/JS frontend. Separate routes per step. JSON file persistence. Backend proxies all AI API calls (keys never leave the server).

**Tech Stack:** Python 3.10+, FastAPI, uvicorn, httpx, Pydantic v2, vanilla HTML/CSS/JS

## Global Constraints

- Platform: Windows 10+ and Linux (Python cross-platform)
- No build toolchain — `pip install -r requirements.txt && python main.py` to run
- No automatic model fallback on API failure — ever
- API keys stored server-side only, never exposed to frontend
- Each step has independent data file, params, and UI route
- System log captures all pipeline activity with specific error messages
- Prompt and parameters must be inspectable and editable by the user for every step
- Project auto-saves on step completion, auto-loads last project on launch
- Build only Step 1 now — stop and wait for user testing before Step 2

---

## File Structure

```
artgen/
├── main.py                  # FastAPI app, static mount, include routers
├── requirements.txt         # fastapi, uvicorn, httpx, pydantic
├── static/
│   ├── css/
│   │   └── style.css        # Sidebar layout, colors, step UI, log widget
│   ├── js/
│   │   ├── api.js            # Shared fetch wrapper with error handling
│   │   ├── settings.js       # Settings page logic (key entry, validation)
│   │   ├── project.js        # Project creation/loading
│   │   ├── log.js            # Log widget (bottom bar) + full log page
│   │   └── step1.js          # Step 1 UI logic
│   ├── index.html            # Project setup / landing page
│   ├── settings.html         # API key management
│   ├── step1.html            # Subtopic Planning
│   └── log.html              # Full system log view
├── data/                     # Created at runtime
│   ├── settings.json         # API keys (persisted)
│   └── last_project.txt      # Path to last opened project
└── log/                      # Created at runtime
    └── <project-name>.log    # Per-project log file
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `main.py`
- Create: `static/css/style.css` (skeleton)
- Create: `static/js/api.js` (skeleton)
- Create: `static/index.html` (placeholder)

**Interfaces:**
- Consumes: nothing
- Produces: `main.py` FastAPI app, directory structure, all later tasks add to this

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.115.0
uvicorn>=0.30.0
httpx>=0.27.0
pydantic>=2.0.0
```

- [ ] **Step 2: Create main.py skeleton**

```python
"""
ArtGen — Automated Article Generator
5-step AI pipeline for turning topics into illustrated articles.
"""
import json
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "log"
SETTINGS_FILE = DATA_DIR / "settings.json"
LAST_PROJECT_FILE = DATA_DIR / "last_project.txt"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# --- FastAPI app ---
app = FastAPI(title="ArtGen", version="0.1.0")

# Mount static files at /static
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# --- Serve HTML pages ---
@app.get("/")
async def serve_index():
    from fastapi.responses import FileResponse
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@app.get("/settings")
@app.get("/settings.html")
async def serve_settings():
    from fastapi.responses import FileResponse
    return FileResponse(str(BASE_DIR / "static" / "settings.html"))


@app.get("/step/{n}")
async def serve_step(n: int):
    from fastapi.responses import FileResponse
    step_file = BASE_DIR / "static" / f"step{n}.html"
    if step_file.exists():
        return FileResponse(str(step_file))
    return {"error": "Step not found"}, 404


@app.get("/log")
@app.get("/log.html")
async def serve_log():
    from fastapi.responses import FileResponse
    return FileResponse(str(BASE_DIR / "static" / "log.html"))


# --- Startup: auto-load last project ---
@app.on_event("startup")
async def startup_event():
    """Log that the app started."""
    print("ArtGen server started at http://localhost:8000")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 3: Create skeleton static files**

Create `static/css/style.css` (empty, placeholder):
```css
/* ArtGen Styles — populated in Task 2 */
```

Create `static/js/api.js` (shared fetch wrapper):
```javascript
// Shared API helper — populated in Task 9

const API = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `GET ${url} failed`);
        }
        return res.json();
    },

    async post(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `POST ${url} failed`);
        }
        return res.json();
    },

    async put(url, body) {
        const res = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `PUT ${url} failed`);
        }
        return res.json();
    }
};
```

Create `static/index.html` (placeholder):
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArtGen — Article Generator</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div id="app">
        <h1>ArtGen</h1>
        <p>Loading...</p>
    </div>
    <script src="/static/js/api.js"></script>
    <script src="/static/js/project.js"></script>
</body>
</html>
```

- [ ] **Step 4: Verify the app starts**

Run: `pip install -r requirements.txt`
Run: `python main.py`
Expected: Server starts at http://localhost:8000, serves index.html at `/`, settings at `/settings`, step1 at `/step/1`

---

### Task 2: Shared Layout + CSS

**Files:**
- Modify: `static/css/style.css` (full layout styles)
- Modify: `static/index.html` (add sidebar structure)

**Interfaces:**
- Consumes: Task 1 file structure
- Produces: CSS classes for sidebar, panels, buttons, forms, log widget; shared HTML layout

- [ ] **Step 1: Write the full CSS**

```css
/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #222636;
    --border: #2d3148;
    --text: #e1e4ed;
    --text-secondary: #8b8fa7;
    --accent: #6c8cff;
    --accent-hover: #8ba4ff;
    --success: #4ade80;
    --error: #f87171;
    --warning: #fbbf24;
    --sidebar-width: 240px;
    --log-height: 200px;
    --radius: 8px;
    --font: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    --mono: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}

body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    overflow: hidden;
}

/* === Layout === */
#app { display: flex; height: 100vh; }

/* === Sidebar === */
#sidebar {
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 16px;
    gap: 4px;
    overflow-y: auto;
}

#sidebar h1 {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 12px;
    letter-spacing: -0.3px;
}

#sidebar .project-name {
    font-size: 13px;
    color: var(--text-secondary);
    padding: 8px 12px;
    background: var(--surface2);
    border-radius: var(--radius);
    margin-bottom: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

#sidebar a, #sidebar button.nav-btn {
    display: block;
    width: 100%;
    text-align: left;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
    color: var(--text-secondary);
    text-decoration: none;
    background: none;
    border: none;
    cursor: pointer;
    font-family: var(--font);
    transition: background 0.15s, color 0.15s;
}

#sidebar a:hover, #sidebar button.nav-btn:hover,
#sidebar a.active, #sidebar button.nav-btn.active {
    background: var(--surface2);
    color: var(--text);
}

#sidebar a.active, #sidebar button.nav-btn.active {
    color: var(--accent);
}

#sidebar .nav-section {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    padding: 12px 12px 4px;
    opacity: 0.6;
}

/* === Main Content === */
#main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

#content {
    flex: 1;
    overflow-y: auto;
    padding: 32px;
    max-width: 900px;
    margin: 0 auto;
    width: 100%;
}

/* === Bottom Log Widget === */
#log-widget {
    height: var(--log-height);
    min-height: var(--log-height);
    background: var(--surface);
    border-top: 1px solid var(--border);
    font-family: var(--mono);
    font-size: 12px;
    overflow-y: auto;
    padding: 8px 16px;
    color: var(--text-secondary);
}

#log-widget .log-entry { padding: 2px 0; border-bottom: 1px solid var(--border); }
#log-widget .log-entry .ts { color: var(--text-secondary); opacity: 0.6; margin-right: 8px; }
#log-widget .log-entry.ERROR { color: var(--error); }
#log-widget .log-entry.WARN { color: var(--warning); }

#log-widget-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 16px;
    background: var(--surface2);
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-secondary);
}
#log-widget-header a { color: var(--accent); text-decoration: none; font-size: 12px; }

/* === Form Elements === */
label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

input[type="text"],
input[type="number"],
input[type="password"],
textarea,
select {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    font-family: var(--font);
    font-size: 14px;
    transition: border-color 0.15s;
}

input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: var(--accent);
}

select {
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3e%3cpath fill='%238b8fa7' d='M6 8L1 3h10z'/%3e%3c/svg%3e");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 36px;
}

textarea {
    resize: vertical;
    min-height: 100px;
    font-family: var(--font);
}

button {
    padding: 8px 20px;
    border: none;
    border-radius: var(--radius);
    background: var(--accent);
    color: #fff;
    font-family: var(--font);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
}

button:hover { background: var(--accent-hover); }
button:disabled { opacity: 0.5; cursor: not-allowed; }
button.secondary { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
button.secondary:hover { background: var(--border); }
button.danger { background: var(--error); }

/* === Cards & Panels === */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 16px;
}

.card h2 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 16px;
    color: var(--text);
}

/* === Form Groups === */
.form-group { margin-bottom: 16px; }
.form-row { display: flex; gap: 12px; }
.form-row > * { flex: 1; }

/* === Status Badges === */
.status {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
.status.idle { background: var(--surface2); color: var(--text-secondary); }
.status.running { background: rgba(108, 140, 255, 0.15); color: var(--accent); }
.status.completed { background: rgba(74, 222, 128, 0.15); color: var(--success); }
.status.failed { background: rgba(248, 113, 113, 0.15); color: var(--error); }

/* === Toggle / Collapsible === */
.collapsible-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    padding: 8px 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border);
    user-select: none;
}
.collapsible-header:hover { color: var(--text); }
.collapsible-header::after { content: '\25BC'; font-size: 10px; transition: transform 0.2s; }
.collapsible-header.open::after { transform: rotate(180deg); }
.collapsible-body { display: none; padding: 12px 0; }
.collapsible-body.open { display: block; }

/* === Subtopic List === */
.subtopic-list { list-style: none; }
.subtopic-list li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: var(--surface2);
    border-radius: 6px;
    margin-bottom: 6px;
}
.subtopic-list li .num {
    font-weight: 700;
    color: var(--accent);
    font-size: 13px;
    min-width: 24px;
}
.subtopic-list li input { flex: 1; }

/* === Error Display === */
.error-box {
    background: rgba(248, 113, 113, 0.1);
    border: 1px solid var(--error);
    border-radius: var(--radius);
    padding: 12px 16px;
    color: var(--error);
    font-size: 13px;
    margin: 12px 0;
}

/* === Success Display === */
.success-box {
    background: rgba(74, 222, 128, 0.1);
    border: 1px solid var(--success);
    border-radius: var(--radius);
    padding: 12px 16px;
    color: var(--success);
    font-size: 13px;
    margin: 12px 0;
}

/* === Spinner === */
.spinner {
    display: inline-block;
    width: 16px; height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    margin-right: 8px;
    vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* === Page headers === */
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.page-header p { color: var(--text-secondary); font-size: 14px; }

/* === Sidebar step status dots === */
.step-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 8px;
    flex-shrink: 0;
}
.step-dot.idle { background: var(--border); }
.step-dot.running { background: var(--accent); }
.step-dot.completed { background: var(--success); }
.step-dot.failed { background: var(--error); }
```

- [ ] **Step 2: Update index.html with sidebar layout**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArtGen — Article Generator</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div id="app">
        <nav id="sidebar">
            <h1>⚡ ArtGen</h1>
            <div class="project-name" id="sidebar-project-name">No project</div>

            <div class="nav-section">Pipeline</div>
            <a href="/step/1" id="nav-step1"><span class="step-dot idle" id="dot-step1"></span>1. Subtopic Planning</a>
            <a href="/step/2" id="nav-step2"><span class="step-dot idle" id="dot-step2"></span>2. Subtopic Research</a>
            <a href="/step/3" id="nav-step3"><span class="step-dot idle" id="dot-step3"></span>3. Article Draft</a>
            <a href="/step/4" id="nav-step4"><span class="step-dot idle" id="dot-step4"></span>4. Style Rewrite</a>
            <a href="/step/5" id="nav-step5"><span class="step-dot idle" id="dot-step5"></span>5. Images</a>

            <div class="nav-section">System</div>
            <a href="/settings" id="nav-settings">⚙ Settings</a>
            <a href="/log" id="nav-log">📋 System Log</a>
        </nav>

        <div id="main">
            <div id="content"></div>
            <div id="log-widget-header">
                <span>System Log</span>
                <a href="/log">View Full Log →</a>
            </div>
            <div id="log-widget"></div>
        </div>
    </div>

    <script src="/static/js/api.js"></script>
    <script src="/static/js/log.js"></script>
    <script src="/static/js/project.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create a shared layout loader**

Create `static/js/layout.js`:
```javascript
// Shared layout — loads content into #content area, highlights nav, refreshes status dots

const Layout = {
    async loadContent(url) {
        const content = document.getElementById('content');
        try {
            const res = await fetch(url);
            if (!res.ok) throw new Error('Page not found');
            const html = await res.text();
            // Extract body content
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const bodyContent = doc.body.innerHTML;
            content.innerHTML = bodyContent;
        } catch (e) {
            content.innerHTML = `<div class="page-header"><h1>Error</h1><p>${e.message}</p></div>`;
        }
    },

    highlightNav(path) {
        document.querySelectorAll('#sidebar a').forEach(a => a.classList.remove('active'));
        const link = document.querySelector(`#sidebar a[href="${path}"]`);
        if (link) link.classList.add('active');
    },

    async refreshStatusDots() {
        try {
            const project = await API.get('/api/project');
            for (let i = 1; i <= 5; i++) {
                const dot = document.getElementById(`dot-step${i}`);
                if (dot && project.steps && project.steps[i]) {
                    dot.className = 'step-dot ' + (project.steps[i].status || 'idle');
                }
            }
            const nameEl = document.getElementById('sidebar-project-name');
            if (nameEl && project.name) nameEl.textContent = project.name;
        } catch (e) {
            // No project yet — dots stay idle
        }
    }
};
```

- [ ] **Step 4: Verify layout renders**

Run: `python main.py`
Open: http://localhost:8000
Expected: Dark sidebar with navigation links, empty content area, empty log widget at bottom

---

### Task 3: Settings Backend

**Files:**
- Modify: `main.py` (add settings routes)

**Interfaces:**
- Consumes: Task 1 — `SETTINGS_FILE`, `DATA_DIR`
- Produces:
  - `GET /api/settings` → `{ anthropic_key: "...masked...", gemini_key: "...masked..." }`
  - `PUT /api/settings` ← `{ anthropic_key: "...", gemini_key: "..." }` → `{ ok: true }`
  - `POST /api/settings/validate/anthropic` → `{ valid: true, model: "claude-haiku-4-5" }` or `{ valid: false, error: "..." }`
  - `POST /api/settings/validate/gemini` → `{ valid: true }` or `{ valid: false, error: "..." }`

- [ ] **Step 1: Add settings API routes to main.py**

Insert after the `LOG_DIR.mkdir(exist_ok=True)` line:

```python
# --- Settings helpers ---
def load_settings() -> dict:
    """Load settings from disk, return defaults if missing."""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"anthropic_key": "", "gemini_key": ""}


def save_settings(settings: dict) -> None:
    """Persist settings to disk."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def mask_key(key: str) -> str:
    """Mask an API key for display: show first 4 + last 4 characters."""
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]
```

Insert after the startup event, before `if __name__ == "__main__":`:

```python
# --- Settings API ---
from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    anthropic_key: str = ""
    gemini_key: str = ""


@app.get("/api/settings")
async def get_settings():
    """Return settings with masked API keys."""
    settings = load_settings()
    return {
        "anthropic_key": mask_key(settings.get("anthropic_key", "")),
        "gemini_key": mask_key(settings.get("gemini_key", "")),
    }


@app.put("/api/settings")
async def update_settings(body: SettingsUpdate):
    """Update settings. Only overwrite keys if non-empty values are provided."""
    settings = load_settings()
    if body.anthropic_key and body.anthropic_key.count("*") < len(body.anthropic_key) - 4:
        settings["anthropic_key"] = body.anthropic_key
    if body.gemini_key and body.gemini_key.count("*") < len(body.gemini_key) - 4:
        settings["gemini_key"] = body.gemini_key
    save_settings(settings)
    return {"ok": True}


@app.post("/api/settings/validate/anthropic")
async def validate_anthropic():
    """Test the Anthropic API key with a minimal call."""
    import httpx
    settings = load_settings()
    api_key = settings.get("anthropic_key", "")
    if not api_key:
        return {"valid": False, "error": "No API key configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Say hi"}],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"valid": True, "model": data.get("model", "unknown")}
            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    error_detail = err_data.get("error", {}).get("message", resp.text)
                except Exception:
                    error_detail = resp.text[:200]
                return {"valid": False, "error": f"API error ({resp.status_code}): {error_detail}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.post("/api/settings/validate/gemini")
async def validate_gemini():
    """Test the Gemini API key with a minimal call."""
    import httpx
    settings = load_settings()
    api_key = settings.get("gemini_key", "")
    if not api_key:
        return {"valid": False, "error": "No API key configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers={
                    "x-goog-api-key": api_key,
                    "content-type": "application/json",
                },
                json={
                    "contents": [{"parts": [{"text": "Say hi"}]}],
                },
            )
            if resp.status_code == 200:
                return {"valid": True}
            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    error_detail = err_data.get("error", {}).get("message", resp.text)
                except Exception:
                    error_detail = resp.text[:200]
                return {"valid": False, "error": f"API error ({resp.status_code}): {error_detail}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}
```

- [ ] **Step 2: Verify settings API**

Run: `python main.py`

Test:
```
curl http://localhost:8000/api/settings
# → {"anthropic_key":"","gemini_key":""}

curl -X PUT http://localhost:8000/api/settings -H "Content-Type: application/json" -d '{"anthropic_key":"test123"}'
# → {"ok":true}

curl http://localhost:8000/api/settings
# → {"anthropic_key":"****123","gemini_key":""}
```

---

### Task 4: Settings Frontend

**Files:**
- Create: `static/settings.html`
- Create: `static/js/settings.js`

**Interfaces:**
- Consumes: Task 2 (CSS), Task 3 (settings API), Task 9 (API wrapper)
- Produces: Functional settings page for API key management

- [ ] **Step 1: Create settings.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings — ArtGen</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="page-header">
        <h1>⚙ Settings</h1>
        <p>Configure API keys for Anthropic and Gemini</p>
    </div>

    <div class="card">
        <h2>Anthropic API Key</h2>
        <div class="form-group">
            <label for="anthropic-key">API Key</label>
            <input type="password" id="anthropic-key" placeholder="sk-ant-...">
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
            <button id="save-anthropic-btn">Save Key</button>
            <button id="validate-anthropic-btn" class="secondary">Validate</button>
            <span id="anthropic-status"></span>
        </div>
    </div>

    <div class="card">
        <h2>Gemini API Key</h2>
        <div class="form-group">
            <label for="gemini-key">API Key</label>
            <input type="password" id="gemini-key" placeholder="AIza...">
        </div>
        <div style="display:flex; gap:8px; align-items:center;">
            <button id="save-gemini-btn">Save Key</button>
            <button id="validate-gemini-btn" class="secondary">Validate</button>
            <span id="gemini-status"></span>
        </div>
    </div>

    <script src="/static/js/api.js"></script>
    <script src="/static/js/settings.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create settings.js**

```javascript
// Settings page logic

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();

    document.getElementById('save-anthropic-btn').addEventListener('click', saveAnthropicKey);
    document.getElementById('validate-anthropic-btn').addEventListener('click', validateAnthropic);
    document.getElementById('save-gemini-btn').addEventListener('click', saveGeminiKey);
    document.getElementById('validate-gemini-btn').addEventListener('click', validateGemini);
});

async function loadSettings() {
    try {
        const settings = await API.get('/api/settings');
        if (settings.anthropic_key) {
            document.getElementById('anthropic-key').value = settings.anthropic_key;
        }
        if (settings.gemini_key) {
            document.getElementById('gemini-key').value = settings.gemini_key;
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function saveAnthropicKey() {
    const key = document.getElementById('anthropic-key').value;
    const btn = document.getElementById('save-anthropic-btn');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    try {
        await API.put('/api/settings', { anthropic_key: key });
        btn.textContent = 'Saved!';
        setTimeout(() => { btn.disabled = false; btn.textContent = 'Save Key'; }, 1500);
    } catch (e) {
        btn.disabled = false;
        btn.textContent = 'Save Key';
        alert('Failed to save: ' + e.message);
    }
}

async function saveGeminiKey() {
    const key = document.getElementById('gemini-key').value;
    const btn = document.getElementById('save-gemini-btn');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    try {
        await API.put('/api/settings', { gemini_key: key });
        btn.textContent = 'Saved!';
        setTimeout(() => { btn.disabled = false; btn.textContent = 'Save Key'; }, 1500);
    } catch (e) {
        btn.disabled = false;
        btn.textContent = 'Save Key';
        alert('Failed to save: ' + e.message);
    }
}

async function validateAnthropic() {
    const status = document.getElementById('anthropic-status');
    const btn = document.getElementById('validate-anthropic-btn');
    status.innerHTML = '<span class="spinner"></span> Testing...';
    btn.disabled = true;
    try {
        const result = await API.post('/api/settings/validate/anthropic', {});
        if (result.valid) {
            status.innerHTML = '<span style="color:var(--success)">✓ Valid — ' + result.model + '</span>';
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ ' + result.error + '</span>';
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ ' + e.message + '</span>';
    }
    btn.disabled = false;
}

async function validateGemini() {
    const status = document.getElementById('gemini-status');
    const btn = document.getElementById('validate-gemini-btn');
    status.innerHTML = '<span class="spinner"></span> Testing...';
    btn.disabled = true;
    try {
        const result = await API.post('/api/settings/validate/gemini', {});
        if (result.valid) {
            status.innerHTML = '<span style="color:var(--success)">✓ Valid</span>';
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ ' + result.error + '</span>';
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ ' + e.message + '</span>';
    }
    btn.disabled = false;
}
```

- [ ] **Step 3: Verify settings page**

Run: `python main.py`
Open: http://localhost:8000/settings
Expected: Two cards for Anthropic and Gemini keys with password inputs, save buttons, and validate buttons. Save persists across restart.

---

### Task 5: Project Management Backend

**Files:**
- Modify: `main.py` (add project routes + model)

**Interfaces:**
- Consumes: Task 1 — `DATA_DIR`, `LAST_PROJECT_FILE`
- Produces:
  - `GET /api/project` → current project info + step statuses
  - `POST /api/project/new` ← `{ name: "..." }` → project metadata
  - `POST /api/project/save` → `{ ok: true }`
  - `GET /api/project/load` → auto-load last project

- [ ] **Step 1: Add project management routes to main.py**

Insert after the settings routes:

```python
# --- Project Management ---
import datetime as dt


class NewProjectRequest(BaseModel):
    name: str


# In-memory project state (loaded from disk)
_current_project: dict | None = None
_current_project_path: Path | None = None


def project_dir(name: str) -> Path:
    """Get the data directory for a project name."""
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    return DATA_DIR / safe_name


def init_step_files(proj_dir: Path) -> None:
    """Create empty step data files for a new project."""
    proj_dir.mkdir(parents=True, exist_ok=True)

    step1_default = {
        "topic": "",
        "subtopic_count": 5,
        "subtopics": [],
        "status": "idle",
        "last_run": None,
        "error": None,
    }
    step2_default = {
        "research_results": [],
        "status": "idle",
        "last_run": None,
        "error": None,
    }
    step3_default = {
        "draft_article": "",
        "status": "idle",
        "last_run": None,
        "error": None,
    }
    step4_default = {
        "styled_article": "",
        "status": "idle",
        "last_run": None,
        "error": None,
    }
    step5_default = {
        "images": [],
        "final_article": "",
        "status": "idle",
        "last_run": None,
        "error": None,
    }

    defaults = {
        "step1.json": step1_default,
        "step2.json": step2_default,
        "step3.json": step3_default,
        "step4.json": step4_default,
        "step5.json": step5_default,
    }

    for filename, default_data in defaults.items():
        filepath = proj_dir / filename
        if not filepath.exists():
            with open(filepath, "w") as f:
                json.dump(default_data, f, indent=2)

    # Project metadata
    project_file = proj_dir / "project.json"
    if not project_file.exists():
        with open(project_file, "w") as f:
            json.dump({
                "name": proj_dir.name,
                "created": dt.datetime.now().isoformat(),
                "current_step": 1,
            }, f, indent=2)


def load_project(proj_dir: Path) -> dict:
    """Load full project state from disk."""
    project = {}
    proj_file = proj_dir / "project.json"
    if proj_file.exists():
        with open(proj_file) as f:
            project = json.load(f)

    steps = {}
    for i in range(1, 6):
        step_file = proj_dir / f"step{i}.json"
        if step_file.exists():
            with open(step_file) as f:
                steps[i] = json.load(f)
        else:
            steps[i] = {"status": "idle"}

    project["steps"] = steps
    return project


@app.get("/api/project")
async def get_project():
    """Get current project metadata + all step statuses."""
    global _current_project
    if _current_project is None:
        return {"name": None, "steps": {}, "exists": False}

    # Reload from disk to pick up any changes
    proj = load_project(_current_project_path)
    # Strip full step data, return only statuses for the sidebar
    result = {
        "name": proj.get("name"),
        "created": proj.get("created"),
        "current_step": proj.get("current_step", 1),
        "exists": True,
        "steps": {str(i): {"status": proj["steps"][i].get("status", "idle")} for i in range(1, 6)},
    }
    return result


@app.post("/api/project/new")
async def new_project(body: NewProjectRequest):
    """Create a new project."""
    global _current_project, _current_project_path

    proj_dir = project_dir(body.name)
    init_step_files(proj_dir)

    _current_project_path = proj_dir
    _current_project = load_project(proj_dir)

    # Save as last project
    with open(LAST_PROJECT_FILE, "w") as f:
        f.write(str(proj_dir))

    # Log
    log_entry("INFO", 0, f"Project '{body.name}' created")

    return {"ok": True, "name": proj_dir.name, "path": str(proj_dir)}


@app.post("/api/project/save")
async def save_project():
    """Persist current project state to disk."""
    global _current_project, _current_project_path
    if _current_project_path is None:
        return {"ok": False, "error": "No project loaded"}

    for i in range(1, 6):
        step_file = _current_project_path / f"step{i}.json"
        if step_file.exists():
            with open(step_file) as f:
                pass  # Already on disk — no-op for now

    log_entry("INFO", 0, "Project saved")
    return {"ok": True}


@app.get("/api/project/load")
async def load_last_project():
    """Auto-load the last project on startup."""
    global _current_project, _current_project_path

    if not LAST_PROJECT_FILE.exists():
        return {"ok": False, "error": "No previous project found"}

    with open(LAST_PROJECT_FILE) as f:
        path_str = f.read().strip()

    proj_dir = Path(path_str)
    if not proj_dir.exists():
        return {"ok": False, "error": f"Project directory not found: {path_str}"}

    _current_project_path = proj_dir
    _current_project = load_project(proj_dir)

    log_entry("INFO", 0, f"Loaded project '{_current_project.get('name', proj_dir.name)}'")

    return {
        "ok": True,
        "name": _current_project.get("name"),
        "created": _current_project.get("created"),
        "steps": {str(i): {"status": _current_project["steps"][i].get("status", "idle")} for i in range(1, 6)},
    }
```

- [ ] **Step 2: Verify project management**

Run: `python main.py`

Test:
```
curl -X POST http://localhost:8000/api/project/new -H "Content-Type: application/json" -d '{"name":"test-project"}'
# → {"ok":true,"name":"test-project","path":"..."}

curl http://localhost:8000/api/project
# → {"name":"test-project","steps":{"1":{"status":"idle"},...},"exists":true}
```

Check that `data/test-project/` exists with `project.json`, `step1.json`–`step5.json`.

---

### Task 6: Project Management Frontend

**Files:**
- Create: `static/js/project.js`
- Modify: `static/index.html` (make functional as project landing page)

**Interfaces:**
- Consumes: Task 2 (layout), Task 5 (project API)
- Produces: Project creation UI, auto-load on startup

- [ ] **Step 1: Create project.js**

```javascript
// Project management — handles project creation and auto-load

document.addEventListener('DOMContentLoaded', async () => {
    // Try to auto-load last project
    const loaded = await autoLoadProject();
    if (!loaded) {
        showProjectSetup();
    }
});

async function autoLoadProject() {
    try {
        const result = await API.get('/api/project/load');
        if (result.ok) {
            window.location.href = '/step/1';
            return true;
        }
    } catch (e) {
        console.log('No previous project to load');
    }
    return false;
}

function showProjectSetup() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="page-header">
            <h1>Welcome to ArtGen</h1>
            <p>Create a new project to get started with article generation</p>
        </div>

        <div class="card">
            <h2>New Project</h2>
            <div class="form-group">
                <label for="project-name">Project Name</label>
                <input type="text" id="project-name" placeholder="e.g., History of Space Exploration">
            </div>
            <button id="create-project-btn">Create Project</button>
            <div id="create-status"></div>
        </div>

        <div class="card">
            <h2>Or Load Existing Project</h2>
            <button id="load-last-btn" class="secondary">Load Last Project</button>
            <div id="load-status"></div>
        </div>
    `;

    document.getElementById('create-project-btn').addEventListener('click', async () => {
        const name = document.getElementById('project-name').value.trim();
        if (!name) {
            document.getElementById('create-status').innerHTML =
                '<span class="error-box">Please enter a project name</span>';
            return;
        }
        const btn = document.getElementById('create-project-btn');
        btn.disabled = true;
        btn.textContent = 'Creating...';
        try {
            await API.post('/api/project/new', { name });
            // Check if settings are configured
            const settings = await API.get('/api/settings');
            const hasKeys = settings.anthropic_key || settings.gemini_key;
            if (!hasKeys) {
                window.location.href = '/settings';
            } else {
                window.location.href = '/step/1';
            }
        } catch (e) {
            document.getElementById('create-status').innerHTML =
                `<span class="error-box">${e.message}</span>`;
            btn.disabled = false;
            btn.textContent = 'Create Project';
        }
    });

    document.getElementById('load-last-btn').addEventListener('click', async () => {
        const btn = document.getElementById('load-last-btn');
        btn.disabled = true;
        btn.textContent = 'Loading...';
        try {
            const result = await API.get('/api/project/load');
            if (result.ok) {
                window.location.href = '/step/1';
            } else {
                document.getElementById('load-status').innerHTML =
                    `<span class="error-box">${result.error}</span>`;
                btn.disabled = false;
                btn.textContent = 'Load Last Project';
            }
        } catch (e) {
            document.getElementById('load-status').innerHTML =
                `<span class="error-box">${e.message}</span>`;
            btn.disabled = false;
            btn.textContent = 'Load Last Project';
        }
    });
}
```

- [ ] **Step 2: Verify project frontend**

Run: `python main.py`
Open: http://localhost:8000 (with no last project)
Expected: Welcome page with "New Project" form and "Load Last Project" button. Creating a project with no API keys redirects to settings. Creating a project with keys set redirects to Step 1.

---

### Task 7: System Log Backend

**Files:**
- Modify: `main.py` (add log routes + log_entry helper)

**Interfaces:**
- Consumes: Task 1 — `LOG_DIR`, Task 5 — `_current_project_path`
- Produces:
  - `log_entry(level, step, message)` — helper used by all other tasks
  - `GET /api/log` → `{ entries: [...] }`
  - `GET /api/log/stream` → SSE stream

- [ ] **Step 1: Add logging infrastructure to main.py**

Insert after the settings helpers and before the settings API routes:

```python
# --- Logging ---
import threading

_log_buffer: list[dict] = []  # In-memory buffer for SSE streaming
_log_lock = threading.Lock()


def log_entry(level: str, step: int, message: str) -> dict:
    """Write a log entry to disk and in-memory buffer."""
    global _log_buffer
    entry = {
        "timestamp": dt.datetime.now().isoformat(),
        "level": level,
        "step": step,
        "message": message,
    }

    # Add to in-memory buffer (keep last 500 entries)
    with _log_lock:
        _log_buffer.append(entry)
        if len(_log_buffer) > 500:
            _log_buffer = _log_buffer[-500:]

    # Write to disk log
    global _current_project_path
    if _current_project_path:
        log_file = LOG_DIR / f"{_current_project_path.name}.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    # Also print to console for debugging
    print(f"[{entry['timestamp']}] [{level}] Step {step}: {message}")

    return entry
```

Insert after the project management routes:

```python
# --- System Log API ---
@app.get("/api/log")
async def get_log():
    """Get all log entries for the current project."""
    global _current_project_path
    entries = []

    if _current_project_path:
        log_file = LOG_DIR / f"{_current_project_path.name}.log"
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

    # Also include buffer entries not yet written
    with _log_lock:
        for entry in _log_buffer:
            if entry not in entries:
                entries.append(entry)

    return {"entries": entries, "project": _current_project_path.name if _current_project_path else None}


from fastapi.responses import StreamingResponse
import asyncio


@app.get("/api/log/stream")
async def stream_log():
    """SSE stream of live log entries."""
    async def event_generator():
        last_idx = len(_log_buffer)
        while True:
            with _log_lock:
                current_len = len(_log_buffer)
                if current_len > last_idx:
                    for entry in _log_buffer[last_idx:current_len]:
                        yield f"data: {json.dumps(entry)}\n\n"
                    last_idx = current_len
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: Verify logging**

Run: `python main.py`

Test:
```
# Reset log
curl http://localhost:8000/api/log
# → {"entries":[],"project":null}

# Create a project (triggers a log entry)
curl -X POST http://localhost:8000/api/project/new -H "Content-Type: application/json" -d '{"name":"log-test"}'

curl http://localhost:8000/api/log
# → {"entries":[{"timestamp":"...","level":"INFO","step":0,"message":"Project 'log-test' created"}],"project":"log-test"}
```

---

### Task 8: System Log Frontend

**Files:**
- Create: `static/js/log.js` (log widget + full log page)
- Create: `static/log.html` (full log view)

**Interfaces:**
- Consumes: Task 2 (CSS, layout), Task 7 (log API)
- Produces: Bottom-bar log widget + full log page at `/log`

- [ ] **Step 1: Create log.js**

```javascript
// System log widget — renders in the bottom bar

const LogWidget = {
    entries: [],
    maxVisible: 50,

    init() {
        this.container = document.getElementById('log-widget');
        this.fetchLog();
        // Refresh every 5 seconds
        setInterval(() => this.fetchLog(), 5000);
    },

    async fetchLog() {
        try {
            const data = await API.get('/api/log');
            this.entries = data.entries || [];
            this.render();
        } catch (e) {
            // Log endpoint not available yet — ignore
        }
    },

    render() {
        if (!this.container) return;
        const recent = this.entries.slice(-this.maxVisible);
        this.container.innerHTML = recent.map(e => {
            const ts = e.timestamp ? e.timestamp.split('T')[1].split('.')[0] : '';
            return `<div class="log-entry ${e.level}"><span class="ts">${ts}</span>${e.message}</div>`;
        }).join('');
        this.container.scrollTop = this.container.scrollHeight;
    }
};

// Initialize on all pages
document.addEventListener('DOMContentLoaded', () => {
    LogWidget.init();
});
```

- [ ] **Step 2: Create log.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Log — ArtGen</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="page-header">
        <h1>📋 System Log</h1>
        <p>All pipeline activity and errors</p>
    </div>

    <div class="card" style="display:flex; justify-content:flex-end; gap:8px; margin-bottom:16px;">
        <button id="refresh-log-btn" class="secondary">Refresh</button>
        <button id="clear-log-display-btn" class="secondary">Clear Display</button>
    </div>

    <div class="card">
        <div id="full-log" style="font-family: var(--mono); font-size: 12px; max-height: 600px; overflow-y: auto;"></div>
    </div>

    <script src="/static/js/api.js"></script>
    <script>
        const logContainer = document.getElementById('full-log');

        async function loadFullLog() {
            try {
                const data = await API.get('/api/log');
                const entries = data.entries || [];
                logContainer.innerHTML = entries.map(e => {
                    const ts = e.timestamp || '';
                    return `<div class="log-entry ${e.level}"><span class="ts">${ts}</span>[${e.level}] Step ${e.step}: ${e.message}</div>`;
                }).join('');
            } catch (e) {
                logContainer.innerHTML = `<div class="error-box">Failed to load log: ${e.message}</div>`;
            }
        }

        document.getElementById('refresh-log-btn').addEventListener('click', loadFullLog);
        document.getElementById('clear-log-display-btn').addEventListener('click', () => {
            logContainer.innerHTML = '';
        });

        loadFullLog();
    </script>
</body>
</html>
```

- [ ] **Step 3: Verify log frontend**

Run: `python main.py`
Open: http://localhost:8000/log
Expected: Full log view with refresh button. Bottom bar widget visible on all pages.

---

### Task 9: Step 1 Backend

**Files:**
- Modify: `main.py` (add Step 1 data/params/run routes)

**Interfaces:**
- Consumes: Task 3 (settings — for API key), Task 5 (project — for project path), Task 7 (logging)
- Produces:
  - `GET /api/step/1/data` → Step 1 data (topic, subtopics, status)
  - `PUT /api/step/1/data` ← Step 1 data → `{ ok: true }`
  - `GET /api/step/1/params` → Step 1 params (model, temp, max_tokens, system_prompt)
  - `PUT /api/step/1/params` ← params → `{ ok: true }`
  - `POST /api/step/1/run` → runs Anthropic API call, returns subtopics

- [ ] **Step 1: Add Step 1 routes to main.py**

Insert after the log API routes:

```python
# --- Step 1: Subtopic Planning ---

STEP1_DEFAULT_PARAMS = {
    "model": "claude-haiku-4-5",
    "temperature": 1.0,
    "max_tokens": 4096,
    "system_prompt": (
        "You are a content planning assistant. Given a MAIN TOPIC and a desired NUMBER of subtopics, "
        "generate exactly that many subtopics that comprehensively cover the main topic. "
        "Each subtopic should be a specific, focused angle that could be researched independently. "
        "Make subtopics diverse, interesting, and non-overlapping. "
        "Return them as a JSON object with a 'subtopics' array where each entry has 'id' (1-based integer) and 'title' (string)."
    ),
}


def get_step1_params() -> dict:
    """Load Step 1 params from disk or return defaults."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step1_params.json"
        if params_file.exists():
            with open(params_file) as f:
                return json.load(f)
    return dict(STEP1_DEFAULT_PARAMS)


def save_step1_params(params: dict) -> None:
    """Persist Step 1 params to disk."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step1_params.json"
        with open(params_file, "w") as f:
            json.dump(params, f, indent=2)


def get_step1_data() -> dict:
    """Load Step 1 data from disk."""
    global _current_project_path
    if _current_project_path:
        step_file = _current_project_path / "step1.json"
        if step_file.exists():
            with open(step_file) as f:
                return json.load(f)
    return {
        "topic": "",
        "subtopic_count": 5,
        "subtopics": [],
        "status": "idle",
        "last_run": None,
        "error": None,
    }


def save_step1_data(data: dict) -> None:
    """Persist Step 1 data to disk."""
    global _current_project_path
    if _current_project_path:
        step_file = _current_project_path / "step1.json"
        with open(step_file, "w") as f:
            json.dump(data, f, indent=2)


# Models available for Step 1 (Anthropic)
STEP1_MODELS = [
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5 (Fastest)"},
    {"id": "claude-sonnet-5", "name": "Claude Sonnet 5 (Balanced)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-8", "name": "Claude Opus 4.8 (Most Capable)"},
    {"id": "claude-fable-5", "name": "Claude Fable 5 (Best)"},
]


@app.get("/api/step/1/data")
async def get_step1():
    """Get Step 1 stored data."""
    return get_step1_data()


class Step1DataUpdate(BaseModel):
    topic: str = ""
    subtopic_count: int = 5
    subtopics: list[dict] = []
    status: str = "idle"
    error: str | None = None


@app.put("/api/step/1/data")
async def update_step1(body: Step1DataUpdate):
    """Update Step 1 data (manual edit)."""
    data = body.model_dump()
    save_step1_data(data)
    log_entry("INFO", 1, f"Step 1 data updated. Topic: '{data['topic']}', Subtopics: {len(data['subtopics'])}")
    return {"ok": True}


@app.get("/api/step/1/params")
async def get_step1_params_route():
    """Get Step 1 parameters."""
    params = get_step1_params()
    params["available_models"] = STEP1_MODELS
    return params


class Step1ParamsUpdate(BaseModel):
    model: str = "claude-haiku-4-5"
    temperature: float = 1.0
    max_tokens: int = 4096
    system_prompt: str = ""


@app.put("/api/step/1/params")
async def update_step1_params(body: Step1ParamsUpdate):
    """Update Step 1 parameters."""
    params = body.model_dump()
    save_step1_params(params)
    log_entry("INFO", 1, f"Step 1 params updated. Model: {params['model']}, Temp: {params['temperature']}")
    return {"ok": True}


@app.post("/api/step/1/run")
async def run_step1():
    """Execute Step 1: call Anthropic API to generate subtopics."""
    import httpx

    # Load data and params
    data = get_step1_data()
    params = get_step1_params()
    settings = load_settings()

    api_key = settings.get("anthropic_key", "")
    if not api_key:
        log_entry("ERROR", 1, "No Anthropic API key configured")
        data["status"] = "failed"
        data["error"] = "No Anthropic API key configured. Go to Settings to add one."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    topic = data.get("topic", "").strip()
    subtopic_count = data.get("subtopic_count", 5)

    if not topic:
        log_entry("ERROR", 1, "No topic provided")
        data["status"] = "failed"
        data["error"] = "No topic provided. Enter a topic and try again."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    if subtopic_count < 1 or subtopic_count > 20:
        log_entry("ERROR", 1, f"Invalid subtopic count: {subtopic_count}")
        data["status"] = "failed"
        data["error"] = "Subtopic count must be between 1 and 20."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    # Mark as running
    data["status"] = "running"
    data["error"] = None
    save_step1_data(data)

    model = params.get("model", "claude-haiku-4-5")
    temperature = params.get("temperature", 1.0)
    max_tokens = params.get("max_tokens", 4096)
    system_prompt = params.get("system_prompt", STEP1_DEFAULT_PARAMS["system_prompt"])

    user_message = (
        f"MAIN TOPIC: {topic}\n"
        f"NUMBER of subtopics to generate: {subtopic_count}\n\n"
        f"Generate exactly {subtopic_count} subtopics for this topic."
    )

    # JSON schema for structured output
    output_schema = {
        "type": "object",
        "properties": {
            "subtopics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "1-based index of the subtopic"},
                        "title": {"type": "string", "description": "The subtopic title"},
                    },
                    "required": ["id", "title"],
                },
                "minItems": subtopic_count,
                "maxItems": subtopic_count,
            }
        },
        "required": ["subtopics"],
    }

    request_body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_message}
        ],
        "output_format": {
            "type": "json_schema",
            "schema": output_schema,
        },
    }

    log_entry("INFO", 1, f"Calling Anthropic API. Model: {model}, Topic: '{topic}', Count: {subtopic_count}")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=request_body,
            )

            if resp.status_code == 200:
                result = resp.json()
                # Extract structured output from the response
                content_blocks = result.get("content", [])
                response_text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        response_text += block.get("text", "")

                # Parse the JSON response
                try:
                    parsed = json.loads(response_text)
                    subtopics = parsed.get("subtopics", [])

                    # Enforce exact count
                    if len(subtopics) != subtopic_count:
                        log_entry("WARN", 1, f"Model returned {len(subtopics)} subtopics, expected {subtopic_count}. Using first {subtopic_count}.")
                        subtopics = subtopics[:subtopic_count]

                    # Re-index to ensure 1-based IDs
                    for i, st in enumerate(subtopics):
                        st["id"] = i + 1

                    data["subtopics"] = subtopics
                    data["status"] = "completed"
                    data["last_run"] = dt.datetime.now().isoformat()
                    data["error"] = None
                    save_step1_data(data)

                    log_entry("INFO", 1, f"Step 1 completed. Generated {len(subtopics)} subtopics.")
                    return {"ok": True, "subtopics": subtopics}

                except json.JSONDecodeError as parse_err:
                    log_entry("ERROR", 1, f"Failed to parse model response as JSON: {parse_err}")
                    # Fall back to unstructured parsing: try to extract numbered list
                    subtopics = _parse_subtopics_fallback(response_text, subtopic_count)
                    if subtopics:
                        data["subtopics"] = subtopics
                        data["status"] = "completed"
                        data["last_run"] = dt.datetime.now().isoformat()
                        data["error"] = None
                        save_step1_data(data)
                        log_entry("WARN", 1, f"Step 1 completed via fallback parsing. Generated {len(subtopics)} subtopics.")
                        return {"ok": True, "subtopics": subtopics}
                    else:
                        data["status"] = "failed"
                        data["error"] = f"Failed to parse model response. Raw response: {response_text[:500]}"
                        save_step1_data(data)
                        return {"ok": False, "error": data["error"]}

            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    error_detail = err_data.get("error", {}).get("message", resp.text[:500])
                except Exception:
                    error_detail = resp.text[:500]

                log_entry("ERROR", 1, f"Anthropic API error ({resp.status_code}): {error_detail}")
                data["status"] = "failed"
                data["error"] = f"API error ({resp.status_code}): {error_detail}"
                save_step1_data(data)
                return {"ok": False, "error": data["error"]}

    except httpx.TimeoutException:
        log_entry("ERROR", 1, "Anthropic API request timed out (120s)")
        data["status"] = "failed"
        data["error"] = "Request timed out after 120 seconds. Try a faster model or fewer subtopics."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    except Exception as e:
        log_entry("ERROR", 1, f"Unexpected error: {str(e)}")
        data["status"] = "failed"
        data["error"] = f"Unexpected error: {str(e)}"
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}


def _parse_subtopics_fallback(text: str, count: int) -> list[dict] | None:
    """Attempt to parse subtopics from unstructured text (e.g., numbered list)."""
    import re
    lines = text.strip().split("\n")
    subtopics = []
    pattern = re.compile(r"^\s*(?:\d+[.)]\s*)?(?:\*\*\s*)?(.+?)(?:\*\*\s*)?$")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            title = match.group(1).strip()
            # Filter out lines that are clearly not subtopic titles
            if len(title) > 3 and not title.lower().startswith(("here", "the ", "these", "below", "above")):
                subtopics.append(title)

    if len(subtopics) >= count:
        return [{"id": i + 1, "title": subtopics[i]} for i in range(count)]
    elif len(subtopics) > 0:
        return [{"id": i + 1, "title": subtopics[i]} for i in range(len(subtopics))]
    return None
```

- [ ] **Step 2: Verify Step 1 backend**

Run: `python main.py`

Test:
```
# First create a project and set params
curl -X POST http://localhost:8000/api/project/new -H "Content-Type: application/json" -d '{"name":"step1-test"}'

# Check default data
curl http://localhost:8000/api/step/1/data
# → {"topic":"","subtopic_count":5,"subtopics":[],"status":"idle",...}

# Check default params
curl http://localhost:8000/api/step/1/params
# → {"model":"claude-haiku-4-5","temperature":1.0,"max_tokens":4096,...}

# Update data with a topic
curl -X PUT http://localhost:8000/api/step/1/data -H "Content-Type: application/json" -d '{"topic":"History of Space Exploration","subtopic_count":3}'

# Update params
curl -X PUT http://localhost:8000/api/step/1/params -H "Content-Type: application/json" -d '{"model":"claude-haiku-4-5","temperature":0.7,"max_tokens":2048,"system_prompt":"You are a content planner. Generate subtopics for the given topic."}'
```

---

### Task 10: Step 1 Frontend

**Files:**
- Create: `static/step1.html`
- Create: `static/js/step1.js`

**Interfaces:**
- Consumes: Task 2 (CSS/layout), Task 9 (Step 1 API)
- Produces: Full Step 1 UI — topic input, subtopic count, model selector, params panel, Go button, editable output list

- [ ] **Step 1: Create step1.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Step 1: Subtopic Planning — ArtGen</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="page-header">
        <h1>Step 1: Subtopic Planning</h1>
        <p>Enter a topic to generate a structured list of subtopics</p>
    </div>

    <!-- Input Card -->
    <div class="card">
        <h2>Topic Input</h2>
        <div class="form-group">
            <label for="step1-topic">Main Topic</label>
            <input type="text" id="step1-topic" placeholder="e.g., The History of Space Exploration">
        </div>
        <div class="form-row">
            <div class="form-group">
                <label for="step1-count">Number of Subtopics</label>
                <input type="number" id="step1-count" value="5" min="1" max="20">
            </div>
        </div>
        <button id="step1-run-btn">🚀 Generate Subtopics</button>
        <span id="step1-run-status"></span>
    </div>

    <!-- Error display -->
    <div id="step1-error" style="display:none;"></div>

    <!-- Parameters Card (collapsible) -->
    <div class="card">
        <div class="collapsible-header" id="params-toggle">
            ⚙ Model & Parameters
        </div>
        <div class="collapsible-body" id="params-body">
            <div class="form-group">
                <label for="step1-model">Model</label>
                <select id="step1-model"></select>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="step1-temperature">Temperature: <span id="temp-value">1.0</span></label>
                    <input type="range" id="step1-temperature" min="0" max="1" step="0.1" value="1.0">
                </div>
                <div class="form-group">
                    <label for="step1-max-tokens">Max Tokens</label>
                    <input type="number" id="step1-max-tokens" value="4096" min="100" max="128000">
                </div>
            </div>
            <div class="form-group">
                <label for="step1-system-prompt">System Prompt</label>
                <textarea id="step1-system-prompt" rows="6"></textarea>
            </div>
            <button id="step1-save-params-btn" class="secondary">Save Parameters</button>
            <span id="step1-params-status"></span>
        </div>
    </div>

    <!-- Output Card -->
    <div class="card" id="step1-output-card">
        <h2>Generated Subtopics</h2>
        <div id="step1-output">
            <p style="color:var(--text-secondary)">Enter a topic and click "Generate Subtopics" to get started.</p>
        </div>
    </div>

    <script src="/static/js/api.js"></script>
    <script src="/static/js/step1.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create step1.js**

```javascript
// Step 1: Subtopic Planning UI

document.addEventListener('DOMContentLoaded', () => {
    initStep1();
});

async function initStep1() {
    // Load current data
    await loadStep1Data();
    await loadStep1Params();

    // Event listeners
    document.getElementById('step1-run-btn').addEventListener('click', runStep1);
    document.getElementById('step1-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step1-temperature').addEventListener('input', (e) => {
        document.getElementById('temp-value').textContent = parseFloat(e.target.value).toFixed(1);
    });

    // Topic input: save on change (debounced)
    let topicTimeout;
    document.getElementById('step1-topic').addEventListener('input', () => {
        clearTimeout(topicTimeout);
        topicTimeout = setTimeout(saveTopicAndCount, 500);
    });
    document.getElementById('step1-count').addEventListener('change', saveTopicAndCount);

    // Collapsible params
    document.getElementById('params-toggle').addEventListener('click', () => {
        document.getElementById('params-toggle').classList.toggle('open');
        document.getElementById('params-body').classList.toggle('open');
    });
}

async function loadStep1Data() {
    try {
        const data = await API.get('/api/step/1/data');
        document.getElementById('step1-topic').value = data.topic || '';
        document.getElementById('step1-count').value = data.subtopic_count || 5;

        // Render existing subtopics
        if (data.subtopics && data.subtopics.length > 0) {
            renderSubtopics(data.subtopics);
        }

        // Show status
        const statusEl = document.getElementById('step1-run-status');
        if (data.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Running...';
        }
        if (data.error && data.status === 'failed') {
            showError(data.error);
        }
    } catch (e) {
        console.error('Failed to load Step 1 data:', e);
    }
}

async function loadStep1Params() {
    try {
        const params = await API.get('/api/step/1/params');

        // Populate model selector
        const modelSelect = document.getElementById('step1-model');
        const models = params.available_models || [];
        modelSelect.innerHTML = models.map(m =>
            `<option value="${m.id}" ${m.id === params.model ? 'selected' : ''}>${m.name}</option>`
        ).join('');

        document.getElementById('step1-temperature').value = params.temperature || 1.0;
        document.getElementById('temp-value').textContent = (params.temperature || 1.0).toFixed(1);
        document.getElementById('step1-max-tokens').value = params.max_tokens || 4096;
        document.getElementById('step1-system-prompt').value = params.system_prompt || '';
    } catch (e) {
        console.error('Failed to load Step 1 params:', e);
    }
}

async function saveTopicAndCount() {
    const topic = document.getElementById('step1-topic').value;
    const count = parseInt(document.getElementById('step1-count').value) || 5;
    try {
        await API.put('/api/step/1/data', {
            topic: topic,
            subtopic_count: count,
            subtopics: [],
            status: 'idle',
            error: null,
        });
    } catch (e) {
        console.error('Failed to save topic:', e);
    }
}

async function saveParams() {
    const btn = document.getElementById('step1-save-params-btn');
    const status = document.getElementById('step1-params-status');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        await API.put('/api/step/1/params', {
            model: document.getElementById('step1-model').value,
            temperature: parseFloat(document.getElementById('step1-temperature').value),
            max_tokens: parseInt(document.getElementById('step1-max-tokens').value),
            system_prompt: document.getElementById('step1-system-prompt').value,
        });
        status.innerHTML = '<span style="color:var(--success)">✓ Saved</span>';
        setTimeout(() => { status.innerHTML = ''; }, 2000);
    } catch (e) {
        status.innerHTML = `<span style="color:var(--error)">✗ ${e.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Parameters';
    }
}

async function runStep1() {
    const btn = document.getElementById('step1-run-btn');
    const status = document.getElementById('step1-run-status');
    const errorDiv = document.getElementById('step1-error');

    btn.disabled = true;
    btn.textContent = 'Running...';
    status.innerHTML = '<span class="spinner"></span> Calling Anthropic API...';
    errorDiv.style.display = 'none';

    try {
        // Save current topic/count first
        await saveTopicAndCount();

        const result = await API.post('/api/step/1/run', {});

        if (result.ok && result.subtopics) {
            status.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
            renderSubtopics(result.subtopics);
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
            showError(result.error || 'Unknown error');
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
        showError(e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🚀 Generate Subtopics';
    }
}

function renderSubtopics(subtopics) {
    const output = document.getElementById('step1-output');
    output.innerHTML = `
        <ul class="subtopic-list">
            ${subtopics.map(st => `
                <li>
                    <span class="num">${st.id}</span>
                    <input type="text" value="${escapeHtml(st.title)}" data-id="${st.id}" class="subtopic-edit">
                </li>
            `).join('')}
        </ul>
        <button id="save-edits-btn" class="secondary" style="margin-top:12px;">Save Edits</button>
    `;

    // Save edits button
    document.getElementById('save-edits-btn').addEventListener('click', async () => {
        const edits = [];
        document.querySelectorAll('.subtopic-edit').forEach(input => {
            edits.push({
                id: parseInt(input.dataset.id),
                title: input.value,
            });
        });

        try {
            await API.put('/api/step/1/data', {
                topic: document.getElementById('step1-topic').value,
                subtopic_count: parseInt(document.getElementById('step1-count').value) || edits.length,
                subtopics: edits,
                status: 'completed',
                error: null,
            });
            const status = document.getElementById('step1-run-status');
            status.innerHTML = '<span style="color:var(--success)">✓ Saved</span>';
            setTimeout(() => { status.innerHTML = ''; }, 2000);
        } catch (e) {
            showError('Failed to save edits: ' + e.message);
        }
    });
}

function showError(message) {
    const errorDiv = document.getElementById('step1-error');
    errorDiv.style.display = 'block';
    errorDiv.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
```

- [ ] **Step 3: Verify Step 1 full flow**

Run: `python main.py`
Open: http://localhost:8000

Expected flow:
1. First visit: project creation page
2. Create project → redirect to settings (if no API keys) or Step 1
3. Step 1 page: topic input, count, model selector, temperature slider, max tokens, system prompt
4. Enter topic, click "Generate Subtopics"
5. Results appear as editable list
6. Edit subtopic titles, click "Save Edits"
7. Data persists on page reload

---

### Task 11: Wire Navigation + Final Integration

**Files:**
- Modify: `static/index.html` (remove duplicate scripts — log.js, project.js already loaded)
- Modify: `static/step1.html` (no changes needed — content loaded via iframe approach)

**Note:** Since our architecture uses full page navigation (not SPA), the sidebar is duplicated across pages. We'll use the `index.html` layout as a shell that loads content pages.

- [ ] **Step 1: Convert to shell-based navigation**

Modify `main.py` serve functions to use a shared shell. Replace the HTML serving routes:

```python
# Replace the individual page serves with a shell pattern
# All non-API, non-static routes serve index.html which acts as a shell

@app.get("/{full_path:path}")
async def serve_shell(full_path: str):
    """Serve index.html for all non-API, non-static routes (SPA shell)."""
    from fastapi.responses import FileResponse

    # Don't intercept API or static
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404)

    return FileResponse(str(BASE_DIR / "static" / "index.html"))
```

Update `static/index.html` to be the SPA shell with content loader:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArtGen — Article Generator</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div id="app">
        <nav id="sidebar">
            <h1>⚡ ArtGen</h1>
            <div class="project-name" id="sidebar-project-name">No project</div>

            <div class="nav-section">Pipeline</div>
            <a href="/step/1" data-route="/step/1"><span class="step-dot idle" id="dot-step1"></span>1. Subtopic Planning</a>
            <a href="/step/2" data-route="/step/2"><span class="step-dot idle" id="dot-step2"></span>2. Subtopic Research</a>
            <a href="/step/3" data-route="/step/3"><span class="step-dot idle" id="dot-step3"></span>3. Article Draft</a>
            <a href="/step/4" data-route="/step/4"><span class="step-dot idle" id="dot-step4"></span>4. Style Rewrite</a>
            <a href="/step/5" data-route="/step/5"><span class="step-dot idle" id="dot-step5"></span>5. Images</a>

            <div class="nav-section">System</div>
            <a href="/settings" data-route="/settings">⚙ Settings</a>
            <a href="/log" data-route="/log">📋 System Log</a>
        </nav>

        <div id="main">
            <div id="content"></div>
            <div id="log-widget-header">
                <span>System Log</span>
                <a href="/log">View Full Log →</a>
            </div>
            <div id="log-widget"></div>
        </div>
    </div>

    <!-- Core scripts (loaded on every page) -->
    <script src="/static/js/api.js"></script>
    <script src="/static/js/log.js"></script>

    <!-- Router: loads page content based on URL -->
    <script>
        // Page registry: maps routes to HTML files and JS files
        const PAGES = {
            '/':              { html: '/static/page-index.html',     js: '/static/js/project.js' },
            '/settings':      { html: '/static/settings.html',       js: '/static/js/settings.js' },
            '/step/1':        { html: '/static/step1.html',          js: '/static/js/step1.js' },
            '/log':           { html: '/static/log.html',            js: null },
        };

        async function navigate(path) {
            const page = PAGES[path];
            if (!page) {
                document.getElementById('content').innerHTML = '<div class="page-header"><h1>404</h1><p>Page not found</p></div>';
                return;
            }

            // Load HTML content
            try {
                const res = await fetch(page.html);
                if (!res.ok) throw new Error('Page not found');
                const html = await res.text();
                document.getElementById('content').innerHTML = html;

                // Load page-specific JS
                if (page.js) {
                    // Remove previously loaded page scripts
                    document.querySelectorAll('script[data-page]').forEach(s => s.remove());
                    const script = document.createElement('script');
                    script.src = page.js;
                    script.setAttribute('data-page', path);
                    document.body.appendChild(script);
                }

                // Update URL
                window.history.pushState({}, '', path);

                // Highlight nav
                document.querySelectorAll('#sidebar a').forEach(a => a.classList.remove('active'));
                const link = document.querySelector(`#sidebar a[data-route="${path}"]`);
                if (link) link.classList.add('active');
            } catch (e) {
                document.getElementById('content').innerHTML = `<div class="page-header"><h1>Error</h1><p>${e.message}</p></div>`;
            }
        }

        // Intercept sidebar clicks
        document.querySelectorAll('#sidebar a[data-route]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                navigate(link.dataset.route);
            });
        });

        // Handle back/forward
        window.addEventListener('popstate', () => {
            navigate(window.location.pathname);
        });

        // Initial navigation
        const initialPath = window.location.pathname;
        if (PAGES[initialPath]) {
            navigate(initialPath);
        } else if (initialPath === '/' || initialPath === '') {
            navigate('/');
        } else {
            navigate('/');
        }

        // Auto-load project and refresh status dots
        async function initProject() {
            try {
                const result = await API.get('/api/project/load');
                if (result.ok) {
                    document.getElementById('sidebar-project-name').textContent = result.name || 'Project';
                    for (const [stepNum, stepData] of Object.entries(result.steps || {})) {
                        const dot = document.getElementById(`dot-step${stepNum}`);
                        if (dot) dot.className = 'step-dot ' + (stepData.status || 'idle');
                    }
                    // Navigate to Step 1 if on root
                    if (initialPath === '/' || initialPath === '') {
                        navigate('/step/1');
                    }
                }
            } catch (e) {
                // No project yet — stay on landing page
            }
        }
        initProject();
    </script>
</body>
</html>
```

- [ ] **Step 2: Create page-index.html for the landing page**

Create `static/page-index.html`:
```html
<div class="page-header">
    <h1>Welcome to ArtGen</h1>
    <p>Create a new project to get started with article generation</p>
</div>

<div class="card">
    <h2>New Project</h2>
    <div class="form-group">
        <label for="project-name">Project Name</label>
        <input type="text" id="project-name" placeholder="e.g., History of Space Exploration">
    </div>
    <button id="create-project-btn">Create Project</button>
    <div id="create-status"></div>
</div>

<div class="card">
    <h2>Or Load Existing Project</h2>
    <button id="load-last-btn" class="secondary">Load Last Project</button>
    <div id="load-status"></div>
</div>
```

- [ ] **Step 3: Simplify project.js for SPA**

Update `static/js/project.js`:
```javascript
// Project management — SPA version

document.addEventListener('DOMContentLoaded', () => {
    const createBtn = document.getElementById('create-project-btn');
    const loadBtn = document.getElementById('load-last-btn');

    if (!createBtn && !loadBtn) return; // Not on the project page

    if (createBtn) {
        createBtn.addEventListener('click', async () => {
            const name = document.getElementById('project-name').value.trim();
            if (!name) {
                document.getElementById('create-status').innerHTML =
                    '<span class="error-box">Please enter a project name</span>';
                return;
            }
            createBtn.disabled = true;
            createBtn.textContent = 'Creating...';
            try {
                await API.post('/api/project/new', { name });
                const settings = await API.get('/api/settings');
                const hasKeys = settings.anthropic_key || settings.gemini_key;
                if (!hasKeys) {
                    window.location.href = '/settings';
                } else {
                    window.location.href = '/step/1';
                }
            } catch (e) {
                document.getElementById('create-status').innerHTML =
                    `<span class="error-box">${e.message}</span>`;
                createBtn.disabled = false;
                createBtn.textContent = 'Create Project';
            }
        });
    }

    if (loadBtn) {
        loadBtn.addEventListener('click', async () => {
            loadBtn.disabled = true;
            loadBtn.textContent = 'Loading...';
            try {
                const result = await API.get('/api/project/load');
                if (result.ok) {
                    window.location.href = '/step/1';
                } else {
                    document.getElementById('load-status').innerHTML =
                        `<span class="error-box">${result.error}</span>`;
                    loadBtn.disabled = false;
                    loadBtn.textContent = 'Load Last Project';
                }
            } catch (e) {
                document.getElementById('load-status').innerHTML =
                    `<span class="error-box">${e.message}</span>`;
                loadBtn.disabled = false;
                loadBtn.textContent = 'Load Last Project';
            }
        });
    }
});
```

- [ ] **Step 4: Full integration test**

Run: `python main.py`
Open: http://localhost:8000

Expected flow:
1. Landing page loads in SPA shell
2. Create project → auto-navigate to settings (no keys) or Step 1
3. Configure API keys at Settings → click Step 1 in sidebar
4. Step 1 loads with topic input, params panel
5. Enter topic → click Generate → subtopics appear
6. Edit subtopics → Save Edits
7. Refresh page → data persists
8. System log shows all activity in bottom bar

---

## Verification Checklist

After all tasks complete, verify:

- [ ] App starts with `pip install -r requirements.txt && python main.py`
- [ ] First launch shows project creation page
- [ ] Creating a project without API keys redirects to Settings
- [ ] API keys can be entered, saved, and validated
- [ ] Keys persist across restarts
- [ ] Step 1 loads with default params (Haiku, temp 1.0, max_tokens 4096)
- [ ] User can change model, temperature, max_tokens, and system prompt
- [ ] Entering a topic + count and clicking Go calls the Anthropic API
- [ ] Generated subtopics appear as an editable list
- [ ] Editing subtopics and saving persists the changes
- [ ] Failed API calls show clear error messages (no auto-fallback)
- [ ] System log widget shows all activity in the bottom bar
- [ ] Full log page at `/log` shows all entries
- [ ] Project auto-loads on restart via `data/last_project.txt`
- [ ] Navigation sidebar works between all pages
