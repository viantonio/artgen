"""
ArtGen — Automated Article Generator
5-step AI pipeline for turning topics into illustrated articles.
"""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "log"
SETTINGS_FILE = DATA_DIR / "settings.json"
LAST_PROJECT_FILE = DATA_DIR / "last_project.txt"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# --- Settings helpers ---
def load_settings() -> dict:
    """Load settings from disk, return defaults if missing."""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"anthropic_key": "", "gemini_key": "", "openai_key": ""}


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

# --- Startup recovery: reset stuck "running" states from previous crashes ---
def _recover_stuck_steps() -> None:
    """On startup, reset any step data stuck in 'running' status from a previous crash/restart."""
    if not DATA_DIR.exists():
        return
    recovered = 0
    for entry in DATA_DIR.iterdir():
        if not entry.is_dir():
            continue
        for step_file_name in ["step1.json", "step2.json", "step3.json", "step4.json", "step5.json", "step6.json"]:
            step_file = entry / step_file_name
            if not step_file.exists():
                continue
            try:
                with open(step_file) as f:
                    data = json.load(f)
                changed = False

                # Top-level status
                if data.get("status") == "running":
                    data["status"] = "idle"
                    data["error"] = "Server was restarted — previous run interrupted. Please retry."
                    changed = True

                # Step 2: nested draft entries can also be stuck
                for d in data.get("drafts", []):
                    if d.get("status") == "running":
                        d["status"] = "idle"
                        d["error"] = "Server was restarted — previous run interrupted. Please retry."
                        changed = True

                if changed:
                    with open(step_file, "w") as f:
                        json.dump(data, f, indent=2)
                    recovered += 1
                    print(f"  Recovered {entry.name}/{step_file_name} — reset stuck 'running' to 'idle'")
            except Exception as e:
                print(f"  Skipped {entry.name}/{step_file_name}: {e}")
    if recovered:
        print(f"Recovery complete: {recovered} file(s) reset.")


# --- FastAPI app ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: recover stuck state, then start serving."""
    print("ArtGen server starting...")
    _recover_stuck_steps()
    print("ArtGen server started at http://localhost:8000")
    yield

app = FastAPI(title="ArtGen", version="0.1.0", lifespan=lifespan)

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


# --- Settings API ---
from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    anthropic_key: str = ""
    gemini_key: str = ""
    openai_key: str = ""


@app.get("/api/settings")
async def get_settings():
    """Return settings with masked API keys."""
    settings = load_settings()
    return {
        "anthropic_key": mask_key(settings.get("anthropic_key", "")),
        "gemini_key": mask_key(settings.get("gemini_key", "")),
        "openai_key": mask_key(settings.get("openai_key", "")),
    }


@app.put("/api/settings")
async def update_settings(body: SettingsUpdate):
    """Update settings. Only overwrite keys if non-empty values are provided."""
    settings = load_settings()
    if body.anthropic_key and "*" * (len(body.anthropic_key) - 8) not in body.anthropic_key:
        settings["anthropic_key"] = body.anthropic_key.strip()
    if body.gemini_key and "*" * (len(body.gemini_key) - 8) not in body.gemini_key:
        settings["gemini_key"] = body.gemini_key.strip()
    if body.openai_key and "*" * (len(body.openai_key) - 8) not in body.openai_key:
        settings["openai_key"] = body.openai_key.strip()
    save_settings(settings)
    return {"ok": True}


@app.post("/api/settings/validate/anthropic")
async def validate_anthropic():
    """Test the Anthropic API key with a minimal call."""
    import httpx
    settings = load_settings()
    api_key = settings.get("anthropic_key", "").strip()
    if not api_key:
        return {"valid": False, "error": "No API key configured"}

    if not api_key.startswith("sk-ant-"):
        return {"valid": False, "error": f"Key format looks wrong — Anthropic keys start with 'sk-ant-'. Your key starts with '{api_key[:8]}...'"}

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
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent",
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


# --- Project Management ---
import datetime as dt
import threading
import shutil

# In-memory project state
_current_project: dict | None = None
_current_project_path: Path | None = None

# Log buffer for SSE streaming
_log_buffer: list[dict] = []
_log_lock = threading.Lock()

# Project index file
PROJECTS_INDEX = DATA_DIR / "projects.json"


def load_project_index() -> list[dict]:
    """Load the project index from disk."""
    if PROJECTS_INDEX.exists():
        with open(PROJECTS_INDEX, "r") as f:
            return json.load(f)
    return []


