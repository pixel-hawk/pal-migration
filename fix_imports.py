#!/usr/bin/env python3
"""Fix imports in palworld_save_tools to use relative imports."""

import os
from pathlib import Path

def fix_file(filepath):
    """Fix imports in a single Python file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace absolute imports with relative imports
    # Handle different import patterns based on file location
    
    # Determine relative depth based on file path
    parts = filepath.parts
    if 'palworld_save_tools' in parts:
        idx = parts.index('palworld_save_tools')
        depth = len(parts) - idx - 2  # -2 for palworld_save_tools and filename
        
        if depth == 0:  # Files in palworld_save_tools root
            replacements = [
                ('from palworld_save_tools.archive import', 'from .archive import'),
                ('from palworld_save_tools.gvas import', 'from .gvas import'),
                ('from palworld_save_tools.json_tools import', 'from .json_tools import'),
                ('from palworld_save_tools.palsav import', 'from .palsav import'),
                ('from palworld_save_tools.paltypes import', 'from .paltypes import'),
                ('from palworld_save_tools.compressor import', 'from .compressor import'),
                ('from palworld_save_tools.rawdata import', 'from .rawdata import'),
            ]
        else:  # Files in subdirectories
            replacements = [
                ('from palworld_save_tools.archive import', 'from ..archive import'),
                ('from palworld_save_tools.gvas import', 'from ..gvas import'),
                ('from palworld_save_tools.json_tools import', 'from ..json_tools import'),
                ('from palworld_save_tools.palsav import', 'from ..palsav import'),
                ('from palworld_save_tools.paltypes import', 'from ..paltypes import'),
                ('from palworld_save_tools.compressor import', 'from . import'),
                ('from palworld_save_tools.compressor.enums import', 'from .enums import'),
                ('from palworld_save_tools.compressor.oozlib import', 'from .oozlib import'),
                ('from palworld_save_tools.compressor.zlib import', 'from .zlib import'),
                ('from palworld_save_tools.commands.convert import', 'from .convert import'),
                ('from palworld_save_tools.rawdata import', 'from . import'),
                ('from palworld_save_tools.rawdata.common import', 'from .common import'),
            ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        # Handle wildcard imports
        if depth > 0:
            content = content.replace('from palworld_save_tools.archive import *', 'from ..archive import *')
            content = content.replace('from palworld_save_tools.archive import Any,', 'from ..archive import Any,')
        else:
            content = content.replace('from palworld_save_tools.archive import *', 'from .archive import *')
            content = content.replace('from palworld_save_tools.archive import Any,', 'from .archive import Any,')
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    return False

def main():
    base_dir = Path(__file__).parent / 'web_service' / 'core' / 'palworld_save_tools'
    
    count = 0
    for py_file in base_dir.rglob('*.py'):
        if fix_file(py_file):
            count += 1
    
    print(f"\nFixed {count} files")

if __name__ == '__main__':
    main()
