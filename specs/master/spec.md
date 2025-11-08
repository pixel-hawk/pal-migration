# Feature Specification: Web-Based Palworld Save Migration Tool

**Status**: Draft | **Date**: 2025-11-08 | **Version**: 1.0

## Overview

A web-based tool to facilitate smooth migration of Palworld save files between host/co-op and dedicated server modes through a browser interface. Users upload save archives, view player mappings in a dual-panel UI, select source and target players, and download migrated saves.

## Background

The existing `gui_palworld_tool` provides desktop GUI (tkinter) for Palworld save migration via the "Fix Host Save" feature. This performs GUID swapping in `Level.sav` and player `.sav` files to transfer characters between hosting modes. The new tool must:

1. Expose the same core migration logic via web API
2. Replace tkinter UI with modern browser interface
3. Support one-to-one player mapping with visual confirmation
4. Use UV for Python dependency management instead of requirements.txt
5. Return final migrated save as downloadable zip

## User Stories

### US-1: Upload Save Archive
**As a** player  
**I want to** upload a zip containing `Level.sav` and `Players/` folder  
**So that** the system can analyze available players

**Acceptance Criteria**:
- Web page accepts .zip file upload via drag-drop or file picker
- Backend extracts and validates presence of `Level.sav` and `Players/` folder
- Returns error if structure is invalid
- Preserves original file for migration

### US-2: View Player Mappings
**As a** player  
**I want to** see dual lists of source and target players with GUID, Name, Guild ID  
**So that** I can identify which characters to swap

**Acceptance Criteria**:
- UI displays two side-by-side panels (similar to attached screenshot)
- Each panel shows: GUID, Player Name, Guild ID
- Search/filter capability in each panel
- Visual distinction between selected source and target

### US-3: Execute Migration
**As a** player  
**I want to** select source player and target player, then click "Migrate"  
**So that** the tool swaps their GUIDs and returns updated save files

**Acceptance Criteria**:
- "Migrate" button enabled only when both source and target selected
- Backend calls `fix_host_save.fix_save()` with selected GUIDs
- Non-interactive mode (no tkinter dialogs)
- Progress indicator during migration
- Error handling with user-friendly messages

### US-4: Download Migrated Save
**As a** player  
**I want to** download the migrated save as a zip file  
**So that** I can replace my game save folder

**Acceptance Criteria**:
- Automatic download of `migrated.zip` after successful migration
- Zip contains updated `Level.sav`, `Players/` folder, and backup metadata
- Original uploaded file remains unmodified
- Clear success message with next steps

## Functional Requirements

### FR-1: File Upload & Validation
- Accept `.zip` files up to 500MB
- Validate zip structure: must contain `Level.sav` at root or one level deep
- Validate `Players/` folder with at least one `.sav` file
- Return HTTP 400 with descriptive error for invalid structure

### FR-2: Player Analysis API
- Parse `Level.sav` using existing `palworld_save_tools` library
- Extract player list with GUID, name, guild from GroupSaveDataMap
- Return JSON array of player objects: `{guid, name, guild_id}`

### FR-3: Migration Engine
- Reuse `gui_palworld_tool/Assets/fix_host_save.py::fix_save()` function
- Monkeypatch tkinter dialogs to non-interactive defaults
- Perform GUID swap in Level.sav and player .sav files
- Handle DPS file copying
- Create backup before modification (disabled for web mode to avoid server bloat)

### FR-4: Modern Web UI
- Single-page application with dual-panel player selector
- Responsive design (desktop primary, mobile secondary)
- Dark theme matching Palworld aesthetic
- Search/filter for each player list
- Clear visual feedback for selection state
- Progress spinner during upload and migration

### FR-5: Dependency Management
- Use UV with `pyproject.toml` for all Python dependencies
- No `requirements.txt` files
- Support for development dependencies separate from runtime

## Non-Functional Requirements

### NFR-1: Performance
- Upload processing < 5 seconds for typical 50MB save
- Migration execution < 10 seconds
- UI response time < 100ms for interactions

### NFR-2: Security
- Runs on localhost by default (127.0.0.1:8000)
- No authentication in v1 (local-only deployment)
- Uploaded files stored in temporary directories with auto-cleanup
- No persistent storage of user saves

### NFR-3: Reliability
- Graceful error handling for corrupted saves
- Validation of GUID format before migration
- Atomic operations (migration succeeds completely or rolls back)

### NFR-4: Maintainability
- Clear separation: web layer (FastAPI) vs core logic (existing Assets/)
- Minimal modifications to existing `fix_host_save.py`
- Comprehensive logging for debugging

## Technical Constraints

1. **Reuse existing code**: Must import and call functions from `gui_palworld_tool/Assets/`
2. **Python ecosystem**: Python 3.11+, FastAPI, UV package manager
3. **No tkinter**: All GUI dialogs must be patched or bypassed
4. **Stateless backend**: No database, no session persistence beyond request lifecycle
5. **Local deployment**: Designed for single-user local execution, not multi-tenant cloud

## UI Design Reference

The attached screenshot shows the desired dual-panel layout:
- Left panel: "Source Player" list with GUID, Name, Guild ID columns
- Right panel: "Target Player" list with same columns
- Search boxes above each list
- "Migrate" button to trigger operation
- Dark theme with table styling

Improvements over screenshot:
- Add file upload area at top
- Add progress indicators
- Add success/error notifications
- Make responsive

## Out of Scope (v1)

- Multi-file batch migration
- Undo functionality
- Save file history/versioning
- Direct folder path input (zip-only for v1)
- Authentication/authorization
- Cloud deployment configuration
- Real-time collaboration

## Success Criteria

1. User can upload save zip and see player list within 5 seconds
2. User can select source and target players and complete migration in under 15 seconds total
3. Downloaded zip successfully loads in Palworld without errors
4. Tool runs on Windows with single command: `uv run app.py`
5. Zero tkinter dependencies in web mode

## Dependencies

- Existing `gui_palworld_tool/Assets/` modules (palworld_save_tools, fix_host_save)
- Python 3.11+
- FastAPI
- UV package manager
- Modern browser (Chrome/Firefox/Edge latest versions)

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Corrupted save files | High - migration fails | Validate structure before processing, clear error messages |
| tkinter dialogs block server | High - hangs | Monkeypatch all messagebox/dialog calls |
| Large file uploads timeout | Medium | Stream processing, increase timeout limits |
| Browser compatibility | Low | Use standard HTML5/ES6, test on major browsers |

## Timeline Estimate

- Phase 0 (Research): 1 hour
- Phase 1 (Design & Contracts): 2 hours
- Phase 2 (Implementation): 4 hours
- Testing & Polish: 2 hours
- **Total**: ~9 hours

## Appendix: Migration Process

The tool follows this workflow (from README.en.md):

1. User copies old Level.sav + Players from original save location
2. User pastes into new save location (host ↔ server)
3. User creates new character in game (~2 min)
4. User uploads save to web tool
5. Tool shows old character (from original) and new character (just created)
6. User selects both and clicks Migrate
7. Tool performs GUID swap and returns migrated.zip
8. User extracts to save folder and launches game

The web tool specifically handles steps 4-7.