def save_project_index(projects: list[dict]) -> None:
    """Save the project index to disk."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(PROJECTS_INDEX, "w") as f:
        json.dump(projects, f, indent=2)


def register_project(name: str, dir_name: str) -> None:
    """Add or update a project in the index."""
    projects = load_project_index()
    # Remove existing entry with same dir_name
    projects = [p for p in projects if p.get("dir_name") != dir_name]
    projects.append({
        "name": name,
        "dir_name": dir_name,
        "created": dt.datetime.now().isoformat(),
        "current_step": 1,
    })
    save_project_index(projects)


def unregister_project(dir_name: str) -> None:
    """Remove a project from the index."""
    projects = load_project_index()
    projects = [p for p in projects if p.get("dir_name") != dir_name]
    save_project_index(projects)


def project_dir(name: str) -> Path:
    """Get the data directory for a project name."""
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    return DATA_DIR / safe_name


def init_step_files(proj_dir: Path) -> None:
    """Create empty step data files for a new project."""
    proj_dir.mkdir(parents=True, exist_ok=True)

    step1_default = {
        "brief": "", "middle_count": 1, "cards": [],
        "status": "idle", "last_run": None, "error": None,
    }
    step2_default = {
        "drafts": [], "status": "idle", "last_run": None, "error": None,
    }
    step3_default = {
        "draft_article": "", "status": "idle", "last_run": None, "error": None,
    }
    step4_default = {
        "styled_article": "", "status": "idle", "last_run": None, "error": None,
    }
    step5_default = {
        "image_count": 3, "image_cards": [], "final_article": "", "status": "idle", "last_run": None, "error": None,
    }
    step6_default = {
        "image_cards": [], "status": "idle", "last_run": None, "error": None,
    }

    defaults = {
        "step1.json": step1_default,
        "step2.json": step2_default,
        "step3.json": step3_default,
        "step4.json": step4_default,
        "step5.json": step5_default,
        "step6.json": step6_default,
    }

    for filename, default_data in defaults.items():
        filepath = proj_dir / filename
        if not filepath.exists():
            with open(filepath, "w") as f:
                json.dump(default_data, f, indent=2)

    project_file = proj_dir / "project.json"
    if not project_file.exists():
        with open(project_file, "w") as f:
            json.dump({
                "name": proj_dir.name,
                "created": dt.datetime.now().isoformat(),
                "current_step": 1,
            }, f, indent=2)


def refresh_project_index() -> None:
    """Rebuild the project index from disk — scans data dir for project folders,
    preserving creation dates from the existing index."""
    old_index = {p["dir_name"]: p for p in load_project_index()}
    new_index = []
    if DATA_DIR.exists():
        for entry in sorted(DATA_DIR.iterdir()):
            if not entry.is_dir():
                continue
            proj_file = entry / "project.json"
            if not proj_file.exists():
                continue
            try:
                with open(proj_file) as f:
                    proj = json.load(f)
            except Exception:
                continue
            dir_name = entry.name
            created = old_index.get(dir_name, {}).get("created", proj.get("created", ""))
            new_index.append({
                "name": proj.get("name", dir_name),
                "dir_name": dir_name,
                "created": created,
                "current_step": proj.get("current_step", 1),
            })
    save_project_index(new_index)


def load_project(proj_dir: Path) -> dict:
    """Load full project state from disk."""
    project = {}
    proj_file = proj_dir / "project.json"
    if proj_file.exists():
        with open(proj_file) as f:
            project = json.load(f)

    steps = {}
    for i in range(1, 7):
        step_file = proj_dir / f"step{i}.json"
        if step_file.exists():
            with open(step_file) as f:
                steps[i] = json.load(f)
        else:
            steps[i] = {"status": "idle"}

    project["steps"] = steps
    return project


# --- Logging ---
def log_entry(level: str, step: int, message: str) -> dict:
    """Write a log entry to disk and in-memory buffer."""
    global _log_buffer
    entry = {
        "timestamp": dt.datetime.now().isoformat(),
        "level": level,
        "step": step,
        "message": message,
    }

    with _log_lock:
        _log_buffer.append(entry)
        if len(_log_buffer) > 500:
            _log_buffer = _log_buffer[-500:]

    global _current_project_path
    if _current_project_path:
        log_file = LOG_DIR / f"{_current_project_path.name}.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    print(f"[{entry['timestamp']}] [{level}] Step {step}: {message}")
    return entry


class NewProjectRequest(BaseModel):
    name: str = ""  # empty = auto-generate


@app.get("/api/project")
async def get_project():
    """Get current project metadata + all step statuses."""
    if _current_project is None:
        return {"name": None, "steps": {}, "exists": False, "dir_name": None}

    proj = load_project(_current_project_path)
    result = {
        "name": proj.get("name"),
        "dir_name": _current_project_path.name,
        "created": proj.get("created"),
        "current_step": proj.get("current_step", 1),
        "exists": True,
        "steps": {str(i): {"status": proj["steps"][i].get("status", "idle")} for i in range(1, 7)},
    }
    return result


@app.get("/api/projects")
async def list_projects():
    """List all projects from the index, refreshing from disk first."""
    refresh_project_index()
    projects = load_project_index()
    # Sort by creation date, newest first
    projects.sort(key=lambda p: p.get("created", ""), reverse=True)
    return {"projects": projects, "current": _current_project_path.name if _current_project_path else None}


@app.post("/api/project/new")
async def new_project(body: NewProjectRequest):
    """Create a new project. Auto-generates name if empty."""
    global _current_project, _current_project_path

    from datetime import datetime

    name = body.name.strip() if body.name else ""
    if not name:
        name = datetime.now().strftime("Project %b %d")

    proj_dir = project_dir(name)
    init_step_files(proj_dir)
    register_project(name, proj_dir.name)

    _current_project_path = proj_dir
    _current_project = load_project(proj_dir)

    with open(LAST_PROJECT_FILE, "w") as f:
        f.write(str(proj_dir))

    log_entry("INFO", 0, f"Project '{name}' created")
    return {"ok": True, "name": name, "dir_name": proj_dir.name, "path": str(proj_dir)}


@app.post("/api/project/load/{dir_name}")
async def load_project_by_name(dir_name: str):
    """Load a specific project by its directory name."""
    global _current_project, _current_project_path

    proj_dir = DATA_DIR / dir_name
    if not proj_dir.exists():
        return {"ok": False, "error": f"Project '{dir_name}' not found"}

    _current_project_path = proj_dir
    _current_project = load_project(proj_dir)

    with open(LAST_PROJECT_FILE, "w") as f:
        f.write(str(proj_dir))

    log_entry("INFO", 0, f"Loaded project '{_current_project.get('name', dir_name)}'")
    return {
        "ok": True,
        "name": _current_project.get("name"),
        "dir_name": dir_name,
        "created": _current_project.get("created"),
        "steps": {str(i): {"status": _current_project["steps"][i].get("status", "idle")} for i in range(1, 7)},
    }


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
        "dir_name": proj_dir.name,
        "created": _current_project.get("created"),
        "steps": {str(i): {"status": _current_project["steps"][i].get("status", "idle")} for i in range(1, 7)},
    }


@app.delete("/api/project/{dir_name}")
async def delete_project(dir_name: str):
    """Delete a project and all its data."""
    global _current_project, _current_project_path

    proj_dir = DATA_DIR / dir_name
    if not proj_dir.exists():
        return {"ok": False, "error": f"Project '{dir_name}' not found"}

    # Remove the directory
    shutil.rmtree(proj_dir)
    # Remove from index
    unregister_project(dir_name)
    # Remove log file
    log_file = LOG_DIR / f"{dir_name}.log"
    if log_file.exists():
        log_file.unlink()

    # If this was the current project, unload it
    if _current_project_path and _current_project_path.name == dir_name:
        _current_project = None
        _current_project_path = None
        if LAST_PROJECT_FILE.exists():
            LAST_PROJECT_FILE.unlink()

    log_entry("INFO", 0, f"Project '{dir_name}' deleted")
    return {"ok": True}


@app.post("/api/project/save")
async def save_project():
    """Persist current project state to disk."""
    if _current_project_path is None:
        return {"ok": False, "error": "No project loaded"}

    # Refresh the project metadata from fresh disk read
    _current_project = load_project(_current_project_path)
    register_project(_current_project.get("name", _current_project_path.name), _current_project_path.name)

    log_entry("INFO", 0, "Project saved")
    return {"ok": True}


# --- Reset ---


@app.post("/api/reset")
async def reset_all():
    """Wipe all project data, logs, and in-memory state. Destructive!"""
    global _current_project, _current_project_path, _log_buffer

    try:
        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR)
        DATA_DIR.mkdir(exist_ok=True)

        if LOG_DIR.exists():
            shutil.rmtree(LOG_DIR)
        LOG_DIR.mkdir(exist_ok=True)

        if LAST_PROJECT_FILE.exists():
            LAST_PROJECT_FILE.unlink()

    except Exception as e:
        return {"ok": False, "error": f"Failed to reset: {str(e)}"}

    _current_project = None
    _current_project_path = None
    with _log_lock:
        _log_buffer = []

    log_entry("INFO", 0, "All data wiped via reset")
    return {"ok": True}


# --- System Log API ---
from fastapi.responses import StreamingResponse
import asyncio


@app.get("/api/log")
async def get_log():
    """Get all log entries for the current project."""
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

    with _log_lock:
        for entry in _log_buffer:
            if entry not in entries:
                entries.append(entry)

    return {"entries": entries, "project": _current_project_path.name if _current_project_path else None}


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


# --- Step 1: Subtopic Planning ---

STEP1_DEFAULT_PARAMS = {
    "model": "claude-haiku-4-5",
    "temperature": 1.0,
    "max_tokens": 4096,
    "thinking_budget": 1600,
    "effort": "high",
    "system_prompt": (
        "You are designing the outline for a persuasive article. Your outline will be handed off to a draft writer "
        "— your job is to give them the best possible ammunition.\n\n"
        "Given a brief, you will produce a structured outline broken into cards. Each card represents one section "
        "of the finished article. There are three card types, each with a distinct purpose:\n\n"
        "BEGINNING (1 card): The opener. Hook the reader immediately — don’t waste words on throat-clearing. "
        "Introduce the topic with urgency, state the thesis clearly, and make the reader understand why this matters "
        "right now. The angle should be the article’s core argument. The ammo should be a braindump of everything "
        "the draft writer could use: startling facts, provocative questions, a compelling anecdote or scene, "
        "the stakes if the reader ignores this, why conventional wisdom is wrong, what’s at risk.\n\n"
        "MIDDLE (N cards, user-specified): The argument chain. Each middle card advances ONE specific claim that "
        "supports the thesis. No two cards should make the same argument — if they overlap, sharpen the distinction "
        "or merge them. The angle is the specific claim this card proves. The ammo should be a maximalist braindump: "
        "evidence of all kinds (data, examples, historical parallels, expert takes, counter-arguments to preempt, "
        "case studies, institutional failures, personal stories, logical reasoning, metaphors, rhetorical strategies). "
        "Throw in everything — the draft writer will curate. Don’t hold back.\n\n"
        "END (1 card): The closer. Drive the thesis home with force. Don’t just summarize — make the reader feel "
        "something. Address the \"so what?\" question. The angle should be the lasting impression you want to leave. "
        "The ammo should include: callbacks to the opening, broader implications, what happens next, a call to action "
        "or a shift in perspective, a memorable final image or line.\n\n"
        "THE AMMO FIELD IS THE MOST IMPORTANT OUTPUT. It is NOT the draft itself — it’s raw material. "
        "Be generous, messy, maximalist. Dump every relevant fact, angle, example, rhetorical move, "
        "counter-argument, and idea you can generate. The draft writer needs a rich pile to work from.\n\n"
        "Your output must be valid JSON matching this schema:\n"
        "{\n"
        "  \"cards\": [\n"
        "    {\n"
        "      \"id\": 1,\n"
        "      \"type\": \"beginning\",\n"
        "      \"title\": \"A sharp, clickable section headline\",\n"
        "      \"angle\": \"The argument this card makes — the claim we’re advancing\",\n"
        "      \"ammo\": \"THE CRITICAL FIELD. A generous braindump of everything the draft writer needs: facts, examples, counter-arguments, rhetorical strategies, data points, historical parallels, metaphors, emotional beats. Messy and maximalist — the writer will curate from this pile.\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Card types MUST be exactly ‘beginning’, ‘middle’, or ‘end’ — no other values.\n"
        "- Exactly 1 beginning card (id=1) and 1 end card (last id). Middle cards fill the gap.\n"
        "- Every card must earn its place. No filler sections.\n"
        "- Titles should sound like something you’d click on.\n"
        "- Angles must be arguable — if nobody could disagree, sharpen it.\n"
        "- Ammo should be long, rich, and varied. More is better. Don’t self-censor.\n"
        "- Cover the brief completely — no major aspect unexplored.\n"
        "- Order matters: open strong, build momentum, end memorably.\n\n"
        "Return ONLY the JSON object, no preamble, no commentary."
    ),
}

STEP1_MODELS = [
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5 (Fastest)"},
    {"id": "claude-sonnet-5", "name": "Claude Sonnet 5 (Balanced)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-8", "name": "Claude Opus 4.8 (Most Capable)"},
    {"id": "claude-fable-5", "name": "Claude Fable 5 (Best)"},
]


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
        "brief": "", "middle_count": 1, "cards": [],
        "status": "idle", "last_run": None, "error": None,
    }


def save_step1_data(data: dict) -> bool:
    """Persist Step 1 data to disk. Returns False if no project is loaded."""
    global _current_project_path
    if not _current_project_path:
        return False
    step_file = _current_project_path / "step1.json"
    with open(step_file, "w") as f:
        json.dump(data, f, indent=2)
    return True


class Step1DataUpdate(BaseModel):
    brief: str = ""
    middle_count: int = 1
    cards: list[dict] = []
    status: str = "idle"
    error: str | None = None


@app.get("/api/step/1/data")
async def get_step1():
    """Get Step 1 stored data."""
    return get_step1_data()


@app.put("/api/step/1/data")
async def update_step1(body: Step1DataUpdate):
    """Update Step 1 data (manual edit)."""
    data = body.model_dump()
    if not save_step1_data(data):
        return {"ok": False, "error": "No project loaded. Go to Project and create or load one first."}
    log_entry("INFO", 1, f"Step 1 data updated. Brief length: {len(data['brief'])}, Cards: {len(data['cards'])}")
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
    thinking_budget: int = 1600
    effort: str = "high"
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

    data = get_step1_data()
    params = get_step1_params()
    settings = load_settings()

    if not _current_project_path:
        log_entry("ERROR", 1, "No project loaded — cannot run Step 1")
        return {"ok": False, "error": "No project loaded. Go to Project and create or load one first."}

    api_key = settings.get("anthropic_key", "").strip()
    if not api_key:
        log_entry("ERROR", 1, "No Anthropic API key configured")
        data["status"] = "failed"
        data["error"] = "No Anthropic API key configured. Go to Settings to add one."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    brief = data.get("brief", "").strip()
    middle_count = data.get("middle_count", 1)

    if not brief:
        log_entry("ERROR", 1, "No brief provided")
        data["status"] = "failed"
        data["error"] = "No brief provided. Write a brief describing what you want to cover."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    if middle_count < 1 or middle_count > 20:
        log_entry("ERROR", 1, f"Invalid middle count: {middle_count}")
        data["status"] = "failed"
        data["error"] = "Middle section count must be between 1 and 20."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    data["status"] = "running"
    data["error"] = None
    save_step1_data(data)

    model = params.get("model", "claude-haiku-4-5")
    temperature = params.get("temperature", 1.0)
    max_tokens = params.get("max_tokens", 4096)
    thinking_budget = params.get("thinking_budget", 1600)
    effort = params.get("effort", "high")
    system_prompt = params.get("system_prompt", STEP1_DEFAULT_PARAMS["system_prompt"])

    total_cards = middle_count + 2  # beginning + N middle + end

    user_message = (
        f"BRIEF: {brief}\n\n"
        f"Generate 1 beginning card, {middle_count} middle cards, and 1 end card "
        f"({total_cards} cards total). Each card needs a type, title, angle, and ammo "
        f"as specified in the output schema.\n\n"
        f"Remember: the AMMO field is the most important output. It's a braindump of "
        f"raw material for the draft writer — be generous, messy, and maximalist. "
        f"Dump every relevant fact, angle, example, counter-argument, and rhetorical "
        f"idea you can generate.\n\n"
        f"Return ONLY valid JSON."
    )

    output_schema = {
        "type": "object",
        "properties": {
            "cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "1-based index"},
                        "type": {"type": "string", "description": "Card type: 'beginning', 'middle', or 'end'"},
                        "title": {"type": "string", "description": "Sharp, clickable section headline"},
                        "angle": {"type": "string", "description": "The argument this card makes — the claim we're advancing"},
                        "ammo": {"type": "string", "description": "Braindump of raw material: facts, examples, counter-arguments, rhetorical strategies, data, metaphors — everything the draft writer needs"},
                    },
                    "required": ["id", "type", "title", "angle", "ammo"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["cards"],
        "additionalProperties": False,
    }

    # Build model-appropriate thinking config
    is_haiku = model.startswith("claude-haiku")
    if is_haiku:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 1.0,  # required for thinking on Haiku
            "system": system_prompt,
            "thinking": {"type": "enabled", "budget_tokens": thinking_budget},
            "messages": [{"role": "user", "content": user_message}],
            "output_config": {
                "format": {"type": "json_schema", "schema": output_schema},
            },
        }
        log_entry("INFO", 1, f"Calling Anthropic API. Model: {model}, Brief length: {len(brief)}, Middle count: {middle_count}, Thinking budget: {thinking_budget}")
    else:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "thinking": {"type": "adaptive"},
            "output_config": {
                "format": {"type": "json_schema", "schema": output_schema},
                "effort": effort,
            },
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 1, f"Calling Anthropic API. Model: {model}, Brief length: {len(brief)}, Middle count: {middle_count}, Effort: {effort}")

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
                content_blocks = result.get("content", [])
                response_text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        response_text += block.get("text", "")

                try:
                    parsed = json.loads(response_text)
                    cards = parsed.get("cards", [])

                    expected = total_cards
                    if len(cards) != expected:
                        log_entry("WARN", 1, f"Model returned {len(cards)} cards, expected {expected}. Using what was returned.")
                        cards = cards[:expected]

                    for i, card in enumerate(cards):
                        card["id"] = i + 1
                        # Ensure type is valid
                        if card.get("type") not in ("beginning", "middle", "end"):
                            if i == 0:
                                card["type"] = "beginning"
                            elif i == len(cards) - 1:
                                card["type"] = "end"
                            else:
                                card["type"] = "middle"

                    data["cards"] = cards
                    data["status"] = "completed"
                    data["last_run"] = dt.datetime.now().isoformat()
                    data["error"] = None
                    save_step1_data(data)

                    log_entry("INFO", 1, f"Step 1 completed. Generated {len(cards)} cards.")
                    return {"ok": True, "cards": cards}

                except json.JSONDecodeError as parse_err:
                    log_entry("ERROR", 1, f"Failed to parse model response as JSON: {parse_err}")
                    # Fallback: try to extract cards from text
                    cards = _parse_cards_fallback(response_text, total_cards)
                    if cards:
                        data["cards"] = cards
                        data["status"] = "completed"
                        data["last_run"] = dt.datetime.now().isoformat()
                        data["error"] = None
                        save_step1_data(data)
                        log_entry("WARN", 1, f"Step 1 completed via fallback. Generated {len(cards)} cards.")
                        return {"ok": True, "cards": cards}
                    else:
                        data["status"] = "failed"
                        data["error"] = f"Failed to parse model response. Raw: {response_text[:500]}"
                        save_step1_data(data)
                        return {"ok": False, "error": data["error"]}

            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    err = err_data.get("error", {})
                    error_detail = err.get("message", resp.text[:500])
                except Exception:
                    error_detail = resp.text[:500]

                log_entry("ERROR", 1, f"Anthropic API error ({resp.status_code}): {error_detail}")

                if resp.status_code == 401:
                    data["error"] = "Authentication failed. Check your API key in Settings — it may have whitespace or be incorrect."
                elif resp.status_code == 403:
                    data["error"] = "Access denied. Your API key may not have permission for this model or endpoint."
                elif resp.status_code == 400:
                    data["error"] = f"Bad request: {error_detail}"
                elif resp.status_code == 429:
                    data["error"] = "Rate limited. Wait a moment and try again."
                else:
                    data["error"] = f"API error ({resp.status_code}): {error_detail}"

                data["status"] = "failed"
                save_step1_data(data)
                return {"ok": False, "error": data["error"]}

    except httpx.TimeoutException:
        log_entry("ERROR", 1, "Anthropic API request timed out (120s)")
        data["status"] = "failed"
        data["error"] = "Request timed out after 120 seconds. Try a faster model or fewer middle sections."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    except Exception as e:
        log_entry("ERROR", 1, f"Unexpected error: {str(e)}")
        data["status"] = "failed"
        data["error"] = f"Unexpected error: {str(e)}"
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}


def _parse_cards_fallback(text: str, total_cards: int) -> list[dict] | None:
    """Attempt to parse cards from unstructured text."""
    import re
    lines = text.strip().split("\n")
    cards = []
    pattern = re.compile(r"^\s*(?:\d+[.)]\s*)?(?:\*\*\s*)?(.+?)(?:\*\*\s*)?$")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            title = match.group(1).strip()
            if len(title) > 3 and not title.lower().startswith(("here", "the ", "these", "below", "above")):
                cards.append(title)

    if len(cards) >= total_cards:
        return [{"id": i + 1, "type": "beginning" if i == 0 else "end" if i == total_cards - 1 else "middle", "title": cards[i], "angle": "", "ammo": ""} for i in range(total_cards)]
    elif len(cards) > 0:
        return [{"id": i + 1, "type": "beginning" if i == 0 else "end" if i == len(cards) - 1 else "middle", "title": cards[i], "angle": "", "ammo": ""} for i in range(len(cards))]
    return None


# --- Step 2: Draft Writing ---

STEP2_DEFAULT_PARAMS = {
    "model": "claude-haiku-4-5",
    "temperature": 1.0,
    "max_tokens": 4096,
    "thinking_budget": 1600,
    "effort": "high",
    "system_prompt": (
        "You are a draft writer. You will be given an outline card with a type, title, angle, "
        "and an ammunition braindump. Your job is to weave the ammunition into a compelling "
        "first draft for this section of the article.\n\n"
        "Use your thinking to:\n"
        "1. Identify the strongest material in the ammo — what hits hardest?\n"
        "2. Decide on the best opening sentence — hook the reader immediately.\n"
        "3. Organize the flow — what order makes the argument land best?\n"
        "4. Choose which evidence/arguments to lead with and which to save for later.\n"
        "5. Figure out how to transition smoothly from the previous section and into the next.\n\n"
        "Write in a persuasive, engaging voice. Make the argument with conviction. "
        "Don't hedge, don't over-qualify, don't use academic throat-clearing. "
        "This is a first draft — not final. Aim for quality and flow, not perfection.\n\n"
        "Write ONLY the section content — no meta-commentary, no notes to yourself, "
        "no \"here's a draft\" preambles. Just the draft text."
    ),
}

STEP2_MODELS = [
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5 (Fastest)"},
    {"id": "claude-sonnet-5", "name": "Claude Sonnet 5 (Balanced)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-8", "name": "Claude Opus 4.8 (Most Capable)"},
    {"id": "claude-fable-5", "name": "Claude Fable 5 (Best)"},
]


def get_step2_params() -> dict:
    """Load Step 2 params from disk or return defaults."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step2_params.json"
        if params_file.exists():
            with open(params_file) as f:
                return json.load(f)
    return dict(STEP2_DEFAULT_PARAMS)


