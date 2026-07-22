# AIIA Editor — RFC & Plan

## Overview

A Python/tkinter desktop GUI that connects to the AIIA HTTP server.
Lives in `../AIIAEditor/` (sibling to OurAI framework).

The editor has three "look" modes, each with different layout, widgets, and
menus. A single window that can also split into floating sub-windows.

---

## Connection

- Connects to `POST /chat` (SSE) for conversation
- Connects to `POST /execute` for direct tool calls
- Optional: `GET /api/v1/health` for status
- Configurable host:port (saved in local config)

---

## Three Editor Modes

### 1. File/Code Editor
```
┌─────────────────────────────────────┐
│ Menu: File | Edit | View | Run      │
├──────────────────┬──────────────────┤
│ File Tree        │ Editor Pane     │
│ (left sidebar)   │ (tabbed files)  │
│                  │                  │
│ project/         │   def hello():  │
│   src/           │     print("hi") │
│   tests/         │                  │
│   config.py      │                  │
├──────────────────┴──────────────────┤
│ AI Chat Pane (bottom)              │
│ ┌──────────────────────────────┐   │
│ │ > create a REST endpoint     │   │
│ │ A: I'll add a Flask route... │   │
│ │                              │   │
│ │ [Input]______________________│   │
│ └──────────────────────────────┘   │
└─────────────────────────────────────┘
```
- Code editor with syntax highlighting (pygments or custom)
- File tree sidebar, tabbed editor panes
- AI chat pane at bottom — send prompts, receive streaming responses
- Highlighted diff view for code changes
- "Apply" button to accept AI-suggested edits
- Terminal pane (optional, collapsible)

### 2. Developer (Project Dashboard)
```
┌─────────────────────────────────────┐
│ Menu: Project | Build | Deploy     │
├──────────┬──────────┬──────────────┤
│ Tasks    │ Timeline │ AI Chat      │
│ (left)   │ (center) │ (right pane) │
│          │          │              │
│ [ ] task1│ ←─┬──┬─→ │ > refactor   │
│ [x] task2│   │  │   │ A: Here's how│
│ [ ] task3│   │  │   │              │
│          │   │  │   │              │
├──────────┴──────────┴──────────────┤
│ Status bar: branch, changes, build │
└─────────────────────────────────────┘
```
- Task/plan view (connects to AIIA plan system)
- Git status overview (branch, dirty files, commit log)
- Build pipeline status
- AI chat pane with plan/build mode switching
- File editor accessible via double-click on files

### 3. Photo/Video Editor
```
┌─────────────────────────────────────┐
│ Menu: File | Filter | Tools       │
├──────────────────┬──────────────────┤
│ Media Preview    │ AI Chat + Tools │
│ (canvas)         │ (right pane)    │
│                  │                  │
│  [image/video]   │ > remove bg     │
│  * zoomable *    │ A: Processing...│
│                  │                  │
│                  │ [Adjustments]   │
│                  │  ┌─┐ brightness │
│                  │  └─┘ contrast   │
├──────────────────┴──────────────────┤
│ Timeline / Layer stack (bottom)    │
└─────────────────────────────────────┘
```
- Image/video preview canvas with zoom/pan
- AI chat for image generation prompts or editing commands
- Sliders for brightness, contrast, crop, resize
- Layer stack or frame timeline for video
- Filter preset browser
- Integration with AIIA image tools (`ReadImage`, `ImageTransform`)

### 4. Book Editor (Literary)
```
┌─────────────────────────────────────┐
│ Menu: File | Write | Analyze      │
├──────────────┬──────────────────────┤
│ Chapter Nav  │ Editor Pane         │
│ (left)       │ (full text)         │
│              │                      │
│ Ch 1: Dawn   │ It was a dark and   │
│ Ch 2: Storm  │ stormy night...     │
│ Ch 3: ...    │                      │
│              │                      │
├──────────────┼──────────────────────┤
│ Notes (collapsible)                │
│ ┌──────────────────────────────┐   │
│ │ Characters, plot arcs, etc  │   │
│ └──────────────────────────────┘   │
├──────────────┴──────────────────────┤
│ AI Chat (bottom)                   │
│ > analyze this chapter's pacing    │
│ A: The pacing in Ch 2 slows...     │
└─────────────────────────────────────┘
```
- Chapter navigator with word counts per chapter
- Rich text editor or plain text with markdown preview
- Notes sidebar for character sheets, plot arcs (syncs with AIIA tips)
- AI chat pane specialized for BookSmith personas
- Revision history per chapter

---

## Window Architecture

```
App
├── MenuBar (changes per mode)
├── MainContent
│   ├── LeftPane   (file tree / nav / tasks)
│   ├── CenterPane (editor / canvas / preview)
│   └── RightPane  (AI chat or tools)
├── BottomPane (terminal / timeline / notes)
└── StatusBar
```

### Detach / Float
Any pane can be "popped out" into its own top-level tkinter window.
Windows can re-dock back into the main layout.

- Right-click tab → "Detach pane"
- Close detached window → re-docks
- State saved between sessions

### Splitter bars
tkinter `PanedWindow` for resizable splits between all panes.

---

## Implementation Plan

### Phase 1 — Skeleton + HTTP Client
- [ ] Create `../AIIAEditor/` with `main.py`
- [ ] HTTP SSE client (threaded) connecting to AIIA server
- [ ] Single window with AI chat pane (proves connection)
- [ ] Text input + streaming output display

### Phase 2 — Mode Framework
- [ ] Mode registry: each mode is a class with `build_menu()`, `build_layout()`
- [ ] Menu switching between modes
- [ ] PanedWindow layout with detachable panes

### Phase 3 — File Editor Mode
- [ ] File tree widget
- [ ] Syntax-highlighted editor (tkText + tags)
- [ ] Tabbed editing
- [ ] Apply AI-suggested edits

### Phase 4 — Developer Mode
- [ ] Task view (connects to AIIA plan API)
- [ ] Git status widget
- [ ] Build output pane

### Phase 5 — Media Mode
- [ ] Image preview canvas (PIL/tkinter)
- [ ] Adjustment sliders
- [ ] Integration with AIIA image tools

### Phase 6 — Book Mode
- [ ] Chapter navigator
- [ ] Markdown preview
- [ ] Tips integration

### Phase 7 — Polish
- [ ] Detach/float/dock for all panes
- [ ] Session state persistence
- [ ] Preferences window
- [ ] Keyboard shortcuts

---

## API Dependencies

The editor needs these endpoints from the AIIA server:

| Endpoint | Used By | Purpose |
|----------|---------|---------|
| `POST /chat` | All modes | Send prompts, receive streaming AI responses |
| `POST /execute` | File/Dev modes | Execute tools directly (ReadFile, WriteFile, Grep, etc.) |
| `GET /health` | All modes | Connection status check |
| `GET /` | All modes | API index, version info |

## Future: Additional Endpoints the Editor Would Like

- `GET /api/v1/plans` — list active plans/tasks
- `POST /api/v1/plans` — create a plan
- `GET /api/v1/state` — full session state (mode, persona, model)
- `POST /api/v1/tools` — list available tools with schemas
- `POST /api/v1/upload` — upload files to `workin/`
- `POST /api/v1/download` — download files from `workout/`
