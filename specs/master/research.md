# Research: Web-Based Palworld Save Migration Tool

**Date**: 2025-11-08 | **Status**: Complete

## Overview

This document resolves technical uncertainties from the Technical Context section of the implementation plan. Each decision is documented with rationale and alternatives considered.

---

## Research Tasks

### 1. Frontend Framework Choice

**Question**: Vanilla JS + HTML/CSS vs React/Vue/Svelte for dual-panel player selection UI?

**Decision**: **Vanilla JavaScript + HTML5 + Modern CSS**

**Rationale**:
- **Simplicity**: The UI has minimal complexity - two tables, search boxes, file upload, and a button
- **No build step**: Eliminates webpack/vite configuration, faster iteration
- **Dependency minimization**: Aligns with project goal of reusing existing code rather than adding frameworks
- **Performance**: Native DOM manipulation is sufficient for <100 players per list
- **Template integration**: Works seamlessly with Jinja2 templates served by FastAPI
- **User reference**: The attached screenshot shows a table-based UI that doesn't require framework abstractions

**Alternatives Considered**:
- **React**: Rejected - overkill for 2 tables, adds 200KB+ bundle, requires build pipeline
- **Vue**: Rejected - similar complexity to React, unnecessary for this scale
- **Svelte**: Rejected - while lightweight, still adds compilation step and learning curve
- **Alpine.js**: Considered - lightweight (15KB), good for reactive UIs, but vanilla JS suffices here

**Implementation Notes**:
- Use `<template>` tags for row rendering
- `fetch()` API for AJAX calls to backend
- CSS Grid for dual-panel layout
- Native `FormData` for file uploads
- Event delegation for table interactions

---

### 2. File Upload Best Practices in FastAPI

**Question**: How to handle streaming large (up to 500MB) zip uploads efficiently?

**Decision**: **Use FastAPI's `UploadFile` with chunked reading + temp file storage**

**Rationale**:
- **FastAPI's `UploadFile`** wraps Starlette's SpooledTemporaryFile, automatically streams large files to disk
- **Memory efficiency**: Doesn't load entire file into RAM, critical for 500MB limit
- **Built-in validation**: `File(...)` parameter allows size limits via dependency injection
- **Simplicity**: No custom stream handling needed

**Best Practices Applied**:
```python
from fastapi import UploadFile, File, HTTPException

@app.post("/analyze")
async def analyze(file: UploadFile = File(..., max_size=500*1024*1024)):
    # UploadFile.file is SpooledTemporaryFile
    content = await file.read()  # Streams from disk if large
    # Or iterate chunks:
    # async for chunk in file:
    #     process(chunk)
```

**Alternatives Considered**:
- **Direct request.body() streaming**: Rejected - more complex, UploadFile handles it
- **Chunked multipart**: Rejected - FastAPI's UploadFile already implements this
- **External storage (S3, etc.)**: Rejected - localhost deployment doesn't need it

**Additional Configurations**:
- Set `client_max_body_size` in Uvicorn config if needed (default 100MB)
- Use `aiofiles` for async file I/O if processing bottlenecks occur
- Add progress tracking via WebSockets if real-time feedback required (future enhancement)

---

### 3. UV + pyproject.toml Patterns

**Question**: How to structure pyproject.toml for UV with separate dev/runtime dependencies?

**Decision**: **Use UV's dependency groups in pyproject.toml**

**Rationale**:
- **UV native support**: UV understands `[dependency-groups]` for separating concerns
- **PEP 735 compliance**: Follows emerging standard for Python dependency management
- **Simple installation**: `uv sync` installs all, `uv sync --no-dev` for production
- **Lock file generation**: `uv.lock` pins exact versions for reproducibility

**Implementation Example**:
```toml
[project]
name = "palworld-web-migrator"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.9",
    "jinja2>=3.1.3",
    "loguru>=0.7.2",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.26.0",  # For testing FastAPI
    "pytest-asyncio>=0.23.0",
    "ruff>=0.2.0",  # Linting
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "httpx>=0.26.0",
]

[tool.pytest.ini_options]
testpaths = ["web_service/tests"]
asyncio_mode = "auto"
```

**Key Commands**:
- `uv sync` - Install all dependencies + dev
- `uv run app.py` - Run with UV's managed environment
- `uv add <package>` - Add runtime dependency
- `uv add --dev <package>` - Add dev dependency
- `uv lock` - Update lock file