def save_step2_params(params: dict) -> None:
    """Persist Step 2 params to disk."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step2_params.json"
        with open(params_file, "w") as f:
            json.dump(params, f, indent=2)


def get_step2_data() -> dict:
    """Load Step 2 data from disk."""
    global _current_project_path
    if _current_project_path:
        step_file = _current_project_path / "step2.json"
        if step_file.exists():
            with open(step_file) as f:
                return json.load(f)
    return {
        "drafts": [], "status": "idle", "last_run": None, "error": None,
    }


def save_step2_data(data: dict) -> bool:
    """Persist Step 2 data to disk. Returns False if no project is loaded."""
    global _current_project_path
    if not _current_project_path:
        return False
    step_file = _current_project_path / "step2.json"
    with open(step_file, "w") as f:
        json.dump(data, f, indent=2)
    return True


class Step2DataUpdate(BaseModel):
    drafts: list[dict] = []
    status: str = "idle"
    error: str | None = None


class Step2ParamsUpdate(BaseModel):
    model: str = "claude-haiku-4-5"
    temperature: float = 1.0
    max_tokens: int = 4096
    thinking_budget: int = 1600
    effort: str = "high"
    system_prompt: str = ""


@app.get("/api/step/2/data")
async def get_step2():
    """Get Step 2 stored data."""
    return get_step2_data()


@app.put("/api/step/2/data")
async def update_step2(body: Step2DataUpdate):
    """Update Step 2 data (manual edit)."""
    data = body.model_dump()
    if not save_step2_data(data):
        return {"ok": False, "error": "No project loaded. Go to Project and create or load one first."}
    log_entry("INFO", 2, f"Step 2 data updated. Drafts: {len(data['drafts'])}")
    return {"ok": True}


@app.get("/api/step/2/params")
async def get_step2_params_route():
    """Get Step 2 parameters."""
    params = get_step2_params()
    params["available_models"] = STEP2_MODELS
    return params


@app.put("/api/step/2/params")
async def update_step2_params(body: Step2ParamsUpdate):
    """Update Step 2 parameters."""
    params = body.model_dump()
    save_step2_params(params)
    log_entry("INFO", 2, f"Step 2 params updated. Model: {params['model']}, Temp: {params['temperature']}, Thinking budget: {params.get('thinking_budget', 0)}")
    return {"ok": True}


@app.post("/api/step/2/run")
async def run_step2():
    """Execute Step 2: draft ALL cards sequentially using Anthropic with thinking."""
    step1_data = get_step1_data()
    step2_data = get_step2_data()
    cards = step1_data.get("cards", [])

    if not _current_project_path:
        return {"ok": False, "error": "No project loaded."}

    if not cards:
        return {"ok": False, "error": "No cards from Step 1. Run Step 1 first."}

    # Initialize draft entries from Step 1 cards
    step2_data["drafts"] = _init_draft_entries(cards)
    step2_data["status"] = "running"
    step2_data["error"] = None
    save_step2_data(step2_data)

    log_entry("INFO", 2, f"Starting draft writing for {len(cards)} cards")

    # Run each sequentially
    for i in range(len(step2_data["drafts"])):
        await _draft_single_card(step2_data, i)

    _update_step2_aggregate_status(step2_data)
    save_step2_data(step2_data)

    log_entry("INFO", 2, f"Step 2 drafting complete. Status: {step2_data['status']}")
    return {"ok": True, "drafts": step2_data["drafts"]}


@app.post("/api/step/2/run-card/{card_id}")
async def run_step2_card(card_id: int):
    """Execute Step 2: draft a SINGLE card."""
    step2_data = get_step2_data()
    drafts = step2_data.get("drafts", [])

    idx = _find_draft_index_by_card_id(drafts, card_id)

    # Auto-create the draft entry if it doesn't exist yet
    if idx is None:
        step1_data = get_step1_data()
        cards = step1_data.get("cards", [])
        card = next((c for c in cards if c.get("id") == card_id), None)
        if card is None:
            log_entry("ERROR", 2, f"Card ID {card_id} not found in Step 1 cards")
            return {"ok": False, "error": f"Card ID {card_id} not found in Step 1 or Step 2."}
        drafts.append({
            "card_id": card_id,
            "card_type": card.get("type", "middle"),
            "card_title": card.get("title", ""),
            "card_angle": card.get("angle", ""),
            "card_ammo": card.get("ammo", ""),
            "draft": "",
            "status": "idle",
            "error": None,
            "last_run": None,
        })
        idx = len(drafts) - 1
        step2_data["drafts"] = drafts
        log_entry("INFO", 2, f"Auto-created draft entry for card #{card_id}")

    step2_data["status"] = "running"
    drafts[idx]["status"] = "running"
    drafts[idx]["error"] = None
    save_step2_data(step2_data)

    log_entry("INFO", 2, f"Drafting card #{card_id}")

    await _draft_single_card(step2_data, idx)

    _update_step2_aggregate_status(step2_data)
    save_step2_data(step2_data)

    return {"ok": True, "draft": drafts[idx]}


# --- Step 2 Core Functions ---


def _init_draft_entries(cards: list[dict]) -> list[dict]:
    """Create draft entries from Step 1 cards, preserving completed drafts."""
    existing = {}
    step2_data = get_step2_data()
    for d in step2_data.get("drafts", []):
        existing[d.get("card_id")] = d

    drafts = []
    for card in cards:
        cid = card.get("id")
        if cid in existing and existing[cid].get("status") == "completed":
            drafts.append(existing[cid])
        else:
            drafts.append({
                "card_id": cid,
                "card_type": card.get("type", "middle"),
                "card_title": card.get("title", ""),
                "card_angle": card.get("angle", ""),
                "card_ammo": card.get("ammo", ""),
                "draft": existing[cid].get("draft", "") if cid in existing else "",
                "status": "idle",
                "error": None,
                "last_run": existing[cid].get("last_run") if cid in existing else None,
            })
    return drafts


def _find_draft_index_by_card_id(drafts: list[dict], card_id: int) -> int | None:
    """Find the index of a draft entry by its card_id."""
    for i, d in enumerate(drafts):
        if d.get("card_id") == card_id:
            return i
    return None


def _update_step2_aggregate_status(step2_data: dict) -> None:
    """Update the top-level status based on individual draft statuses."""
    drafts = step2_data.get("drafts", [])
    if not drafts:
        step2_data["status"] = "idle"
        return

    statuses = [d.get("status", "idle") for d in drafts]
    if any(s == "running" for s in statuses):
        step2_data["status"] = "running"
    elif all(s == "completed" for s in statuses):
        step2_data["status"] = "completed"
        step2_data["last_run"] = dt.datetime.now().isoformat()
    elif all(s == "failed" for s in statuses):
        step2_data["status"] = "failed"
    elif any(s == "completed" for s in statuses):
        step2_data["status"] = "partial"
    else:
        step2_data["status"] = "idle"


async def _draft_single_card(step2_data: dict, idx: int) -> None:
    """Write a first draft for one card using Anthropic with extended thinking. Retries once on failure."""
    import httpx
    import asyncio

    draft_entry = step2_data["drafts"][idx]
    params = get_step2_params()
    settings = load_settings()

    api_key = settings.get("anthropic_key", "").strip()
    if not api_key:
        draft_entry["status"] = "failed"
        draft_entry["error"] = "No Anthropic API key configured. Go to Settings to add one."
        save_step2_data(step2_data)
        return

    model = params.get("model", "claude-haiku-4-5")
    temperature = params.get("temperature", 1.0)
    max_tokens = params.get("max_tokens", 4096)
    thinking_budget = params.get("thinking_budget", 1600)
    effort = params.get("effort", "high")
    system_prompt = params.get("system_prompt", STEP2_DEFAULT_PARAMS["system_prompt"])

    # Build user message — only the info the model needs for THIS card
    card_type = draft_entry.get("card_type", "middle")
    card_title = draft_entry.get("card_title", "")
    card_angle = draft_entry.get("card_angle", "")
    card_ammo = draft_entry.get("card_ammo", "")

    user_message = (
        f"CARD TYPE: {card_type}\n"
        f"TITLE: {card_title}\n"
        f"ANGLE: {card_angle}\n\n"
        f"AMMUNITION:\n{card_ammo}\n\n"
        f"Write the first draft for this section."
    )

    log_entry("INFO", 2, (
        f"Prompt for card #{draft_entry.get('card_id')}:\n"
        f"--- SYSTEM ---\n{system_prompt[:300]}...\n"
        f"--- USER ---\n{user_message[:500]}..."
    ))

    # Build model-appropriate thinking config
    # Haiku 4.5: uses budget_tokens, temp must be 1.0, no effort
    # Sonnet 5 / Opus 4.8 / Fable 5: uses adaptive thinking + effort, no temp restriction
    is_haiku = model.startswith("claude-haiku")
    if is_haiku:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 1.0,  # required for thinking on Haiku
            "system": system_prompt,
            "thinking": {"type": "enabled", "budget_tokens": thinking_budget},
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 2, f"Drafting card #{draft_entry.get('card_id')} with {model} (thinking budget: {thinking_budget})")
    else:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 2, f"Drafting card #{draft_entry.get('card_id')} with {model} (adaptive thinking, effort: {effort})")

    # Attempt 1
    success = await _call_anthropic_draft(step2_data, idx, api_key, request_body, attempt=1)

    # Retry after 3s delay on failure
    if not success:
        log_entry("WARN", 2, f"Card #{draft_entry.get('card_id')} failed attempt 1. Retrying in 3s...")
        await asyncio.sleep(3)
        success = await _call_anthropic_draft(step2_data, idx, api_key, request_body, attempt=2)

    if success:
        draft_entry["status"] = "completed"
        draft_entry["last_run"] = dt.datetime.now().isoformat()
        log_entry("INFO", 2, f"Card #{draft_entry.get('card_id')} draft completed")
    # If failed, status is already set to "failed" by _call_anthropic_draft


async def _call_anthropic_draft(
    step2_data: dict, idx: int, api_key: str,
    request_body: dict, attempt: int,
) -> bool:
    """Make a single Anthropic API call for drafting. Returns True on success, False on failure."""
    import httpx

    draft_entry = step2_data["drafts"][idx]

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
                content_blocks = result.get("content", [])
                response_text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        response_text += block.get("text", "")

                if response_text.strip():
                    draft_entry["draft"] = response_text.strip()
                    save_step2_data(step2_data)
                    usage = result.get("usage", {})
                    log_entry("INFO", 2, (
                        f"Card #{draft_entry.get('card_id')} — "
                        f"draft {len(response_text)} chars, "
                        f"input_tokens={usage.get('input_tokens', 'N/A')}, "
                        f"output_tokens={usage.get('output_tokens', 'N/A')}"
                    ))
                    return True
                else:
                    draft_entry["status"] = "failed"
                    draft_entry["error"] = f"Model returned empty response (attempt {attempt})"
                    save_step2_data(step2_data)
                    log_entry("ERROR", 2, f"Card #{draft_entry.get('card_id')} — empty response (attempt {attempt})")
                    return False

            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    err = err_data.get("error", {})
                    error_detail = err.get("message", resp.text[:500])
                except Exception:
                    error_detail = resp.text[:500]

                log_entry("ERROR", 2, f"Anthropic API error ({resp.status_code}) attempt {attempt}: {error_detail}")

                draft_entry["status"] = "failed"
                if resp.status_code == 401:
                    draft_entry["error"] = "Authentication failed. Check your Anthropic API key in Settings."
                elif resp.status_code == 403:
                    draft_entry["error"] = "Access denied. Your API key may not have permission for this model."
                elif resp.status_code == 429:
                    draft_entry["error"] = f"Rate limited (attempt {attempt}). Wait a moment and try again."
                elif resp.status_code == 400:
                    draft_entry["error"] = f"Bad request (attempt {attempt}): {error_detail}"
                elif resp.status_code == 503:
                    draft_entry["error"] = f"Service unavailable (attempt {attempt}). Try again shortly."
                else:
                    draft_entry["error"] = f"API error ({resp.status_code}) attempt {attempt}: {error_detail}"
                save_step2_data(step2_data)
                return False

    except httpx.TimeoutException:
        draft_entry["status"] = "failed"
        draft_entry["error"] = f"Request timed out after 120s (attempt {attempt})"
        save_step2_data(step2_data)
        log_entry("ERROR", 2, f"Anthropic timeout on attempt {attempt} for card #{draft_entry.get('card_id')}")
        return False

    except Exception as e:
        draft_entry["status"] = "failed"
        draft_entry["error"] = f"Unexpected error (attempt {attempt}): {str(e)}"
        save_step2_data(step2_data)
        log_entry("ERROR", 2, f"Anthropic unexpected error attempt {attempt}: {str(e)}")
        return False


# --- Step 3: Article Synthesis ---

STEP3_DEFAULT_PARAMS = {
    "model": "claude-haiku-4-5",
    "temperature": 1.0,
    "max_tokens": 8192,
    "thinking_budget": 1600,
    "effort": "high",
    "system_prompt": (
        "You are a masterful article editor and writer. You will receive a set of draft sections "
        "written by a draft writer — one section per card in an outline. Your job is to synthesize "
        "them into one cohesive, compelling, finished article.\n\n"
        "This is not just copy-paste stitching. You must:\n"
        "1. Weave the sections together so they flow naturally — one idea leading into the next. "
        "Fix any abrupt transitions. Make it feel like a single voice wrote the entire piece.\n"
        "2. Add style, tone, and personality. Be witty, observational, attention-grabbing. "
        "Be interesting. Be funny where appropriate. Don't be dry or academic — this should "
        "read like a great magazine feature or a smart, opinionated newsletter.\n"
        "3. Strengthen the opening hook — the first paragraph must grab the reader and make "
        "them need to keep reading. Strengthen the closing — leave the reader with something "
        "to think about, a shift in perspective, or a memorable final image.\n"
        "4. Cut filler. Tighten weak sentences. If a paragraph drags, compress it or kill it. "
        "Every sentence should earn its place.\n"
        "5. Keep the substance. The draft sections contain arguments, evidence, and ideas — "
        "don't lose them. Your job is to elevate the presentation, not gut the content.\n"
        "6. Match the structure to the content. Use paragraph breaks, rhythm, and pacing to "
        "keep the reader engaged. Vary sentence length. Read like a human wrote it for humans.\n\n"
        "Output the full article — no meta-commentary, no notes to yourself, no \"here's the "
        "final draft\" preamble. Just the article text, ready to publish."
    ),
}

STEP3_MODELS = [
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5 (Fastest)"},
    {"id": "claude-sonnet-5", "name": "Claude Sonnet 5 (Balanced)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-8", "name": "Claude Opus 4.8 (Most Capable)"},
    {"id": "claude-fable-5", "name": "Claude Fable 5 (Best)"},
]


def get_step3_params() -> dict:
    """Load Step 3 params from disk or return defaults."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step3_params.json"
        if params_file.exists():
            with open(params_file) as f:
                return json.load(f)
    return dict(STEP3_DEFAULT_PARAMS)


