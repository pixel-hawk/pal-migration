# Palworld Save Migration Web Tool

Web-based tool for migrating Palworld saves between Host/Co-op and Dedicated Server modes by swapping player GUIDs.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)

### Installation

```powershell
# Clone or navigate to the repository
cd c:\World\save-transfer

# Install dependencies
uv sync --all-extras
```

### Running the Server

```powershell
# Start the web server
uv run uvicorn web_service.app:app --reload --host 127.0.0.1 --port 8000
```

Then open your browser to: **http://127.0.0.1:8000**

## 📖 Usage

1. **Upload**: Drag and drop or select your Palworld save `.zip` file
   - Must contain `Level.sav` and `Players/` folder
   - Maximum file size: 500MB

2. **Select Players**: Click to select source and target players from the dual-panel tables
   - Use search boxes to filter by GUID, name, or guild ID
   - Source: The player data you want to move FROM
   - Target: The player data you want to move TO

3. **Migrate**: Click the "✨ Migrate Players" button
   - The tool will swap the two player GUIDs in the save file
   - All ownership (pals, bases, items) is transferred

4. **Download**: The migrated save automatically downloads as `migrated.zip`
   - Extract the zip and replace your original save folder
   - **Always backup your saves first!**

## 🔒 Security Features

The tool includes comprehensive security validation:

- ✅ Path traversal protection (prevents `../` attacks)
- ✅ Absolute path rejection (prevents `/etc/passwd` or `C:\Windows` writes)
- ✅ File type whitelist (only `.sav` files allowed)
- ✅ Zip bomb protection (max 1GB extracted size)
- ✅ Resource exhaustion prevention (max 1000 files)

## ⚠️ Supported Save Formats

### ✅ Fully Supported
- **PLZ format** (Zlib compression) - Most common
- **CNK format** (Chunked Zlib) - Standard format

### ❌ Not Yet Supported
- **PLM format** (Oodle compression) - Requires `ooz` library

If you get an error about "Oodle compression" or "PLM format":

**Option 1**: Use a different save file (most Palworld saves use PLZ format)

**Option 2**: Add Oodle support (advanced)
1. Obtain the `ooz` library for your platform
2. Create `web_service/core/palworld_save_tools/lib/windows/` (or linux/mac)
3. Place the `ooz` binary files in that directory
4. Restart the server

## 🛠️ Development

### Project Structure

```
web_service/
├── app.py                  # FastAPI application
├── models.py               # Pydantic data models
├── core/
│   ├── security.py         # Security validation
│   ├── save_parser.py      # Player extraction
│   ├── migration.py        # GUID swap logic
│   └── palworld_save_tools/  # Save file library
├── static/
│   ├── styles.css          # Dark theme UI
│   └── app.js              # Frontend logic
└── templates/
    └── index.html          # Main page
```

### Running Tests

```powershell
# Run all tests
uv run pytest web_service/tests/

# Run with coverage
uv run pytest --cov=web_service web_service/tests/

# Linting
uv run ruff check web_service/
```

### API Endpoints

- `GET /` - Serve the web UI
- `GET /health` - Health check endpoint
- `POST /analyze` - Upload and analyze save file (returns player list)
- `POST /migrate` - Perform GUID migration and download result

See `specs/master/contracts/api.openapi.yaml` for full API documentation.

## 🐛 Troubleshooting

### "Oodle compression not supported"
Your save file uses PLM format. See "Supported Save Formats" above.

### "Invalid structure" error
Ensure your zip contains:
- `Level.sav` at root or one level deep
- `Players/` folder with at least one `.sav` file

### "File too large"
Maximum upload size is 500MB. Compress your save or contact support.

### "Source and target must be different"
You selected the same player twice. Select two different players to swap.

### Server won't start
1. Check Python version: `python --version` (must be 3.11+)
2. Reinstall dependencies: `uv sync --all-extras`
3. Check logs in `logs/web_service.log`

## 📚 Documentation

- [Feature Specification](specs/master/spec.md)
- [Implementation Plan](specs/master/plan.md)
- [API Contracts](specs/master/contracts/api.openapi.yaml)
- [Security Guidelines](specs/master/SECURITY.md)
- [Task Breakdown](specs/master/tasks.md)

## ⚡ Performance

- Upload analysis: < 5 seconds
- GUID migration: < 10 seconds
- UI interactions: < 100ms

Tested with saves up to 500MB containing 50+ players.

## 🙏 Credits

Based on the palworld_save_tools library from the gui_palworld_tool project.

Migration logic adapted from `fix_host_save.py` with tkinter dependencies removed for headless operation.

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🚨 Important Notes

- **Always backup your saves before migration!**
- Test the migrated save in a separate game instance first
- The tool performs a complete GUID swap (bidirectional)
- Guild memberships and ownership records are automatically updated
- Original uploaded files are never modified (migration works on copies)

## 🔗 Links

- Report issues: [GitHub Issues](https://github.com/your-repo/issues)
- Documentation: [Quickstart Guide](specs/master/quickstart.md)
- API Spec: [OpenAPI](specs/master/contracts/api.openapi.yaml)
