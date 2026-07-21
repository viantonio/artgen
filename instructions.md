# Project: Automated Article Generator (AI Pipeline)

## Overview

Build a 5-step pipeline that turns a topic into a fully illustrated, styled article.
Each step is **independent**: its own UI panel/window, its own stored data, its own
ability to run, re-run, or be edited in isolation without needing to re-run other
steps. The user must be able to jump between steps freely to inspect, edit, and
re-trigger any part of the pipeline.

**Build order: sequential, one step at a time.** Do not start Step 2 until Step 1
is confirmed working. Do not build Step 5 at all until explicitly told to — build
Steps 1–4 first, then stop and wait for further instruction before starting Step 5.

---

## Pipeline Steps

### Step 1 — Subtopic Planning
- **Input:** a topic (string) + a number of subtopics (int), both entered by the user.
- **Model:** Anthropic, starting with Haiku. Model must be user-selectable (see
  "Model Selection" below), Haiku is just the starting default.
- **Behavior:** The system prompt — not the user — decides what the subtopics
  actually are. The user only supplies the topic and the count. On "Go," make one
  API call that returns a JSON schema/object listing the subtopics to be researched.
- **Output:** structured JSON (topic + list of subtopics), saved as this step's
  persistent data, used as input to Step 2.
- **Calls per run:** 1.

### Step 2 — Subtopic Research
- **Input:** the subtopic list from Step 1.
- **Model:** Gemini, using grounded Google Search.
- **Behavior:** One API call per subtopic, run **one at a time** (not all
  in parallel) — the user should be able to trigger research for a single
  subtopic independently. Each call should produce an "informed opinion" /
  research summary for that subtopic, grounded in search results.
- **Error handling:**
  - If a call fails to generate, do **not** retry automatically and do **not**
    fall back to a different model. Surface the failure clearly.
  - Log every failure to a continuously-updated system log (see "System Log"
    below) with a useful, specific error message, so the user can decide what
    to tell the agent to fix.
  - The user manually re-triggers the failed subtopic once ready.
- **Output:** one research result per subtopic, saved as this step's data,
  used as input to Step 3.
- **Calls per run:** N (one per subtopic).

### Step 3 — Article Draft
- **Input:** all subtopic research results from Step 2.
- **Model:** Anthropic (better writing quality than Gemini for this purpose).
- **Behavior:** One API call that condenses/synthesizes all Step 2 research
  into a single first-draft article.
- **Output:** draft article text, saved as this step's data, used as input to
  Step 4.
- **Calls per run:** 1.

### Step 4 — Style Rewrite
- **Input:** the draft article from Step 3.
- **Model:** Anthropic (again, for writing quality).
- **Behavior:** One API call that rewrites the article in the tone/style of
  classic Cracked.com — irreverent, funny, entertaining. This is a system
  prompt engineering task; the style needs to be well specified in the
  system prompt.
- **Output:** rewritten article, saved as this step's data, used as input to
  Step 5.
- **Calls per run:** 1.
- **Note:** Build this step, but do not proceed to Step 5 until told to.

### Step 5 — Image Generation (build later, on explicit go-ahead)
- **Input:** the styled article from Step 4.
- **Model:** Gemini.
- **Behavior:** Analyze the finished article and a user-set target number of
  images. For each image, the model determines (a) where in the article it
  should go and (b) a generation prompt for it. Images are then generated and
  programmatically inserted at those locations to produce the finished,
  illustrated article.
- **Output:** final illustrated article.
- **Do not start this step until Steps 1–4 are confirmed working and the user
  explicitly asks for it.**

---

## Cross-Cutting Requirements

### Independent step architecture
- Each step is its own panel/window with its own persisted data store (its
  inputs, outputs, and run status).
- Any step can be run, re-run, or edited on its own without forcing a re-run
  of other steps.
- Editing a step's output and re-running a later step should pick up the
  edited data.
- The user needs to be able to move forward (step N → N+1) or backward
  (re-open and edit an earlier step) at will.

### Model selection
- Step 1: Anthropic — default model Haiku, but user-selectable.
- Step 2: Gemini (grounded Google Search).
- Step 3: Anthropic.
- Step 4: Anthropic.
- Step 5: Gemini.
- **No automatic model fallback on failure, ever.** If a call fails, it fails
  visibly and gets logged. The user decides how to respond — never silently
  substitute a different model.

### API key management
- API keys (Anthropic, Gemini) are set once in a settings area that:
  - Lets the user validate the key (test call to confirm it works).
  - Persists the key so it never has to be re-entered on subsequent runs.

### System log
- A continuously-updated, user-visible system log capturing all pipeline
  activity, especially failures.
- Failure entries must include a specific, useful error message (not just
  "failed") — enough detail that the user knows what to tell the coding
  agent to fix.

### Prompt & parameter transparency
- The user must be able to inspect the exact system prompt sent to the model
  for every step/call.
- The user must be able to inspect and edit the parameters (temperature,
  max tokens, model name, etc.) for every step/call.

### Project persistence
- A save function that persists the full project state (all step data, logs,
  settings) to disk.
- On launch, the program automatically reopens the last project worked on —
  no manual "open project" step required.

### Platform
- Must run on both Windows and Linux. Choose whatever format/stack
  satisfies this and all requirements above (e.g., a local web app served
  from a cross-platform backend, or an Electron-style desktop app) — the
  specific stack is your call as long as it meets these constraints.

---

## Build Instructions for the Agent

Work through this sequentially, not all at once:

1. Build Step 1 only. Stop and wait for the user to test it.
2. Once Step 1 is confirmed good, build Step 2. Stop and wait for testing.
3. Once Step 2 is confirmed good, build Step 3. Stop and wait for testing.
4. Once Step 3 is confirmed good, build Step 4. Stop and wait for testing.
5. Do not build Step 5 until explicitly instructed, even after Step 4 is done.

Reference materials: Anthropic API usage docs are in the `anthropic` folder
(see its text-generation file) for Steps 1, 3, and 4. Gemini API usage docs
(grounded search) apply to Step 2, and Gemini image generation docs apply
to Step 5.