**Alternatives Considered**:
- **Poetry**: Rejected - UV is faster, spec requires UV specifically
- **requirements.txt + pip**: Rejected - spec explicitly forbids requirements.txt
- **Conda**: Rejected - UV provides better Python-native workflow

**Migration Notes**:
- The existing `web_service/requirements.txt` created earlier should be removed
- Convert those deps to pyproject.toml at root level
- Existing `gui_palworld_tool/pyproject.toml` can remain for that subproject

---

### 4. Dual-Panel UI Design Pattern

**Question**: Best way to implement synchronized dual-table player selection?

**Decision**: **Independent table components with shared selection state**

**Rationale**:
- **Separation of concerns**: Each panel (source/target) manages its own data and filtering
- **State management**: Simple JavaScript object holds selected GUIDs
- **Event-driven updates**: Click handlers update shared state and enable/disable migrate button
- **Search independence**: Each search box filters its own table without affecting the other

**Implementation Pattern**:
```javascript
const state = {
    players: [],
    sourceSelected: null,
    targetSelected: null,
};

function renderTable(containerId, players) {
    // Render rows with click handlers
    rows.forEach(row => {
        row.addEventListener('click', () => {
            if (containerId === 'source') state.sourceSelected = row.guid;
            else state.targetSelected = row.guid;
            updateMigrateButton();
        });
    });
}

function updateMigrateButton() {
    const btn = document.getElementById('migrate-btn');
    btn.disabled = !(state.sourceSelected && state.targetSelected);
}
```

**Alternatives Considered**:
- **Single table with dual selection**: Rejected - confusing UX, doesn't match reference screenshot
- **Drag-and-drop mapping**: Rejected - nice-to-have, adds complexity for v1
- **Checkbox selection**: Rejected - radio buttons better for one-to-one mapping

---

### 5. Tkinter Elimination Strategy

**Question**: How to handle tkinter dependencies when migrating code?

**Decision**: **Complete removal - refactor code to eliminate all GUI calls**

**Rationale**:
- **Clean architecture**: Web service shouldn't have GUI dependencies
- **Full control**: Can simplify logic without dialog interruptions
- **Better for removal**: Since `gui_palworld_tool/` will be deleted, we need self-contained code
- **Easier testing**: No mocking needed, pure functions
- **Smaller dependency footprint**: No need for tkinter in production

**Refactoring Strategy**:
```python
# OLD (gui_palworld_tool/Assets/fix_host_save.py):
if messagebox.askyesno("Rename World?", f"Current: {old_name}"):
    new_name = ask_string_with_icon("Enter new name:", ...)
    meta_json['WorldName'] = new_name

# NEW (web_service/core/migration.py):
def migrate_save(folder: str, old_guid: str, new_guid: str, 
                 rename_world: Optional[str] = None):
    """
    Pure function - no GUI calls.
    rename_world parameter allows API to pass new name if desired.
    """
    if rename_world:
        meta_json['WorldName'] = rename_world
```

**Migration Checklist**:
- ✅ Remove all `import tkinter` statements
- ✅ Remove `messagebox.showinfo()` calls → replace with logging
- ✅ Remove `messagebox.askyesno()` → pass as function parameters
- ✅ Remove `simpledialog.askstring()` → optional API parameters
- ✅ Remove window creation (`tk.Toplevel()`, `tk.Tk()`)
- ✅ Extract core logic into pure functions

**Alternatives Considered**:
- **Monkeypatch/mock**: Rejected - still couples code to tkinter API
- **Keep original + wrapper**: Rejected - defeats purpose of removing gui_palworld_tool
- **Subprocess isolation**: Rejected - overhead, complexity
- **Conditional imports**: Rejected - cleaner to remove entirely

---

## Summary of Decisions

| Area | Decision | Impact |
|------|----------|--------|
| Frontend | Vanilla JS + HTML/CSS | No build step, faster development |
| File Upload | FastAPI UploadFile with streaming | Handles 500MB efficiently |
| Dependency Mgmt | UV + pyproject.toml with groups | Modern, fast, spec-compliant |
| UI Pattern | Independent dual tables | Clear one-to-one mapping |
| Tkinter Patching | Import-time monkeypatch | Non-invasive to existing code |

## Next Steps

Proceed to **Phase 1: Data Model & Contracts**:
1. Define Pydantic models for Player, UploadResponse, MigrationRequest
2. Generate OpenAPI contract for API endpoints
3. Create quickstart.md for running the application
4. Update agent context with chosen technologies