def save_step3_params(params: dict) -> None:
    """Persist Step 3 params to disk."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step3_params.json"
        with open(params_file, "w") as f:
            json.dump(params, f, indent=2)


def get_step3_data() -> dict:
    """Load Step 3 data from disk."""
    global _current_project_path
    if _current_project_path:
        step_file = _current_project_path / "step3.json"
        if step_file.exists():
            with open(step_file) as f:
                return json.load(f)
    return {
        "draft_article": "", "status": "idle", "last_run": None, "error": None,
    }


def save_step3_data(data: dict) -> bool:
    """Persist Step 3 data to disk. Returns False if no project is loaded."""
    global _current_project_path
    if not _current_project_path:
        return False
    step_file = _current_project_path / "step3.json"
    with open(step_file, "w") as f:
        json.dump(data, f, indent=2)
    return True


class Step3DataUpdate(BaseModel):
    draft_article: str = ""
    status: str = "idle"
    error: str | None = None


class Step3ParamsUpdate(BaseModel):
    model: str = "claude-haiku-4-5"
    temperature: float = 1.0
    max_tokens: int = 8192
    thinking_budget: int = 1600
    effort: str = "high"
    system_prompt: str = ""


@app.get("/api/step/3/data")
async def get_step3():
    """Get Step 3 stored data."""
    return get_step3_data()


@app.put("/api/step/3/data")
async def update_step3(body: Step3DataUpdate):
    """Update Step 3 data (manual edit)."""
    data = body.model_dump()
    if not save_step3_data(data):
        return {"ok": False, "error": "No project loaded. Go to Project and create or load one first."}
    log_entry("INFO", 3, f"Step 3 data updated. Article length: {len(data.get('draft_article', ''))}")
    return {"ok": True}


@app.get("/api/step/3/params")
async def get_step3_params_route():
    """Get Step 3 parameters."""
    params = get_step3_params()
    params["available_models"] = STEP3_MODELS
    return params


@app.put("/api/step/3/params")
async def update_step3_params(body: Step3ParamsUpdate):
    """Update Step 3 parameters."""
    params = body.model_dump()
    save_step3_params(params)
    log_entry("INFO", 3, f"Step 3 params updated. Model: {params['model']}, Temp: {params['temperature']}, Thinking budget: {params.get('thinking_budget', 0)}")
    return {"ok": True}


@app.post("/api/step/3/run")
async def run_step3():
    """Execute Step 3: synthesize all Step 2 drafts into a final article."""
    import httpx
    import asyncio

    step2_data = get_step2_data()
    step3_data = get_step3_data()
    params = get_step3_params()
    settings = load_settings()

    if not _current_project_path:
        return {"ok": False, "error": "No project loaded."}

    # Validate Step 2 is done
    drafts = step2_data.get("drafts", [])
    if not drafts:
        return {"ok": False, "error": "No drafts from Step 2. Run Step 2 first."}

    all_completed = all(d.get("status") == "completed" for d in drafts)
    if not all_completed:
        pending = [d.get("card_title", f"Card #{d.get('card_id')}") for d in drafts if d.get("status") != "completed"]
        return {"ok": False, "error": f"Not all drafts are completed. Still pending: {', '.join(pending[:5])}"}

    api_key = settings.get("anthropic_key", "").strip()
    if not api_key:
        step3_data["status"] = "failed"
        step3_data["error"] = "No Anthropic API key configured. Go to Settings to add one."
        save_step3_data(step3_data)
        return {"ok": False, "error": step3_data["error"]}

    step3_data["status"] = "running"
    step3_data["error"] = None
    save_step3_data(step3_data)

    model = params.get("model", "claude-haiku-4-5")
    temperature = params.get("temperature", 1.0)
    max_tokens = params.get("max_tokens", 8192)
    thinking_budget = params.get("thinking_budget", 1600)
    effort = params.get("effort", "high")
    system_prompt = params.get("system_prompt", STEP3_DEFAULT_PARAMS["system_prompt"])

    # Build user message — stitch all drafts together
    sections = []
    for i, d in enumerate(drafts, 1):
        card_type = d.get("card_type", "middle")
        card_title = d.get("card_title", "")
        draft_text = d.get("draft", "")
        sections.append(
            f"SECTION {i}: {card_type.upper()} — {card_title}\n\n{draft_text}"
        )
    stitched = "\n\n---\n\n".join(sections)

    user_message = (
        f"You have {len(drafts)} draft sections written by a draft writer. "
        f"Your job is to synthesize them into one cohesive, compelling final article.\n\n"
        f"DRAFT SECTIONS:\n\n{stitched}\n\n"
        f"---\n\n"
        f"Synthesize these into the final article now. Weave them together with style, "
        f"wit, and a strong narrative arc. Make it read like one voice. "
        f"Fix transitions. Tighten where needed. Strengthen the opening and closing. "
        f"Output the full article — nothing else."
    )

    log_entry("INFO", 3, (
        f"Synthesizing {len(drafts)} drafts into final article.\n"
        f"--- SYSTEM ---\n{system_prompt[:300]}...\n"
        f"--- USER ---\n{user_message[:500]}..."
    ))

    # Build model-appropriate thinking config
    is_haiku = model.startswith("claude-haiku")
    if is_haiku:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 1.0,
            "system": system_prompt,
            "thinking": {"type": "enabled", "budget_tokens": thinking_budget},
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 3, f"Synthesizing with {model} (thinking budget: {thinking_budget})")
    else:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 3, f"Synthesizing with {model} (adaptive thinking, effort: {effort})")

    # Retry loop — 2 attempts
    success = False
    for attempt in range(1, 3):
        try:
            async with httpx.AsyncClient(timeout=180) as client:
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
                content_blocks = result.get("content", [])
                response_text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        response_text += block.get("text", "")

                if response_text.strip():
                    step3_data["draft_article"] = response_text.strip()
                    step3_data["status"] = "completed"
                    step3_data["last_run"] = dt.datetime.now().isoformat()
                    step3_data["error"] = None
                    save_step3_data(step3_data)
                    usage = result.get("usage", {})
                    log_entry("INFO", 3, (
                        f"Step 3 completed — article {len(response_text)} chars, "
                        f"input_tokens={usage.get('input_tokens', 'N/A')}, "
                        f"output_tokens={usage.get('output_tokens', 'N/A')}"
                    ))
                    return {"ok": True, "draft_article": step3_data["draft_article"]}
                else:
                    log_entry("ERROR", 3, f"Step 3 — empty response (attempt {attempt})")
                    step3_data["status"] = "failed"
                    step3_data["error"] = f"Model returned empty response (attempt {attempt})"
            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    err = err_data.get("error", {})
                    error_detail = err.get("message", resp.text[:500])
                except Exception:
                    error_detail = resp.text[:500]

                log_entry("ERROR", 3, f"Anthropic API error ({resp.status_code}) attempt {attempt}: {error_detail}")
                step3_data["status"] = "failed"
                step3_data["error"] = f"API error ({resp.status_code}) attempt {attempt}: {error_detail}"

        except httpx.TimeoutException:
            log_entry("ERROR", 3, f"Anthropic timeout on attempt {attempt}")
            step3_data["status"] = "failed"
            step3_data["error"] = f"Request timed out after 180s (attempt {attempt})"
        except Exception as e:
            log_entry("ERROR", 3, f"Anthropic unexpected error attempt {attempt}: {str(e)}")
            step3_data["status"] = "failed"
            step3_data["error"] = f"Unexpected error (attempt {attempt}): {str(e)}"

        # Retry with delay if not last attempt
        if attempt == 1:
            log_entry("WARN", 3, "Step 3 failed attempt 1. Retrying in 3s...")
            await asyncio.sleep(3)

    save_step3_data(step3_data)
    return {"ok": False, "error": step3_data["error"]}


# --- Step 4: Style Rewrite ---

STEP4_DEFAULT_PARAMS = {
    "model": "claude-haiku-4-5",
    "temperature": 1.0,
    "max_tokens": 8192,
    "thinking_budget": 1600,
    "effort": "high",
    "system_prompt": (
        "You are a Cracked.com writer circa 2012. Not a journalist. Not an educator. A comedian "
        "who happens to be armed with facts and is going to make you laugh so hard you don't "
        "notice you're learning something until it's already lodged in your brain.\n\n"
        "YOUR JOB:\n"
        "Make the reader laugh first, think second. The information matters — but it only lands "
        "BECAUSE the comedy softens them up. You're not writing a textbook with jokes sprinkled "
        "on top. You're writing a comedy piece where the punchlines happen to be true. The reader "
        "should be too busy laughing to realize they're being persuaded.\n\n"
        "Rewrite the draft article completely. Kill its structure — no section breaks, no "
        "\"firstly/secondly/in conclusion\" scaffolding, no polite transitions. This is a from-scratch "
        "rewrite using the draft as raw material.\n\n"
        "CRITICAL — LENGTH: The draft is too long. Your output should be SIGNIFICANTLY shorter — "
        "roughly HALF the original word count or less. Be ruthless:\n"
        "- Make each point ONCE. If you've already said it, don't rephrase it. Move on.\n"
        "- Not every fact survives. Keep the wildest, funniest, most convincing ones. Kill anything "
        "redundant, minor, or boring.\n"
        "- If the draft spends three paragraphs on the same idea, pick the best angle and kill the "
        "other two. One hilarious paragraph beats three informative ones.\n\n"
        "THE VOICE:\n"
        "- Funny first. Your PRIMARY job is to be entertaining. Every paragraph should either make "
        "them laugh, make them go \"wait WHAT,\" or ideally both. The facts are ammunition for "
        "jokes — not the other way around.\n"
        "- RIDICULOUS. Old-school Cracked didn't do subtle. Take ideas to their most absurd "
        "logical conclusion. Compare things that shouldn't be compared. Use hyperbole that's "
        "so specific it becomes funny again. If you're not at least a little unhinged, you're "
        "not trying hard enough.\n"
        "- Relentless. Don't give the reader a chance to get bored. Every paragraph sets up the "
        "next one. By the time they finish one outrageous claim, you're already hitting them "
        "with the evidence that proves it, which sets up an even MORE outrageous implication. "
        "Shake them down with facts and jokes until they have no choice but to agree with you.\n"
        "- Cynical, irreverent, but never mean-spirited. You're on the reader's side. You're both "
        "looking at how absurd this all is together. The tone is \"can you BELIEVE this?\" not "
        "\"you're an idiot for not knowing.\"\n"
        "- Conversational. Read like someone talking too fast because they're genuinely excited "
        "about how insane this all is. Short paragraphs. Varied rhythm. If a sentence sounds like "
        "it came from a textbook, a press release, or a LinkedIn post, kill it.\n\n"
        "WHAT TO AVOID:\n"
        "- Don't preserve the original structure. Synthesize. Blend. Make it one piece.\n"
        "- Don't overuse any single joke structure. If you catch yourself doing \"It's not X, "
        "it's Y\" twice, the second one dies.\n"
        "- Don't be a template. If the article reads like you filled in blanks on a Cracked Mad "
        "Lib, scrap it and write like a human.\n"
        "- Don't play it safe. The draft is polite. You are not. Be funnier, louder, and more "
        "ridiculous than the draft dares to be.\n\n"
        "FORMAT:\n"
        "Output in Markdown. ## for section heads, **bold** for punch and emphasis, *italics* "
        "for asides, numbered/bulleted lists where they serve the flow, --- for major breaks "
        "if needed. Clean and render-ready.\n\n"
        "Output ONLY the article. No preamble, no sign-off, no meta. Just the piece."
    ),
}

STEP4_MODELS = [
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5 (Fastest)"},
    {"id": "claude-sonnet-5", "name": "Claude Sonnet 5 (Balanced)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-8", "name": "Claude Opus 4.8 (Most Capable)"},
    {"id": "claude-fable-5", "name": "Claude Fable 5 (Best)"},
]


def get_step4_params() -> dict:
    """Load Step 4 params from disk or return defaults."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step4_params.json"
        if params_file.exists():
            with open(params_file) as f:
                return json.load(f)
    return dict(STEP4_DEFAULT_PARAMS)


