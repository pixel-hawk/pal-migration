# Migration Checklist: gui_palworld_tool → web_service

**Status**: Planning Phase | **Target**: Complete self-contained web service

## Overview

This document tracks the migration of core Palworld save manipulation logic from the desktop GUI tool (`gui_palworld_tool/`) into the self-contained web service (`web_service/`). Once complete, the old folder will be deleted.

---

## Phase 1: Copy palworld_save_tools Library

**Goal**: Get the core save parsing library into web_service without modifications.

### Tasks

- [ ] Copy `gui_palworld_tool/Assets/palworld_save_tools/` → `web_service/core/palworld_save_tools/`
  - [ ] `__init__.py`
  - [ ] `archive.py`
  - [ ] `gvas.py`
  - [ ] `json_tools.py`
  - [ ] `palsav.py`
  - [ ] `paltypes.py`
  - [ ] `commands/` (convert.py, resave_test.py)
  - [ ] `compressor/` (enums.py, oozlib.py, zlib.py)
  - [ ] `rawdata/` (all modules: base_camp.py, character.py, group.py, etc.)

- [ ] Update imports in copied files
  - [ ] Change relative imports to `from web_service.core.palworld_save_tools import ...`
  - [ ] Remove any tkinter dependencies (none expected in this library)

- [ ] Test basic parsing
  ```python
  from web_service.core.palworld_save_tools.palsav import decompress_sav_to_gvas
  from web_service.core.palworld_save_tools.gvas import GvasFile
  # Test with a sample Level.sav
  ```

**Dependencies**: loguru (already in pyproject.toml)

---

## Phase 2: Refactor fix_host_save.py Logic

**Goal**: Extract pure migration functions without GUI dependencies.

### Tasks

- [ ] Create `web_service/core/migration.py`

- [ ] Port core functions from `gui_palworld_tool/Assets/fix_host_save.py`:
  - [ ] `sav_to_json(filepath)` → Keep as-is (uses palworld_save_tools)
  - [ ] `json_to_sav(json_data, output_path)` → Keep as-is
  - [ ] `fix_save(save_path, new_guid, old_guid, guild_fix=True)` → Refactor:
    ```python
    def migrate_guids(
        save_folder: Path,
        source_guid: str,
        target_guid: str,
        rename_world: Optional[str] = None,
        create_backup: bool = False
    ) -> Dict[str, Any]:
        """
        Swap GUIDs between two players in Palworld save files.
        
        Returns dict with:
          - success: bool
          - message: str
          - backup_path: Optional[str]
        """
    ```
  - [ ] Remove all tkinter calls:
    - [ ] `messagebox.askyesno(...)` → use `rename_world` parameter
    - [ ] `messagebox.showinfo(...)` → return status dict
    - [ ] `messagebox.showerror(...)` → raise exceptions
    - [ ] `ask_string_with_icon(...)` → parameter
  - [ ] Remove window creation code (all `tk.Toplevel`, `tk.Tk()`)

- [ ] Port helper functions:
  - [ ] `copy_dps_file(src_folder, src_uid, tgt_folder, tgt_uid)`
  - [ ] `backup_whole_directory(source, backup)` → make optional
  - [ ] `deep_swap_ownership(data, old_uid, new_uid)`
  - [ ] `count_owner_uid(data, uid)`

- [ ] Create `web_service/core/save_parser.py` for analysis:
  ```python
  def extract_players(level_sav_path: Path) -> List[PlayerInfo]:
      """
      Parse Level.sav and return list of players with GUID, name, guild.
      Extracted from populate_player_lists() in fix_host_save.py
      """
  ```

**Testing**:
- [ ] Unit test: `test_migration.py::test_guid_swap`
- [ ] Unit test: `test_migration.py::test_dps_file_copy`
- [ ] Unit test: `test_save_parser.py::test_extract_players`

---

## Phase 3: Update web_service to Use Migrated Code

**Goal**: Replace temporary stub code with real migration logic.

### Tasks

- [ ] Update `web_service/core.py` → Rename to `web_service/core/__init__.py`
  - [ ] Import from `migration.py` and `save_parser.py`
  - [ ] Remove old sys.path manipulation (no longer importing from gui_palworld_tool)
  - [ ] Remove tkinter monkeypatch (no longer needed)

- [ ] Update `web_service/app.py`:
  - [ ] Replace analyze logic to use `core.save_parser.extract_players()`
  - [ ] Replace migrate logic to use `core.migration.migrate_guids()`
  - [ ] Add proper error handling for migration exceptions

- [ ] Create `web_service/models.py` with Pydantic models (from data-model.md):
  - [ ] `Player`
  - [ ] `MigrationRequest`
  - [ ] `MigrationResponse`
  - [ ] `ErrorResponse`

**Testing**:
- [ ] Integration test: `test_api.py::test_analyze_endpoint`
- [ ] Integration test: `test_api.py::test_migrate_endpoint`
- [ ] Integration test: `test_api.py::test_full_migration_flow`

---

## Phase 4: Build Production UI

**Goal**: Create polished dual-panel interface matching screenshot.

### Tasks

