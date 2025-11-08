# Quickstart Guide: Palworld Web Migration Tool

**Version**: 1.0.0 | **Updated**: 2025-11-08

## Prerequisites

- **Python**: 3.11 or higher
- **UV**: Package manager ([install instructions](https://github.com/astral-sh/uv))
- **OS**: Windows (primary), Linux/macOS (experimental)
- **Browser**: Chrome, Firefox, or Edge (latest version)

---

## Installation

### 1. Clone or Navigate to Repository

```powershell
cd C:\World\save-transfer
```

### 2. Install UV (if not already installed)

```powershell
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# Or via pip
pip install uv
```

### 3. Install Dependencies

```powershell
# Install all dependencies (runtime + dev)
uv sync

# Install only runtime dependencies (for production)
uv sync --no-dev
```

This reads `pyproject.toml` and installs:
- FastAPI
- Uvicorn
- Python-multipart
- Jinja2
- Loguru
- Dev tools (pytest, httpx, ruff)

---

## Running the Application

### Quick Start (Development Mode)

```powershell
# Run with UV (auto-detects pyproject.toml)
uv run uvicorn web_service.app:app --reload --host 127.0.0.1 --port 8000
```

**What this does**:
- Starts FastAPI server on http://127.0.0.1:8000
- `--reload`: Auto-restarts on code changes
- Serves both API and browser UI

### Alternative: Direct Python

```powershell
# Activate UV environment
.venv\Scripts\Activate.ps1

# Run the app
python -m web_service.app
```

### Open in Browser

Navigate to: **http://127.0.0.1:8000**

---

## Using the Tool

### Step 1: Prepare Your Save Files

1. Copy `Level.sav` and `Players/` folder from your Palworld save location:
   - **Host/Co-op**: `%localappdata%\Pal\Saved\SaveGames\<YOURID>\<WORLDID>\`
   - **Dedicated Server**: `steamapps\common\Palworld\Pal\Saved\SaveGames\0\<SERVERID>\`

2. Create a zip archive containing both:
   ```
   save.zip
   ├── Level.sav
   └── Players/
       ├── 00000000000000000000000000000001.sav
       ├── 1b31c53d000000000000000000000000.sav
       └── ...
   ```

### Step 2: Upload and Analyze

1. In the browser UI, click "**Choose File**" or drag-drop your `save.zip`
2. Click "**Analyze**"
3. Wait 2-5 seconds for player list to populate

### Step 3: Select Players

**Left Panel (Source Player)**:
- Select the **old character** from your original save
- This is the character whose progress you want to keep

**Right Panel (Target Player)**:
- Select the **new character** you just created in the game
- This character will be replaced with the old character's data

**Use search boxes** to filter by name or GUID.

### Step 4: Migrate

1. Click "**Migrate**" button (enabled only when both players selected)
2. Wait 5-10 seconds for processing
3. `migrated.zip` automatically downloads

### Step 5: Apply Changes

1. Extract `migrated.zip` to a temporary folder
2. Copy `Level.sav` and `Players/` from extracted folder
3. Paste into your actual save directory (overwrite existing)
4. Start Palworld and verify your character is intact!

---

## API Usage (Advanced)

### Analyze Save Archive

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@save.zip" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "players": [
    {
      "guid": "00000000000000000000000000000001",
      "name": "Tamil Gamers Tech",
      "guild_id": "99e60934-44f3-e515-2001-e7b71"
    },
    {
      "guid": "1b31c53d000000000000000000000000",
      "name": "Raptor",
      "guild_id": "99e60934-44f3-e515-2001-e7b71"
    }
  ],
  "archive_id": "abc123"
}
```

### Perform Migration

```bash
curl -X POST http://127.0.0.1:8000/migrate \
  -F "file=@save.zip" \
  -F "source_guid=00000000000000000000000000000001" \
  -F "target_guid=1b31c53d000000000000000000000000" \
  --output migrated.zip
```

---

## Configuration

### Change Port

```powershell
uv run uvicorn web_service.app:app --port 9000
```

### Increase File Size Limit

Edit `web_service/app.py`:
```python
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(
    # Add size limit middleware
    MaxSizeMiddleware,
    max_upload_size=1_000_000_000  # 1GB
)
```

### Enable CORS (for remote access)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for security
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Troubleshooting

### Issue: "Module not found: web_service.core"

**Cause**: Python can't find the web_service package.

**Fix**:
```powershell
# Ensure you're running from repository root
cd C:\World\save-transfer
uv run uvicorn web_service.app:app

# Or install in editable mode
uv pip install -e .
```

### Issue: "Level.sav not found in archive"

**Cause**: Zip structure incorrect.

**Fix**: Ensure `Level.sav` is at the root of the zip, not nested in subdirectories:
```
✅ Correct:
save.zip
├── Level.sav
└── Players/

❌ Incorrect:
save.zip
└── PalworldSave/
    ├── Level.sav
    └── Players/
```

### Issue: "Import errors from palworld_save_tools"

**Cause**: Module structure may have changed during migration.

**Fix**: 
```powershell
# Verify the core module structure
ls web_service/core/palworld_save_tools

# Check imports in migration.py
# Should be: from web_service.core.palworld_save_tools import ...
```

### Issue: "Port already in use"

**Cause**: Another process using port 8000.

**Fix**:
```powershell
# Kill existing process
Get-Process | Where-Object {$_.Path -like "*uvicorn*"} | Stop-Process

# Or use different port
uv run uvicorn web_service.app:app --port 8001
```

---

## Development

### Run Tests

```powershell
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=web_service --cov-report=html

# Run specific test file
uv run pytest web_service/tests/test_api.py
```

### Code Formatting & Linting

```powershell
# Format code
uv run ruff check --fix web_service/

# Check types (if using mypy)
uv run mypy web_service/
```

### Hot Reload Development

```powershell
# Uvicorn auto-reloads on file changes
uv run uvicorn web_service.app:app --reload
```

**Edit files** → **Save** → **Browser auto-refreshes**

---

## Project Structure

```
C:\World\save-transfer\
├── web_service/              # Self-contained web application
│   ├── app.py                # FastAPI server + routes
│   ├── models.py             # Pydantic data models
│   ├── core/                 # Migrated core logic (no GUI deps)
│   │   ├── migration.py      # GUID swap logic (refactored)
│   │   ├── save_parser.py    # Save file analysis
│   │   └── palworld_save_tools/  # Copied from gui_palworld_tool
│   │       ├── archive.py
│   │       ├── gvas.py
│   │       ├── palsav.py
│   │       └── ...
│   ├── static/               # CSS, JS, images
│   │   ├── styles.css
│   │   └── app.js
│   ├── templates/            # HTML templates
│   │   └── index.html
│   └── tests/
│       ├── test_api.py
│       ├── test_migration.py
│       └── fixtures/
├── pyproject.toml            # UV dependencies
├── uv.lock                   # Locked versions
└── specs/                    # Documentation
    └── master/
        ├── spec.md
        ├── plan.md
        ├── research.md
        ├── data-model.md
        ├── quickstart.md (this file)
        └── contracts/
            └── api.openapi.yaml

# NOTE: gui_palworld_tool/ will be removed after migration is complete
```

---

## Next Steps

- **Read the full spec**: [spec.md](./spec.md)
- **Understand the design**: [plan.md](./plan.md)
- **API reference**: [contracts/api.openapi.yaml](./contracts/api.openapi.yaml)
- **Contribute**: See development section above

---

## Support

- **GitHub Issues**: Report bugs or request features
- **Discord**: Contact `Pylar1991` for help
- **Documentation**: See [README.en.md](../../gui_palworld_tool/README.en.md) for background

---

## License

See [LICENSE](../../gui_palworld_tool/license) file in the original tool directory.