def save_step4_params(params: dict) -> None:
    """Persist Step 4 params to disk."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step4_params.json"
        with open(params_file, "w") as f:
            json.dump(params, f, indent=2)


def get_step4_data() -> dict:
    """Load Step 4 data from disk."""
    global _current_project_path
    if _current_project_path:
        step_file = _current_project_path / "step4.json"
        if step_file.exists():
            with open(step_file) as f:
                return json.load(f)
    return {
        "styled_article": "", "status": "idle", "last_run": None, "error": None,
    }


def save_step4_data(data: dict) -> bool:
    """Persist Step 4 data to disk. Returns False if no project is loaded."""
    global _current_project_path
    if not _current_project_path:
        return False
    step_file = _current_project_path / "step4.json"
    with open(step_file, "w") as f:
        json.dump(data, f, indent=2)
    return True


class Step4DataUpdate(BaseModel):
    styled_article: str = ""
    status: str = "idle"
    error: str | None = None


class Step4ParamsUpdate(BaseModel):
    model: str = "claude-haiku-4-5"
    temperature: float = 1.0
    max_tokens: int = 8192
    thinking_budget: int = 1600
    effort: str = "high"
    system_prompt: str = ""


def _build_step4_user_message(step3_draft_article: str) -> str:
    """Build the user message for Step 4 from a Step 3 draft article."""
    return (
        "DRAFT TO REWRITE:\n\n"
        f"{step3_draft_article}\n\n"
        "---\n\n"
        "Rewrite this from scratch. The draft above is TOO LONG and TOO POLITE — your output "
        "should be roughly HALF its length and TEN TIMES funnier. Kill the structure. Kill the "
        "transitions. Make it one flowing, ridiculous, laugh-out-loud piece in the voice "
        "described above.\n\n"
        "Be ruthless: keep only the strongest facts, make each point once, and make sure every "
        "paragraph either gets a laugh or sets one up. The draft is raw material. You're here "
        "to turn it into entertainment that happens to be true.\n\n"
        "Output the article in Markdown. Nothing else."
    )


@app.get("/api/step/4/data")
async def get_step4():
    """Get Step 4 stored data."""
    return get_step4_data()


@app.put("/api/step/4/data")
async def update_step4(body: Step4DataUpdate):
    """Update Step 4 data (manual edit)."""
    data = body.model_dump()
    if not save_step4_data(data):
        return {"ok": False, "error": "No project loaded. Go to Project and create or load one first."}
    log_entry("INFO", 4, f"Step 4 data updated. Article length: {len(data.get('styled_article', ''))}")
    return {"ok": True}


@app.get("/api/step/4/params")
async def get_step4_params_route():
    """Get Step 4 parameters."""
    params = get_step4_params()
    params["available_models"] = STEP4_MODELS
    return params


@app.put("/api/step/4/params")
async def update_step4_params(body: Step4ParamsUpdate):
    """Update Step 4 parameters."""
    params = body.model_dump()
    save_step4_params(params)
    log_entry("INFO", 4, f"Step 4 params updated. Model: {params['model']}, Temp: {params['temperature']}, Thinking budget: {params.get('thinking_budget', 0)}")
    return {"ok": True}


@app.get("/api/step/4/user-message")
async def get_step4_user_message():
    """Get the user message preview for Step 4 — what will be sent to the model."""
    step3_data = get_step3_data()
    draft_article = step3_data.get("draft_article", "")
    if not draft_article.strip():
        return {"user_message": "", "warning": "Step 3 has no article yet. Run Step 3 first."}
    user_message = _build_step4_user_message(draft_article)
    return {"user_message": user_message}


@app.post("/api/step/4/run")
async def run_step4():
    """Execute Step 4: rewrite the Step 3 article in Cracked.com style."""
    import httpx
    import asyncio

    step3_data = get_step3_data()
    step4_data = get_step4_data()
    params = get_step4_params()
    settings = load_settings()

    if not _current_project_path:
        return {"ok": False, "error": "No project loaded."}

    # Validate Step 3 is done
    draft_article = step3_data.get("draft_article", "")
    if step3_data.get("status") != "completed" or not draft_article.strip():
        return {"ok": False, "error": "Step 3 is not complete. Run Step 3 (Article Synthesis) first."}

    api_key = settings.get("anthropic_key", "").strip()
    if not api_key:
        step4_data["status"] = "failed"
        step4_data["error"] = "No Anthropic API key configured. Go to Settings to add one."
        save_step4_data(step4_data)
        return {"ok": False, "error": step4_data["error"]}

    step4_data["status"] = "running"
    step4_data["error"] = None
    save_step4_data(step4_data)

    model = params.get("model", "claude-haiku-4-5")
    temperature = params.get("temperature", 1.0)
    max_tokens = params.get("max_tokens", 8192)
    thinking_budget = params.get("thinking_budget", 1600)
    effort = params.get("effort", "high")
    system_prompt = params.get("system_prompt", STEP4_DEFAULT_PARAMS["system_prompt"])

    user_message = _build_step4_user_message(draft_article)

    log_entry("INFO", 4, (
        f"Rewriting article in Cracked.com style. Step 3 article: {len(draft_article)} chars.\n"
        f"--- SYSTEM ---\n{system_prompt[:300]}...\n"
        f"--- USER ---\n{user_message[:500]}..."
    ))

    # Build model-appropriate thinking config
    is_haiku = model.startswith("claude-haiku")
    if is_haiku:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 1.0,
            "system": system_prompt,
            "thinking": {"type": "enabled", "budget_tokens": thinking_budget},
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 4, f"Style rewrite with {model} (thinking budget: {thinking_budget})")
    else:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 4, f"Style rewrite with {model} (adaptive thinking, effort: {effort})")

    # Retry loop — 2 attempts
    success = False
    for attempt in range(1, 3):
        try:
            async with httpx.AsyncClient(timeout=180) as client:
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
                content_blocks = result.get("content", [])
                response_text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        response_text += block.get("text", "")

                if response_text.strip():
                    step4_data["styled_article"] = response_text.strip()
                    step4_data["status"] = "completed"
                    step4_data["last_run"] = dt.datetime.now().isoformat()
                    step4_data["error"] = None
                    save_step4_data(step4_data)
                    usage = result.get("usage", {})
                    log_entry("INFO", 4, (
                        f"Step 4 completed — article {len(response_text)} chars, "
                        f"input_tokens={usage.get('input_tokens', 'N/A')}, "
                        f"output_tokens={usage.get('output_tokens', 'N/A')}"
                    ))
                    return {"ok": True, "styled_article": step4_data["styled_article"]}
                else:
                    log_entry("ERROR", 4, f"Step 4 — empty response (attempt {attempt})")
                    step4_data["status"] = "failed"
                    step4_data["error"] = f"Model returned empty response (attempt {attempt})"
            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    err = err_data.get("error", {})
                    error_detail = err.get("message", resp.text[:500])
                except Exception:
                    error_detail = resp.text[:500]

                log_entry("ERROR", 4, f"Anthropic API error ({resp.status_code}) attempt {attempt}: {error_detail}")
                step4_data["status"] = "failed"
                step4_data["error"] = f"API error ({resp.status_code}) attempt {attempt}: {error_detail}"

        except httpx.TimeoutException:
            log_entry("ERROR", 4, f"Anthropic timeout on attempt {attempt}")
            step4_data["status"] = "failed"
            step4_data["error"] = f"Request timed out after 180s (attempt {attempt})"
        except Exception as e:
            log_entry("ERROR", 4, f"Anthropic unexpected error attempt {attempt}: {str(e)}")
            step4_data["status"] = "failed"
            step4_data["error"] = f"Unexpected error (attempt {attempt}): {str(e)}"

        # Retry with delay if not last attempt
        if attempt == 1:
            log_entry("WARN", 4, "Step 4 failed attempt 1. Retrying in 3s...")
            await asyncio.sleep(3)

    save_step4_data(step4_data)
    return {"ok": False, "error": step4_data["error"]}


# ============================================================
# Step 5 — Image Planning
# ============================================================

STEP5_DEFAULT_PARAMS = {
    "model": "claude-haiku-4-5",
    "temperature": 1.0,
    "max_tokens": 8192,
    "thinking_budget": 1600,
    "effort": "high",
    "system_prompt": (
        "You are an image planner for a comedy article. Your job: read the article, find the "
        "best spots for images, and plan them out.\n\n"
        "THE ARTICLE:\n"
        "The user will give you a finished article written in the voice of 2010s Cracked.com — "
        "funny, cynical, irreverent, ridiculous. Your images need to MATCH that energy. No "
        "stock-photo corporate nonsense. No generic \"person looking at computer\" garbage. "
        "Every image should feel like it belongs in a Cracked article.\n\n"
        "WHAT TO DO:\n"
        "1. Read the article carefully. Find exactly the specified number of natural break points where an image would "
        "land with maximum impact — punchlines, absurd comparisons, \"wait WHAT\" moments, "
        "or places where a visual would make the joke hit twice as hard.\n"
        "2. For each spot, identify the ANCHOR TEXT — the EXACT sentence or phrase from the "
        "article (copied verbatim, character-for-character) that marks where the image goes. "
        "The image and caption will be inserted AFTER this text. The anchor MUST be unique "
        "enough to match only one place in the article.\n"
        "3. Write a CAPTION in the article's voice. The caption should be "
        "funny on its own — it's part of the entertainment, not a dry label. Think of it as "
        "a mini-joke that adds another layer to the article.\n"
        "4. Write an IMAGE PROMPT that's detailed and specific enough for an AI image generator "
        "(like DALL-E or Midjourney) to produce something great. Include:\n"
        "   - Subject and composition (what's in the frame, how it's arranged)\n"
        "   - Style/aesthetic (photorealistic, illustration, retro, cinematic, etc. — pick "
        "what serves the joke best)\n"
        "   - Mood and tone (absurd, dramatic, deadpan, chaotic — match the caption)\n"
        "   - Color palette if relevant\n"
        "   - Any specific details that make the image work for the joke\n"
        "5. Include a brief RATIONALE — why THIS image at THIS spot. One sentence is fine.\n\n"
        "IMAGE PLACEMENT STRATEGY:\n"
        "- Don't cluster images too close together. Spread them across the article.\n"
        "- The first image should hook readers early (within the first few paragraphs).\n"
        "- Save at least one banger for the closing section — leave them laughing.\n"
        "- If the article makes an insane comparison or absurd claim, VISUALIZE IT. Those "
        "are your best image opportunities.\n"
        "- Don't illustrate the obvious. If the text already paints a perfect mental picture, "
        "move on. Find the spots where a visual ADDS something.\n\n"
        "CRITICAL — ANCHOR TEXT RULES:\n"
        "- Copy the anchor sentence from the article EXACTLY — same punctuation, same "
        "capitalization, same spacing. It must be findable with Ctrl+F.\n"
        "- Pick a phrase long enough to be unique (at least 60 characters if possible). "
        "If the article says \"and that's why dolphins are actually jerks,\" your anchor "
        "is \"and that's why dolphins are actually jerks\" — verbatim.\n"
        "- Don't paraphrase. Don't summarize. Don't describe the section. Copy the text.\n"
        "- If you can't find a unique anchor, pick the longest distinctive substring "
        "that only appears once in the article.\n\n"
        "OUTPUT FORMAT:\n"
        "Output a single JSON object with an \"image_cards\" array. Each entry has:\n"
        "- \"id\": 1-based index\n"
        "- \"anchor_text\": EXACT verbatim sentence/phrase from the article — image goes AFTER this\n"
        "- \"caption\": The image caption (funny, in the article's voice)\n"
        "- \"image_prompt\": Detailed AI image generation prompt\n"
        "- \"rationale\": Why this image here (one sentence)\n\n"
        "Output ONLY valid JSON. No preamble, no markdown fences, no sign-off. Just the JSON object."
    ),
}

STEP5_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "image_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "1-based index of this image card"},
                    "anchor_text": {"type": "string", "description": "EXACT sentence or phrase from the article to anchor placement — copy it verbatim so it can be found with a text search. The image and caption will be inserted AFTER this text."},
                    "caption": {"type": "string", "description": "Witty, Cracked-style image caption — the final text displayed under the image"},
                    "image_prompt": {"type": "string", "description": "Detailed AI image generation prompt with style, composition, mood"},
                    "rationale": {"type": "string", "description": "Why this image belongs at this spot"},
                },
                "required": ["id", "anchor_text", "caption", "image_prompt"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["image_cards"],
    "additionalProperties": False,
}

STEP5_MODELS = [
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5 (Fastest)"},
    {"id": "claude-sonnet-5", "name": "Claude Sonnet 5 (Balanced)"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "claude-opus-4-8", "name": "Claude Opus 4.8 (Most Capable)"},
    {"id": "claude-fable-5", "name": "Claude Fable 5 (Best)"},
]


def get_step5_params() -> dict:
    """Load Step 5 params from disk or return defaults."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step5_params.json"
        if params_file.exists():
            with open(params_file) as f:
                return json.load(f)
    return dict(STEP5_DEFAULT_PARAMS)