- [ ] `web_service/templates/index.html`:
  - [ ] File upload area (drag-drop + file picker)
  - [ ] Dual-panel layout (CSS Grid)
  - [ ] Left panel: Source Player table (GUID, Name, Guild ID)
  - [ ] Right panel: Target Player table (GUID, Name, Guild ID)
  - [ ] Search boxes above each table
  - [ ] Migrate button (disabled until both selected)
  - [ ] Progress spinner overlay
  - [ ] Success/error toast notifications

- [ ] `web_service/static/styles.css`:
  - [ ] Dark theme (#2f2f2f background)
  - [ ] Table styling (zebra striping, hover effects)
  - [ ] Selection highlighting
  - [ ] Responsive layout (desktop primary)

- [ ] `web_service/static/app.js`:
  - [ ] File upload handling
  - [ ] Fetch `/analyze` and populate tables
  - [ ] Search/filter functionality per table
  - [ ] Row selection tracking
  - [ ] Fetch `/migrate` and trigger download
  - [ ] Progress indicators

**Testing**:
- [ ] Manual: Upload real Palworld save and test full flow
- [ ] Manual: Test with corrupted zip (verify error handling)
- [ ] Manual: Test with large file (500MB near limit)

---

## Phase 5: Documentation & Polish

### Tasks

- [ ] Update root `README.md`:
  - [ ] Add web service section
  - [ ] Link to `specs/master/quickstart.md`
  - [ ] Add screenshot of web UI

- [ ] Create `web_service/README.md`:
  - [ ] Installation instructions
  - [ ] API documentation (link to OpenAPI spec)
  - [ ] Development guide

- [ ] Update `pyproject.toml`:
  - [ ] Ensure all dependencies listed
  - [ ] Add scripts section:
    ```toml
    [project.scripts]
    palworld-web = "web_service.app:main"
    ```

- [ ] Add `web_service/__main__.py` for `python -m web_service`:
  ```python
  import uvicorn
  uvicorn.run("web_service.app:app", host="127.0.0.1", port=8000)
  ```

---

## Phase 6: Validation & Cleanup

### Final Checks

- [ ] All tests passing: `uv run pytest web_service/tests/`
- [ ] Linting clean: `uv run ruff check web_service/`
- [ ] Type checking (if using mypy): `uv run mypy web_service/`
- [ ] Manual end-to-end test with real save files
- [ ] Verify backup creation (if enabled)
- [ ] Verify migrated save loads in Palworld

### Remove Old Code

- [ ] **DELETE** `gui_palworld_tool/` folder entirely
- [ ] Update `.gitignore` if needed
- [ ] Update any references in other docs

---

## Estimated Timeline

| Phase | Estimated Time | Status |
|-------|---------------|--------|
| Phase 1: Copy library | 30 min | ⏳ Not started |
| Phase 2: Refactor migration | 2-3 hours | ⏳ Not started |
| Phase 3: Integrate with web_service | 1 hour | ⏳ Not started |
| Phase 4: Production UI | 2-3 hours | ⏳ Not started |
| Phase 5: Documentation | 1 hour | ⏳ Not started |
| Phase 6: Validation & cleanup | 1 hour | ⏳ Not started |
| **Total** | **~8-10 hours** | |

---

## Key Refactoring Patterns

### Before (GUI-coupled):
```python
# gui_palworld_tool/Assets/fix_host_save.py
def fix_save(save_path, new_guid, old_guid, guild_fix=True):
    # ... logic ...
    if messagebox.askyesno("Rename?", f"Current: {old_name}"):
        new_name = ask_string_with_icon("Enter name:", ...)
        meta_json['WorldName'] = new_name
    # ... more logic ...
    messagebox.showinfo("Success", "Migration complete!")
```

### After (Pure function):
```python
# web_service/core/migration.py
def migrate_guids(
    save_folder: Path,
    source_guid: str,
    target_guid: str,
    rename_world: Optional[str] = None,
    create_backup: bool = False
) -> MigrationResult:
    """Pure function - no side effects except file I/O."""
    # ... logic ...
    if rename_world:
        meta_json['WorldName'] = rename_world
    # ... more logic ...
    return MigrationResult(
        success=True,
        message="Migration complete",
        backup_path=backup_path if create_backup else None
    )
```

---

## Dependencies to Add

Already in `pyproject.toml`:
- ✅ fastapi
- ✅ uvicorn
- ✅ python-multipart
- ✅ jinja2
- ✅ loguru

May need to add:
- [ ] `aiofiles` (for async file operations if needed)
- [ ] `pytest-asyncio` (dev dependency, for async tests)

---

## Success Criteria

- [ ] Web service runs without importing from `gui_palworld_tool/`
- [ ] No tkinter imports anywhere in `web_service/`
- [ ] All unit tests pass
- [ ] Integration tests pass with real save files
- [ ] Manual end-to-end migration succeeds in Palworld
- [ ] `gui_palworld_tool/` folder deleted with no errors
- [ ] Documentation updated and accurate

---

## Notes

- Keep commits atomic (one phase per commit)
- Tag versions: `v1.0.0-web-migration-complete`
- Consider keeping gui_palworld_tool in a separate branch before deletion (for reference)
