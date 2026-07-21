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

# --- FastAPI app ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: log that the server started."""
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
    if body.anthropic_key and "*" * (len(body.anthropic_key) - 8) not in body.anthropic_key:
        settings["anthropic_key"] = body.anthropic_key.strip()
    if body.gemini_key and "*" * (len(body.gemini_key) - 8) not in body.gemini_key:
        settings["gemini_key"] = body.gemini_key.strip()
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
        "topic": "", "subtopic_count": 5, "subtopics": [],
        "status": "idle", "last_run": None, "error": None,
    }
    step2_default = {
        "research_results": [], "status": "idle", "last_run": None, "error": None,
    }
    step3_default = {
        "draft_article": "", "status": "idle", "last_run": None, "error": None,
    }
    step4_default = {
        "styled_article": "", "status": "idle", "last_run": None, "error": None,
    }
    step5_default = {
        "images": [], "final_article": "", "status": "idle", "last_run": None, "error": None,
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
    for i in range(1, 6):
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
        "steps": {str(i): {"status": proj["steps"][i].get("status", "idle")} for i in range(1, 6)},
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
        "steps": {str(i): {"status": _current_project["steps"][i].get("status", "idle")} for i in range(1, 6)},
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
        "steps": {str(i): {"status": _current_project["steps"][i].get("status", "idle")} for i in range(1, 6)},
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
    "temperature": 0.5,
    "max_tokens": 4096,
    "system_prompt": (
        "You are designing the outline for a persuasive, well-researched article. Your outline will be handed off to a research agent "
        "and then to a writer — your job is to give them the best possible blueprint.\n\n"
        "Given a brief describing what the article should cover, produce exactly the requested number of subtopics. "
        "Each subtopic will become a full section of the finished article. Think of each one as a chapter in a book: "
        "it needs a reason to exist, a clear argument, and enough depth to justify its word count.\n\n"
        "CORE PRINCIPLE: Every section must make an argument and back it up with evidence. The article is persuasive, "
        "not a neutral summary. Each subtopic should advance a claim — something debatable, interesting, worth convincing "
        "the reader of. The research agent's job is to find sources that support that claim.\n\n"
        "Be pragmatic about evidence. Sometimes the best support is academic research and data. Sometimes it's investigative "
        "journalism, historical precedent, expert testimony, legal analysis, or first-person accounts. Sometimes it's a mix. "
        "The type of evidence should fit the argument — don't force statistics where a compelling narrative case is stronger, "
        "and don't rely on anecdotes where hard data would be more convincing.\n\n"
        "Your output must be valid JSON matching this schema:\n"
        "{\n"
        '  "subtopics": [\n'
        "    {\n"
        '      "id": 1,\n'
        '      "title": "A sharp, clickable section headline that makes someone want to read it",\n'
        '      "angle": "The argument this section makes — what claim are we advancing? what should the reader be convinced of by the end of this section?",\n'
        '      "research_info": "The kind of evidence that would best support this argument: specific data points, historical examples, expert opinions, case studies, legal rulings, personal accounts, institutional patterns — whatever form of proof makes the argument land hardest",\n'
        '      "search_query": "THE MOST CRITICAL FIELD. This query will be used with Google Search to research this subtopic. Craft a creative, effective search that would surface the kind of evidence needed to prove the angle. Start from the observable reality described in the angle — what would someone actually search to understand WHY this happens? Make it a search that makes sense, not a keyword dump. Think about what terms would surface investigative journalism, deep analysis, documented cases, financial reporting, or expert commentary — whatever best fits the evidence this argument needs. Be specific enough to find real results, broad enough to cast a wide net."\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules for a strong outline:\n"
        "- Every subtopic must earn its place. If two subtopics overlap, merge them or sharpen their distinctions.\n"
        "- Titles should sound like something you'd click on. No academic paper titles.\n"
        "- Angles must be arguable. Not \"an overview of X\" — more like \"here's why X is actually Y\" or \"the case for X.\" If nobody could disagree with it, the angle isn't sharp enough.\n"
        "- Research info should be specific about what kind of evidence the argument needs. Don't just say \"find sources\" — say what kind of sources and what they should demonstrate.\n"
        "- Search queries are THE critical output — Step 2’s entire research quality depends on them. Craft a creative, effective Google search for each subtopic. Start from the observable reality in the angle and search for evidence that proves it. Do not just stuff keywords together — think about what an intelligent person would actually type into Google to find deep analysis, investigative reporting, documented cases, or expert commentary on this specific argument. Be specific enough to surface real results, broad enough to not miss unexpected angles. The query should make sense as a search, not read like a list of concepts.\n"
        "- Cover the brief completely. The full set of subtopics should leave no major aspect of the brief unexplored.\n"
        "- Order matters. Arrange subtopics in the sequence they should appear in the finished article: open strong, build momentum, end memorably.\n\n"
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
        "topic": "", "subtopic_count": 5, "subtopics": [],
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
    topic: str = ""
    subtopic_count: int = 5
    subtopics: list[dict] = []
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
    log_entry("INFO", 1, f"Step 1 data updated. Brief length: {len(data['topic'])}, Subtopics: {len(data['subtopics'])}")
    return {"ok": True}


@app.get("/api/step/1/params")
async def get_step1_params_route():
    """Get Step 1 parameters."""
    params = get_step1_params()
    params["available_models"] = STEP1_MODELS
    return params


class Step1ParamsUpdate(BaseModel):
    model: str = "claude-haiku-4-5"
    temperature: float = 0.5
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

    brief = data.get("topic", "").strip()
    subtopic_count = data.get("subtopic_count", 5)

    if not brief:
        log_entry("ERROR", 1, "No brief provided")
        data["status"] = "failed"
        data["error"] = "No brief provided. Write a brief describing what you want to cover."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    if subtopic_count < 1 or subtopic_count > 20:
        log_entry("ERROR", 1, f"Invalid subtopic count: {subtopic_count}")
        data["status"] = "failed"
        data["error"] = "Subtopic count must be between 1 and 20."
        save_step1_data(data)
        return {"ok": False, "error": data["error"]}

    data["status"] = "running"
    data["error"] = None
    save_step1_data(data)

    model = params.get("model", "claude-haiku-4-5")
    temperature = params.get("temperature", 1.0)
    max_tokens = params.get("max_tokens", 4096)
    system_prompt = params.get("system_prompt", STEP1_DEFAULT_PARAMS["system_prompt"])

    user_message = (
        f"BRIEF: {brief}\n\n"
        f"Generate exactly {subtopic_count} subtopics that comprehensively cover "
        f"the key arguments in the brief above. For each subtopic, provide a title, "
        f"angle, research_info, and search_query as specified in the output schema.\n\n"
        f"The SEARCH QUERY is the most important field. It will be used by a research "
        f"agent with Google Search to find evidence that proves your angle. Craft each "
        f"query as a creative, effective Google search — think about what an intelligent "
        f"person would actually type in to find deep analysis, investigative reporting, "
        f"or documented cases on this specific argument. Make it a search that makes sense, "
        f"not a keyword dump. Be specific enough to surface real results, broad enough to "
        f"catch unexpected angles.\n\n"
        f"Return ONLY valid JSON."
    )

    # NOTE: minItems > 1 and maxItems are NOT supported by Anthropic structured outputs.
    # The exact count is enforced via the user message + system prompt instead.
    output_schema = {
        "type": "object",
        "properties": {
            "subtopics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "1-based index"},
                        "title": {"type": "string", "description": "Sharp, clickable section headline"},
                        "angle": {"type": "string", "description": "The argument this section makes — the claim we're advancing and convincing the reader of"},
                        "research_info": {"type": "string", "description": "The evidence needed to back up this argument: data, historical examples, expert opinions, case studies, legal rulings, personal accounts, institutional patterns — whatever best proves the claim"},
                        "search_query": {"type": "string", "description": "Targeted search query (5-12 words) to find the strongest sources supporting this section's argument"},
                    },
                    "required": ["id", "title", "angle", "research_info", "search_query"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["subtopics"],
        "additionalProperties": False,
    }

    request_body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
        "output_config": {
            "format": {"type": "json_schema", "schema": output_schema},
        },
    }

    log_entry("INFO", 1, f"Calling Anthropic API. Model: {model}, Brief length: {len(brief)}, Count: {subtopic_count}")

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
                    subtopics = parsed.get("subtopics", [])

                    if len(subtopics) != subtopic_count:
                        log_entry("WARN", 1, f"Model returned {len(subtopics)} subtopics, expected {subtopic_count}. Using what was returned.")
                        subtopics = subtopics[:subtopic_count]

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
                    subtopics = _parse_subtopics_fallback(response_text, subtopic_count)
                    if subtopics:
                        data["subtopics"] = subtopics
                        data["status"] = "completed"
                        data["last_run"] = dt.datetime.now().isoformat()
                        data["error"] = None
                        save_step1_data(data)
                        log_entry("WARN", 1, f"Step 1 completed via fallback. Generated {len(subtopics)} subtopics.")
                        return {"ok": True, "subtopics": subtopics}
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
    """Attempt to parse subtopics from unstructured text."""
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
            if len(title) > 3 and not title.lower().startswith(("here", "the ", "these", "below", "above")):
                subtopics.append(title)

    if len(subtopics) >= count:
        return [{"id": i + 1, "title": subtopics[i], "angle": "", "research_info": "", "search_query": ""} for i in range(count)]
    elif len(subtopics) > 0:
        return [{"id": i + 1, "title": subtopics[i], "angle": "", "research_info": "", "search_query": ""} for i in range(len(subtopics))]
    return None


# --- Step 2: Subtopic Research ---

STEP2_DEFAULT_PARAMS = {
    "model": "gemini-2.5-flash-lite",
    "temperature": 0.7,
    "max_tokens": 8192,
    "system_prompt": (
        "You are a research agent. You will be given a specific argument to back up. "
        "You MUST use Google Search to find evidence. Do NOT rely on your training data — "
        "everything you write must be grounded in actual search results.\n\n"
        "Your job is to document the facts as they fit the argument. Go beyond the "
        "obvious surface-level data. Dig into the observable reality: what is actually "
        "happening, why it is happening, what it reveals. Look for the mechanics, the "
        "decisions, the incentives, the cascading effects.\n\n"
        "Before writing anything, search for multiple angles of the topic. Only write "
        "your research brief AFTER you have search results. Cite sources naturally "
        "where you reference specific facts."
    ),
}

STEP2_MODELS = [
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash-Lite (Fastest/Cheapest)"},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Balanced)"},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (Most Capable)"},
    {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash-Lite"},
    {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash (Best)"},
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
        "research_results": [], "status": "idle", "last_run": None, "error": None,
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
    research_results: list[dict] = []
    status: str = "idle"
    error: str | None = None


class Step2ParamsUpdate(BaseModel):
    model: str = "gemini-2.5-flash-lite"
    temperature: float = 0.7
    max_tokens: int = 8192
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
    log_entry("INFO", 2, f"Step 2 data updated. Research results: {len(data['research_results'])}")
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
    log_entry("INFO", 2, f"Step 2 params updated. Model: {params['model']}, Temp: {params['temperature']}")
    return {"ok": True}


@app.post("/api/step/2/run")
async def run_step2():
    """Execute Step 2: run Gemini grounded research for ALL subtopics sequentially."""
    step1_data = get_step1_data()
    step2_data = get_step2_data()
    subtopics = step1_data.get("subtopics", [])

    if not _current_project_path:
        return {"ok": False, "error": "No project loaded."}

    if not subtopics:
        return {"ok": False, "error": "No subtopics from Step 1. Run Step 1 first."}

    # Initialize research results from Step 1 subtopics
    step2_data["research_results"] = _init_research_results(subtopics)
    step2_data["status"] = "running"
    step2_data["error"] = None
    save_step2_data(step2_data)

    log_entry("INFO", 2, f"Starting research for {len(subtopics)} subtopics")

    # Run each sequentially
    for i in range(len(step2_data["research_results"])):
        await _research_single_topic(step2_data, i)

    _update_step2_aggregate_status(step2_data)
    save_step2_data(step2_data)

    log_entry("INFO", 2, f"Step 2 research complete. Status: {step2_data['status']}")
    return {"ok": True, "research_results": step2_data["research_results"]}


@app.post("/api/step/2/run-topic/{topic_id}")
async def run_step2_topic(topic_id: int):
    """Execute Step 2: run Gemini grounded research for a SINGLE subtopic."""
    step2_data = get_step2_data()
    results = step2_data.get("research_results", [])

    idx = _find_result_index_by_topic_id(results, topic_id)

    # Auto-create the result entry if it doesn't exist yet
    if idx is None:
        step1_data = get_step1_data()
        subtopics = step1_data.get("subtopics", [])
        st = next((s for s in subtopics if s.get("id") == topic_id), None)
        if st is None:
            log_entry("ERROR", 2, f"Topic ID {topic_id} not found in Step 1 subtopics either")
            return {"ok": False, "error": f"Topic ID {topic_id} not found in Step 1 or Step 2."}
        # Create new result entry from Step 1 subtopic
        results.append({
            "topic_id": topic_id,
            "research_summary": "",
            "sources": [],
            "status": "idle",
            "error": None,
            "last_run": None,
        })
        idx = len(results) - 1
        step2_data["research_results"] = results
        log_entry("INFO", 2, f"Auto-created research entry for topic #{topic_id}")

    step2_data["status"] = "running"
    results[idx]["status"] = "running"
    results[idx]["error"] = None
    save_step2_data(step2_data)

    log_entry("INFO", 2, f"Researching subtopic #{topic_id}")

    await _research_single_topic(step2_data, idx)

    _update_step2_aggregate_status(step2_data)
    save_step2_data(step2_data)

    return {"ok": True, "result": results[idx]}


# --- Step 2 Core Functions ---


def _init_research_results(subtopics: list[dict]) -> list[dict]:
    """Create research result entries from Step 1 subtopics, preserving completed results."""
    existing = {}
    step2_data = get_step2_data()
    for r in step2_data.get("research_results", []):
        existing[r.get("topic_id")] = r

    results = []
    for st in subtopics:
        tid = st.get("id")
        if tid in existing and existing[tid].get("status") == "completed":
            results.append(existing[tid])
        else:
            results.append({
                "topic_id": tid,
                "research_summary": existing[tid].get("research_summary", "") if tid in existing else "",
                "sources": existing[tid].get("sources", []) if tid in existing else [],
                "status": "idle",
                "error": None,
                "last_run": existing[tid].get("last_run") if tid in existing else None,
            })
    return results


def _find_result_index_by_topic_id(results: list[dict], topic_id: int) -> int | None:
    """Find the index of a research result by its topic_id."""
    for i, r in enumerate(results):
        if r.get("topic_id") == topic_id:
            return i
    return None


def _update_step2_aggregate_status(step2_data: dict) -> None:
    """Update the top-level status based on individual result statuses."""
    results = step2_data.get("research_results", [])
    if not results:
        step2_data["status"] = "idle"
        return

    statuses = [r.get("status", "idle") for r in results]
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


async def _research_single_topic(step2_data: dict, idx: int) -> None:
    """Run grounded Google Search research for one subtopic with retry logic."""
    import httpx
    import asyncio

    result = step2_data["research_results"][idx]
    params = get_step2_params()
    settings = load_settings()

    api_key = settings.get("gemini_key", "").strip()
    if not api_key:
        result["status"] = "failed"
        result["error"] = "No Gemini API key configured. Go to Settings to add one."
        save_step2_data(step2_data)
        return

    model = params.get("model", "gemini-2.5-flash-lite")
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("max_tokens", 8192)
    system_prompt = params.get("system_prompt", STEP2_DEFAULT_PARAMS["system_prompt"])

    # Pull Step 1 subtopic fields for the prompt
    topic_id = result.get("topic_id")
    step1_data = get_step1_data()
    st_fields = {}
    for st in step1_data.get("subtopics", []):
        if st.get("id") == topic_id:
            st_fields = st
            break

    # Build user message from Step 1 subtopic fields
    user_message = (
        f"ARGUMENT TO PROVE: {st_fields.get('angle', '')}\n"
        f"WHAT TO DIG FOR: {st_fields.get('research_info', '')}\n"
        f"SEARCH: {st_fields.get('search_query', '')}\n"
        f"TITLE: {st_fields.get('title', '')}\n\n"
        "CRITICAL: You MUST use Google Search right now to research this topic. "
        "Do not answer from your training data. Execute the search, review the results, "
        "then write a factual research brief grounded in what you found. "
        "Search multiple angles — dig deeper than the first result. "
        "Cite your sources where you reference specific facts."
    )

    # Log the full prompt being sent so the user can inspect it
    log_entry("INFO", 2, (
        f"Prompt for subtopic #{topic_id}:\n"
        f"--- SYSTEM ---\n{system_prompt[:500]}...\n"
        f"--- USER ---\n{user_message}"
    ))

    # Build request body
    is_gemini3 = model.startswith("gemini-3")

    request_body = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_message}]}
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    # Gemini 3+ supports responseFormat + google_search together; 2.5 does not
    if is_gemini3:
        request_body["generationConfig"]["responseFormat"] = {
            "type": "application/json",
            "schema": {
                "type": "object",
                "properties": {
                    "research_summary": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["url", "title"],
                        },
                    },
                },
                "required": ["research_summary", "sources"],
                "additionalProperties": False,
            },
        }

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": api_key,
        "content-type": "application/json",
    }

    log_entry("INFO", 2, f"Researching subtopic #{result.get('topic_id')} with {model}")

    # Attempt 1
    success = await _call_gemini(step2_data, idx, endpoint, headers, request_body, attempt=1, is_gemini3=is_gemini3)

    # Retry after 3s delay on failure
    if not success:
        log_entry("WARN", 2, f"Subtopic #{result.get('topic_id')} failed attempt 1. Retrying in 3s...")
        await asyncio.sleep(3)
        success = await _call_gemini(step2_data, idx, endpoint, headers, request_body, attempt=2, is_gemini3=is_gemini3)

    if success:
        result["status"] = "completed"
        result["last_run"] = dt.datetime.now().isoformat()
        log_entry("INFO", 2, f"Subtopic #{result.get('topic_id')} research completed")
    # If failed, status is already set to "failed" by _call_gemini