def save_step5_params(params: dict) -> None:
    """Persist Step 5 params to disk."""
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step5_params.json"
        with open(params_file, "w") as f:
            json.dump(params, f, indent=2)


def get_step5_data() -> dict:
    """Load Step 5 data from disk."""
    global _current_project_path
    if _current_project_path:
        step_file = _current_project_path / "step5.json"
        if step_file.exists():
            with open(step_file) as f:
                return json.load(f)
    return {
        "image_count": 3, "image_cards": [], "final_article": "", "status": "idle", "last_run": None, "error": None,
    }


def save_step5_data(data: dict) -> bool:
    """Persist Step 5 data to disk. Returns False if no project is loaded."""
    global _current_project_path
    if not _current_project_path:
        return False
    step_file = _current_project_path / "step5.json"
    with open(step_file, "w") as f:
        json.dump(data, f, indent=2)
    return True


class Step5DataUpdate(BaseModel):
    image_count: int = 3
    image_cards: list = []
    status: str = "idle"
    error: str | None = None


class Step5ParamsUpdate(BaseModel):
    model: str = "claude-haiku-4-5"
    temperature: float = 1.0
    max_tokens: int = 8192
    thinking_budget: int = 1600
    effort: str = "high"
    system_prompt: str = ""


def _build_step5_user_message(step4_styled_article: str, image_count: int = 3) -> str:
    """Build the user message for Step 5 from a Step 4 styled article."""
    return (
        "STYLED ARTICLE:\n\n"
        f"{step4_styled_article}\n\n"
        "---\n\n"
        f"Plan exactly {image_count} images for this article.\n\n"
        "For each image spot:\n"
        "1. Find a natural break point. Copy the EXACT sentence or phrase to use as anchor_text "
        "(verbatim from the article — same punctuation, capitalization, spacing — so it can be "
        "found with a text search). Pick a phrase at least 60 chars long if possible. The image "
        "and caption will be inserted AFTER this anchor.\n"
        "2. Write a caption in the same voice as the article — funny, punchy, irreverent.\n"
        "3. Write a detailed AI image generation prompt — include style, composition, mood, "
        "subject, and any specific visual details that sell the joke.\n\n"
        "CRITICAL — ANCHOR TEXT RULES:\n"
        "- Copy the anchor sentence EXACTLY from the article — every character, every space, "
        "every punctuation mark. Use Ctrl+C on the article text above, then Ctrl+V into your "
        "anchor_text field. Do NOT retype it.\n"
        "- PRESERVE ALL MARKDOWN FORMATTING. If the article says \"*illusion*\" your anchor "
        "must say \"*illusion*\" — not \"illusion\". If it says \"**absolutely**\" your anchor "
        "must say \"**absolutely**\". Asterisks, bold, italics — keep everything.\n"
        "- Do not paraphrase. Do not summarize. Do not describe the section. Copy the text "
        "character-for-character from the article above. It must be findable with Ctrl+F.\n"
        "- If the article says \"dolphins are actually complete jerks about it,\" your "
        "anchor_text is exactly \"dolphins are actually complete jerks about it\" — not "
        "\"the dolphin paragraph\" or \"the part about dolphin behavior.\"\n\n"
        "Spread images across the article. First image should hook early, save at least one "
        "banger for the closing section. Don't cluster them.\n\n"
        f"Output ONLY valid JSON with an \"image_cards\" array containing exactly {image_count} entries. "
        f"No markdown fences, no preamble, no sign-off. Just the JSON object."
    )


