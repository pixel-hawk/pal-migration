import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List

# Ensure the original Assets folder is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "gui_palworld_tool" / "Assets"
if str(ASSETS_DIR) not in sys.path:
    sys.path.insert(0, str(ASSETS_DIR))

# Import functions from the original tool
try:
    import fix_host_save as fixmod
except Exception as e:
    raise ImportError(f"Could not import fix_host_save from Assets: {e}")

# The original tool uses tkinter messagebox dialogs (askyesno, showinfo) and simpledialogs.
# When running on a server/headless environment these would cause errors or hang.
# Monkeypatch common tkinter dialog functions to non-interactive defaults so fix_save
# runs non-interactively: respond 'No' to prompts and suppress info dialogs.
try:
    import tkinter as _tk
    try:
        _tk.messagebox.askyesno = lambda *a, **k: False
    except Exception:
        pass
    try:
        _tk.messagebox.showinfo = lambda *a, **k: None
    except Exception:
        pass
except Exception:
    # tkinter may not be available in the environment; ignore in that case
    pass


def _extract_to_temp(upload_path: str) -> str:
    """If upload_path is a zip file, extract it to a temp dir and return the folder.
    If it's a folder path, return it as-is."""
    if os.path.isfile(upload_path) and zipfile.is_zipfile(upload_path):
        tmpdir = tempfile.mkdtemp(prefix="pal_migrate_")
        with zipfile.ZipFile(upload_path, "r") as z:
            z.extractall(tmpdir)
        return tmpdir
    elif os.path.isdir(upload_path):
        return upload_path
    else:
        raise ValueError("Uploaded file must be a .zip of the save folder or a folder path")


def save_upload_bytes_to_file(file_bytes: bytes, filename: str = "upload.zip") -> str:
    tmp = tempfile.mkdtemp(prefix="pal_upload_")
    path = os.path.join(tmp, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path


def analyze_zip_bytes(file_bytes: bytes) -> List[str]:
    """Return the list of players found in the uploaded zip containing Level.sav + Players."""
    zip_path = save_upload_bytes_to_file(file_bytes, "upload.zip")
    extracted = _extract_to_temp(zip_path)
    # Try to find Level.sav in the extracted tree
    level_paths = []
    for root, dirs, files in os.walk(extracted):
        if "Level.sav" in files and "Players" in dirs:
            level_paths.append(root)
    if not level_paths:
        raise FileNotFoundError("Level.sav with Players folder not found in uploaded archive")
    # Use the first matching one
    folder = level_paths[0]
    players = fixmod.populate_player_lists(folder)
    # players is a list of strings like "UID - Name - guild"
    return players


def migrate_zip_bytes(file_bytes: bytes, old_guid: str, new_guid: str) -> bytes:
    """Run fix_save on the uploaded zip and return a zip bytes of the modified folder.

    old_guid and new_guid should be plain hex strings (no dashes)."""
    zip_path = save_upload_bytes_to_file(file_bytes, "upload.zip")
    extracted = _extract_to_temp(zip_path)
    # find the folder containing Level.sav
    level_paths = []
    for root, dirs, files in os.walk(extracted):
        if "Level.sav" in files and "Players" in dirs:
            level_paths.append(root)
    if not level_paths:
        raise FileNotFoundError("Level.sav with Players folder not found in uploaded archive")
    folder = level_paths[0]
    # Call the original fix_save logic
    fixmod.fix_save(folder, new_guid, old_guid)
    # After modification, zip the entire extracted folder and return bytes
    out_tmp = tempfile.mkdtemp(prefix="pal_out_")
    out_zip_path = os.path.join(out_tmp, "migrated.zip")
    shutil.make_archive(out_zip_path.replace('.zip', ''), 'zip', extracted)
    with open(out_zip_path, 'rb') as f:
        data = f.read()
    # Cleanup temp dirs if desired (left for debug)
    return data