async def _call_gemini(
    step2_data: dict, idx: int, endpoint: str, headers: dict,
    request_body: dict, attempt: int, is_gemini3: bool = False,
) -> bool:
    """Make a single Gemini API call. Returns True on success, False on failure."""
    import httpx

    result = step2_data["research_results"][idx]

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(endpoint, headers=headers, json=request_body)

            if resp.status_code == 200:
                resp_data = resp.json()
                candidates = resp_data.get("candidates", [])
                if not candidates:
                    result["status"] = "failed"
                    result["error"] = "Empty response from Gemini (no candidates returned)"
                    save_step2_data(step2_data)
                    return False

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])

                # Extract text from parts — check both "text" key and direct string values
                response_text = ""
                for part in parts:
                    if "text" in part:
                        response_text += part["text"]
                    elif isinstance(part, str):
                        response_text += part

                # If still no text, try top-level text field on content
                if not response_text:
                    response_text = content.get("text", "")

                # Extract sources from THREE places:
                # 1. Inline url_citation annotations on parts
                # 2. groundingMetadata.groundingChunks (generateContent API)
                # 3. groundingMetadata.groundingSupports
                sources = []
                seen_urls = set()

                # Format 1: Inline annotations on parts
                for part in parts:
                    for ann in part.get("annotations", []):
                        if ann.get("type") == "url_citation":
                            url = ann.get("url", "").strip()
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                sources.append({
                                    "url": url,
                                    "title": ann.get("title", ""),
                                })

                # Format 2: groundingMetadata.groundingChunks
                grounding = candidates[0].get("groundingMetadata", {})
                for chunk in grounding.get("groundingChunks", []):
                    web = chunk.get("web", {})
                    url = web.get("uri", "").strip()
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        sources.append({
                            "url": url,
                            "title": web.get("title", ""),
                        })

                # Format 3: groundingMetadata.groundingSupports
                for gs in grounding.get("groundingSupports", []):
                    for seg in gs.get("segment", []):
                        # segment might contain citation info
                        pass

                # Always save sources from grounding metadata
                if sources:
                    result["sources"] = sources

                # For Gemini 3+ with responseFormat, try JSON parse first
                # For 2.5 models (no responseFormat), use raw text directly
                if is_gemini3:
                    parsed = _parse_gemini_json(response_text)
                    if parsed and "research_summary" in parsed:
                        result["research_summary"] = parsed["research_summary"]
                        for s in parsed.get("sources", []):
                            url = (s.get("url") or "").strip()
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                sources.append({"url": url, "title": s.get("title", "")})
                        result["sources"] = sources
                        save_step2_data(step2_data)
                        log_entry("INFO", 2, (
                            f"Subtopic #{result.get('topic_id')} — "
                            f"summary {len(parsed['research_summary'])} chars, "
                            f"{len(sources)} sources"
                        ))
                        return True
                    # Fall through to use raw text if JSON parse fails

                # 2.5 models or JSON parse failed: use raw response text as research_summary
                if response_text.strip():
                    result["research_summary"] = response_text.strip()
                    result["sources"] = sources
                    result["status"] = "completed"
                    save_step2_data(step2_data)
                    usage = resp_data.get("usageMetadata", {})
                    log_entry("INFO", 2, (
                        f"Subtopic #{result.get('topic_id')} — "
                        f"summary {len(response_text)} chars (raw text), "
                        f"{len(sources)} sources from grounding, "
                        f"toolUsePromptTokenCount={usage.get('toolUsePromptTokenCount', 'N/A')}, "
                        f"candidatesTokenCount={usage.get('candidatesTokenCount', 'N/A')}, "
                        f"groundingChunks={len(grounding.get('groundingChunks', []))}"
                    ))
                    return True

                # No text at all — model generated nothing
                result["status"] = "failed"
                result["error"] = (
                    f"Gemini returned no text (attempt {attempt}). "
                    f"Parts: {len(parts)}, grounding chunks: {len(sources)}"
                )
                # Save sources even on failure
                save_step2_data(step2_data)
                log_entry("ERROR", 2, (
                    f"Subtopic #{result.get('topic_id')} — empty response (attempt {attempt}). "
                    f"parts_count={len(parts)}, "
                    f"content_keys={list(content.keys())}, "
                    f"candidate_keys={list(candidates[0].keys())}, "
                    f"sources_from_grounding={len(sources)}"
                ))
                return False

            else:
                error_detail = _extract_gemini_error(resp)
                log_entry("ERROR", 2, f"Gemini API error ({resp.status_code}) attempt {attempt}: {error_detail}")

                result["status"] = "failed"
                if resp.status_code == 401:
                    result["error"] = "Authentication failed. Check your Gemini API key in Settings."
                elif resp.status_code == 403:
                    result["error"] = "Access denied. Your API key may not have permission for this model or Google Search grounding."
                elif resp.status_code == 429:
                    result["error"] = f"Rate limited (attempt {attempt}). The model is busy — try again in a moment."
                elif resp.status_code == 400:
                    result["error"] = f"Bad request (attempt {attempt}): {error_detail}"
                elif resp.status_code == 503:
                    result["error"] = f"Service unavailable (attempt {attempt}). Gemini may be overloaded — try again shortly."
                else:
                    result["error"] = f"API error ({resp.status_code}) attempt {attempt}: {error_detail}"
                save_step2_data(step2_data)
                return False

    except httpx.TimeoutException:
        result["status"] = "failed"
        result["error"] = f"Request timed out after 120s (attempt {attempt})"
        save_step2_data(step2_data)
        log_entry("ERROR", 2, f"Gemini timeout on attempt {attempt} for subtopic #{result.get('topic_id')}")
        return False

    except Exception as e:
        result["status"] = "failed"
        result["error"] = f"Unexpected error (attempt {attempt}): {str(e)}"
        save_step2_data(step2_data)
        log_entry("ERROR", 2, f"Gemini unexpected error attempt {attempt}: {str(e)}")
        return False


def _parse_gemini_json(text: str) -> dict | None:
    """Parse JSON from Gemini response text. Handles markdown fences and common issues."""
    import re

    if not text or not text.strip():
        return None

    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` fences
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { to last } brace pair
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _extract_gemini_error(resp) -> str:
    """Extract error message from a Gemini error response."""
    try:
        err_data = resp.json()
        return err_data.get("error", {}).get("message", resp.text[:500])
    except Exception:
        return resp.text[:500]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