@app.get("/api/step/5/data")
async def get_step5():
    """Get Step 5 stored data."""
    return get_step5_data()


@app.put("/api/step/5/data")
async def update_step5(body: Step5DataUpdate):
    """Update Step 5 data (manual edit)."""
    data = body.model_dump()
    if not save_step5_data(data):
        return {"ok": False, "error": "No project loaded. Go to Project and create or load one first."}
    log_entry("INFO", 5, f"Step 5 data updated. Image cards: {len(data.get('image_cards', []))}")
    return {"ok": True}


@app.get("/api/step/5/params")
async def get_step5_params_route():
    """Get Step 5 parameters."""
    params = get_step5_params()
    params["available_models"] = STEP5_MODELS
    return params


@app.put("/api/step/5/params")
async def update_step5_params(body: Step5ParamsUpdate):
    """Update Step 5 parameters."""
    params = body.model_dump()
    save_step5_params(params)
    log_entry("INFO", 5, f"Step 5 params updated. Model: {params['model']}, Temp: {params['temperature']}, Thinking budget: {params.get('thinking_budget', 0)}")
    return {"ok": True}


@app.get("/api/step/5/user-message")
async def get_step5_user_message():
    """Get the user message preview for Step 5 — what will be sent to the model."""
    step4_data = get_step4_data()
    step5_data = get_step5_data()
    styled_article = step4_data.get("styled_article", "")
    image_count = step5_data.get("image_count", 3)
    if not styled_article.strip():
        return {"user_message": "", "warning": "Step 4 has no article yet. Run Step 4 (Style Rewrite) first.", "image_count": image_count}
    user_message = _build_step5_user_message(styled_article, image_count)
    return {"user_message": user_message, "image_count": image_count}


@app.post("/api/step/5/run")
async def run_step5():
    """Execute Step 5: plan image placements for the styled article."""
    import httpx
    import asyncio

    step4_data = get_step4_data()
    step5_data = get_step5_data()
    params = get_step5_params()
    settings = load_settings()

    if not _current_project_path:
        return {"ok": False, "error": "No project loaded."}

    # Validate Step 4 is done
    styled_article = step4_data.get("styled_article", "")
    if step4_data.get("status") != "completed" or not styled_article.strip():
        return {"ok": False, "error": "Step 4 is not complete. Run Step 4 (Style Rewrite) first."}

    # Validate image count
    image_count = step5_data.get("image_count", 3)
    if image_count < 1 or image_count > 20:
        return {"ok": False, "error": f"Image count must be between 1 and 20 (got {image_count})."}

    api_key = settings.get("anthropic_key", "").strip()
    if not api_key:
        step5_data["status"] = "failed"
        step5_data["error"] = "No Anthropic API key configured. Go to Settings to add one."
        save_step5_data(step5_data)
        return {"ok": False, "error": step5_data["error"]}

    step5_data["status"] = "running"
    step5_data["error"] = None
    save_step5_data(step5_data)

    model = params.get("model", "claude-haiku-4-5")
    temperature = params.get("temperature", 1.0)
    max_tokens = params.get("max_tokens", 8192)
    thinking_budget = params.get("thinking_budget", 1600)
    effort = params.get("effort", "high")
    system_prompt = params.get("system_prompt", STEP5_DEFAULT_PARAMS["system_prompt"])

    user_message = _build_step5_user_message(styled_article, image_count)

    log_entry("INFO", 5, (
        f"Planning {image_count} images for styled article. Article: {len(styled_article)} chars.\n"
        f"--- SYSTEM ---\n{system_prompt[:300]}...\n"
        f"--- USER ---\n{user_message[:500]}..."
    ))

    # Build model-appropriate thinking config with structured JSON output
    is_haiku = model.startswith("claude-haiku")
    if is_haiku:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 1.0,
            "system": system_prompt,
            "thinking": {"type": "enabled", "budget_tokens": thinking_budget},
            "output_config": {
                "format": {"type": "json_schema", "schema": STEP5_OUTPUT_SCHEMA},
            },
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 5, f"Image planning with {model} (thinking budget: {thinking_budget})")
    else:
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "thinking": {"type": "adaptive"},
            "output_config": {
                "format": {"type": "json_schema", "schema": STEP5_OUTPUT_SCHEMA},
                "effort": effort,
            },
            "messages": [{"role": "user", "content": user_message}],
        }
        log_entry("INFO", 5, f"Image planning with {model} (adaptive thinking, effort: {effort})")

    # Retry loop — 2 attempts
    for attempt in range(1, 3):
        try:
            async with httpx.AsyncClient(timeout=180) as client:
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
                content_blocks = result.get("content", [])
                response_text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        response_text += block.get("text", "")

                if response_text.strip():
                    # Parse JSON response
                    try:
                        parsed = json.loads(response_text)
                        raw_cards = parsed.get("image_cards", [])

                        if not isinstance(raw_cards, list):
                            raise ValueError(f"Expected 'image_cards' array, got {type(raw_cards).__name__}")

                        # Add status tracking fields to each card for Step 6
                        image_cards = []
                        for i, card in enumerate(raw_cards):
                            card["id"] = card.get("id", i + 1)
                            card["status"] = "completed"
                            card["error"] = None
                            image_cards.append(card)

                        step5_data["image_cards"] = image_cards
                        step5_data["status"] = "completed"
                        step5_data["last_run"] = dt.datetime.now().isoformat()
                        step5_data["error"] = None
                        save_step5_data(step5_data)
                        usage = result.get("usage", {})
                        log_entry("INFO", 5, (
                            f"Step 5 completed — {len(image_cards)} image cards planned, "
                            f"input_tokens={usage.get('input_tokens', 'N/A')}, "
                            f"output_tokens={usage.get('output_tokens', 'N/A')}"
                        ))
                        return {"ok": True, "image_cards": image_cards}

                    except (json.JSONDecodeError, ValueError) as parse_err:
                        log_entry("ERROR", 5, f"Step 5 — failed to parse JSON response (attempt {attempt}): {parse_err}")
                        step5_data["status"] = "failed"
                        step5_data["error"] = f"Model returned invalid JSON (attempt {attempt}): {str(parse_err)}. Raw: {response_text[:500]}"
                else:
                    log_entry("ERROR", 5, f"Step 5 — empty response (attempt {attempt})")
                    step5_data["status"] = "failed"
                    step5_data["error"] = f"Model returned empty response (attempt {attempt})"
            else:
                error_detail = "Unknown error"
                try:
                    err_data = resp.json()
                    err = err_data.get("error", {})
                    error_detail = err.get("message", resp.text[:500])
                except Exception:
                    error_detail = resp.text[:500]

                log_entry("ERROR", 5, f"Anthropic API error ({resp.status_code}) attempt {attempt}: {error_detail}")
                step5_data["status"] = "failed"
                step5_data["error"] = f"API error ({resp.status_code}) attempt {attempt}: {error_detail}"

        except httpx.TimeoutException:
            log_entry("ERROR", 5, f"Anthropic timeout on attempt {attempt}")
            step5_data["status"] = "failed"
            step5_data["error"] = f"Request timed out after 180s (attempt {attempt})"
        except Exception as e:
            log_entry("ERROR", 5, f"Anthropic unexpected error attempt {attempt}: {str(e)}")
            step5_data["status"] = "failed"
            step5_data["error"] = f"Unexpected error (attempt {attempt}): {str(e)}"

        # Retry with delay if not last attempt
        if attempt == 1:
            log_entry("WARN", 5, "Step 5 failed attempt 1. Retrying in 3s...")
            await asyncio.sleep(3)

    save_step5_data(step5_data)
    return {"ok": False, "error": step5_data["error"]}


# ============================================================
# Step 6 — Image Generation (OpenAI)
# ============================================================

STEP6_DEFAULT_PARAMS = {
    "model": "gpt-image-1-mini",
    "size": "1024x1024",
    "quality": "high",
}

STEP6_MODELS = [
    {"id": "gpt-image-1-mini", "name": "GPT Image 1 Mini (Cheapest)"},
    {"id": "gpt-image-1", "name": "GPT Image 1"},
    {"id": "gpt-image-1.5", "name": "GPT Image 1.5"},
    {"id": "gpt-image-2", "name": "GPT Image 2 (Best)"},
]

STEP6_SIZES = [
    {"id": "1024x1024", "name": "1024×1024 (Square)"},
    {"id": "1536x1024", "name": "1536×1024 (Landscape)"},
    {"id": "1024x1536", "name": "1024×1536 (Portrait)"},
]

STEP6_QUALITIES = [
    {"id": "low", "name": "Low — fastest, cheapest"},
    {"id": "medium", "name": "Medium — balanced"},
    {"id": "high", "name": "High — best quality"},
]


def get_step6_params() -> dict:
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step6_params.json"
        if params_file.exists():
            with open(params_file) as f:
                return json.load(f)
    return dict(STEP6_DEFAULT_PARAMS)


def save_step6_params(params: dict) -> None:
    global _current_project_path
    if _current_project_path:
        params_file = _current_project_path / "step6_params.json"
        with open(params_file, "w") as f:
            json.dump(params, f, indent=2)


def get_step6_data() -> dict:
    global _current_project_path
    if _current_project_path:
        step_file = _current_project_path / "step6.json"
        if step_file.exists():
            with open(step_file) as f:
                return json.load(f)
    return {"image_cards": [], "status": "idle", "last_run": None, "error": None}


def save_step6_data(data: dict) -> bool:
    global _current_project_path
    if not _current_project_path:
        return False
    step_file = _current_project_path / "step6.json"
    with open(step_file, "w") as f:
        json.dump(data, f, indent=2)
    return True


def _init_step6_cards_from_step5(step6_data: dict) -> None:
    """Populate step6 image_cards from step5 if step6 is empty."""
    if step6_data.get("image_cards"):
        return  # already has cards
    step5_data = get_step5_data()
    step5_cards = step5_data.get("image_cards", [])
    if not step5_cards:
        return
    image_cards = []
    for card in step5_cards:
        image_cards.append({
            "id": card.get("id", 0),
            "anchor_text": card.get("anchor_text", ""),
            "caption": card.get("caption", ""),
            "image_prompt": card.get("image_prompt", ""),
            "rationale": card.get("rationale", ""),
            "image_b64": None,
            "status": "idle",
            "error": None,
            "last_run": None,
        })
    step6_data["image_cards"] = image_cards


def _find_step6_card_index(cards: list, card_id: int) -> int | None:
    for i, c in enumerate(cards):
        if c.get("id") == card_id:
            return i
    return None


def _update_step6_aggregate_status(data: dict) -> None:
    cards = data.get("image_cards", [])
    if not cards:
        data["status"] = "idle"
        return
    statuses = {c.get("status") for c in cards}
    if "running" in statuses:
        data["status"] = "running"
    elif "failed" in statuses and "completed" not in statuses and "idle" not in statuses:
        data["status"] = "failed"
    elif all(s == "completed" for s in statuses):
        data["status"] = "completed"
    elif any(s == "completed" for s in statuses):
        data["status"] = "partial"
    else:
        data["status"] = "idle"


class Step6DataUpdate(BaseModel):
    image_cards: list = []
    status: str = "idle"
    error: str | None = None


class Step6ParamsUpdate(BaseModel):
    model: str = "gpt-image-1-mini"
    size: str = "1024x1024"
    quality: str = "high"


async def _generate_step6_image(card: dict, params: dict, api_key: str) -> None:
    """Generate a single image via OpenAI and update the card."""
    import httpx

    prompt = card.get("image_prompt", "")
    if not prompt.strip():
        card["status"] = "failed"
        card["error"] = "No image prompt — card may be missing data from Step 5."
        return

    request_body = {
        "model": params.get("model", "gpt-image-1-mini"),
        "prompt": prompt,
        "n": 1,
        "size": params.get("size", "1024x1024"),
        "quality": params.get("quality", "low"),
    }

    log_entry("INFO", 6, f"Generating image for card #{card.get('id')} — model: {request_body['model']}, size: {request_body['size']}, quality: {request_body['quality']}")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )

        if resp.status_code == 200:
            result = resp.json()
            data_list = result.get("data", [])
            if data_list and data_list[0].get("b64_json"):
                card["image_b64"] = data_list[0]["b64_json"]
                card["status"] = "completed"
                card["last_run"] = dt.datetime.now().isoformat()
                card["error"] = None
                log_entry("INFO", 6, f"Card #{card.get('id')} image generated successfully.")
            else:
                card["status"] = "failed"
                card["error"] = "OpenAI returned no image data."
                log_entry("ERROR", 6, f"Card #{card.get('id')}: no image data in response.")
        else:
            error_detail = "Unknown error"
            try:
                err_data = resp.json()
                err = err_data.get("error", {})
                error_detail = err.get("message", resp.text[:500])
            except Exception:
                error_detail = resp.text[:500]
            card["status"] = "failed"
            card["error"] = f"OpenAI error ({resp.status_code}): {error_detail}"
            log_entry("ERROR", 6, f"Card #{card.get('id')} OpenAI error ({resp.status_code}): {error_detail}")

    except httpx.TimeoutException:
        card["status"] = "failed"
        card["error"] = "Request timed out after 120s"
        log_entry("ERROR", 6, f"Card #{card.get('id')} timeout.")
    except Exception as e:
        card["status"] = "failed"
        card["error"] = f"Unexpected error: {str(e)}"
        log_entry("ERROR", 6, f"Card #{card.get('id')} unexpected error: {str(e)}")


@app.get("/api/step/6/data")
async def get_step6():
    data = get_step6_data()
    _init_step6_cards_from_step5(data)
    return data


@app.put("/api/step/6/data")
async def update_step6(body: Step6DataUpdate):
    data = body.model_dump()
    if not save_step6_data(data):
        return {"ok": False, "error": "No project loaded."}
    log_entry("INFO", 6, f"Step 6 data updated. Cards: {len(data.get('image_cards', []))}")
    return {"ok": True}


@app.get("/api/step/6/params")
async def get_step6_params_route():
    params = get_step6_params()
    params["available_models"] = STEP6_MODELS
    params["available_sizes"] = STEP6_SIZES
    params["available_qualities"] = STEP6_QUALITIES
    return params


@app.put("/api/step/6/params")
async def update_step6_params(body: Step6ParamsUpdate):
    params = body.model_dump()
    save_step6_params(params)
    log_entry("INFO", 6, f"Step 6 params updated. Model: {params['model']}, Size: {params['size']}, Quality: {params['quality']}")
    return {"ok": True}


@app.post("/api/step/6/run")
async def run_step6():
    """Generate images for ALL cards sequentially."""
    step6_data = get_step6_data()
    params = get_step6_params()
    settings = load_settings()

    if not _current_project_path:
        return {"ok": False, "error": "No project loaded."}

    _init_step6_cards_from_step5(step6_data)
    cards = step6_data.get("image_cards", [])

    if not cards:
        return {"ok": False, "error": "No image cards. Run Step 5 (Image Planning) first."}

    api_key = settings.get("openai_key", "").strip()
    if not api_key:
        step6_data["status"] = "failed"
        step6_data["error"] = "No OpenAI API key configured. Go to Settings to add one."
        save_step6_data(step6_data)
        return {"ok": False, "error": step6_data["error"]}

    step6_data["status"] = "running"
    step6_data["error"] = None
    save_step6_data(step6_data)

    log_entry("INFO", 6, f"Starting image generation for {len(cards)} cards")

    for card in cards:
        if card.get("status") == "completed":
            continue  # skip already-generated cards
        card["status"] = "running"
        card["error"] = None
        save_step6_data(step6_data)
        await _generate_step6_image(card, params, api_key)
        save_step6_data(step6_data)

    _update_step6_aggregate_status(step6_data)
    save_step6_data(step6_data)
    log_entry("INFO", 6, f"Step 6 image generation complete. Status: {step6_data['status']}")
    return {"ok": True, "image_cards": step6_data["image_cards"]}


@app.post("/api/step/6/run-card/{card_id}")
async def run_step6_card(card_id: int):
    """Generate image for a SINGLE card."""
    step6_data = get_step6_data()
    params = get_step6_params()
    settings = load_settings()

    if not _current_project_path:
        return {"ok": False, "error": "No project loaded."}

    _init_step6_cards_from_step5(step6_data)
    cards = step6_data.get("image_cards", [])

    idx = _find_step6_card_index(cards, card_id)
    if idx is None:
        return {"ok": False, "error": f"Card #{card_id} not found."}

    api_key = settings.get("openai_key", "").strip()
    if not api_key:
        return {"ok": False, "error": "No OpenAI API key configured."}

    card = cards[idx]
    card["status"] = "running"
    card["error"] = None
    save_step6_data(step6_data)

    await _generate_step6_image(card, params, api_key)

    _update_step6_aggregate_status(step6_data)
    save_step6_data(step6_data)
    return {"ok": True, "card": card}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
