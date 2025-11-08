"""Security utilities for safe zip file handling.

This module implements critical security measures to prevent:
- Path traversal attacks (../../etc/passwd)
- Absolute path injection (/etc/passwd, C:\\Windows)
- Zip bombs (decompression bombs)
- Malicious file types (.exe, .dll, .sh)
- Resource exhaustion (too many files)

All zip files MUST be validated with validate_zip_safety() before extraction.
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Tuple

from loguru import logger


# Security constants
MAX_EXTRACTED_SIZE_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB
MAX_FILE_COUNT = 1000
ALLOWED_EXTENSIONS = {".sav"}  # Whitelist only .sav files
DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".sh", ".bat", ".ps1", ".cmd",
    ".msi", ".app", ".deb", ".rpm", ".apk", ".jar", ".com", ".scr"
}


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


def validate_zip_safety(zip_path: Path) -> Tuple[bool, str]:
    """Validate a zip file for security threats before extraction.
    
    Checks for:
    - Path traversal (../ in entry names)
    - Absolute paths (/, C:, etc.)
    - Dangerous file types
    - Zip bombs (excessive decompressed size)
    - Resource exhaustion (too many files)
    
    Args:
        zip_path: Path to the zip file to validate
        
    Returns:
        Tuple of (is_safe: bool, error_message: str or empty)
        
    Example:
        is_safe, error = validate_zip_safety(Path("upload.zip"))
        if not is_safe:
            raise SecurityError(error)
    """
    if not zip_path.exists():
        return False, f"Zip file not found: {zip_path}"
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Check 1: File count (prevent resource exhaustion)
            file_count = len(zf.namelist())
            if file_count > MAX_FILE_COUNT:
                return False, f"Too many files in archive: {file_count} (max {MAX_FILE_COUNT})"
            
            total_size = 0
            for info in zf.infolist():
                entry_name = info.filename
                
                # Check 2: Path traversal (../ or ..\)
                if ".." in entry_name:
                    return False, f"Path traversal detected in entry: {entry_name}"
                
                # Check 3: Absolute paths
                if entry_name.startswith('/') or entry_name.startswith('\\'):
                    return False, f"Absolute path detected in entry: {entry_name}"
                
                # Check for Windows drive letters (C:, D:, etc.)
                if len(entry_name) >= 2 and entry_name[1] == ':':
                    return False, f"Windows absolute path detected in entry: {entry_name}"
                
                # Check 4: Dangerous file types
                entry_path = Path(entry_name)
                extension = entry_path.suffix.lower()
                
                if extension in DANGEROUS_EXTENSIONS:
                    return False, f"Dangerous file type detected: {entry_name} ({extension})"
                
                # Skip directory entries for size calculation
                if not entry_name.endswith('/') and not entry_name.endswith('\\'):
                    # Only enforce whitelist for files (not directories)
                    if extension and extension not in ALLOWED_EXTENSIONS:
                        # Allow files without extensions (directories might appear as files)
                        if entry_path.name and '.' in entry_path.name:
                            return False, f"File type not allowed: {entry_name} (only .sav files permitted)"
                
                # Check 5: Zip bomb detection (decompressed size)
                total_size += info.file_size
                if total_size > MAX_EXTRACTED_SIZE_BYTES:
                    return False, f"Zip bomb detected: extracted size {total_size} bytes exceeds {MAX_EXTRACTED_SIZE_BYTES} bytes"
            
            logger.info(f"Zip validation passed: {file_count} files, {total_size} bytes decompressed")
            return True, ""
            
    except zipfile.BadZipFile:
        return False, "Invalid or corrupted zip file"
    except Exception as e:
        logger.error(f"Zip validation error: {e}")
        return False, f"Zip validation failed: {str(e)}"


def safe_extract_zip(zip_path: Path, extract_to: Path) -> Path:
    """Safely extract a zip file after security validation.
    
    Performs double-check validation during extraction to prevent
    race conditions or tampered zip files.
    
    Args:
        zip_path: Path to the validated zip file
        extract_to: Directory to extract files to (must not exist)
        
    Returns:
        Path to the extracted directory
        
    Raises:
        SecurityError: If validation fails
        ValueError: If extract_to already exists
        
    Example:
        extracted_path = safe_extract_zip(
            Path("upload.zip"),
            Path("/tmp/save_12345")
        )
    """
    # Pre-validation
    is_safe, error = validate_zip_safety(zip_path)
    if not is_safe:
        raise SecurityError(f"Zip validation failed: {error}")
    
    # Ensure extraction directory doesn't exist
    if extract_to.exists():
        raise ValueError(f"Extraction directory already exists: {extract_to}")
    
    # Create extraction directory
    extract_to.mkdir(parents=True, exist_ok=False)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for info in zf.infolist():
                # Double-check each entry during extraction
                entry_name = info.filename
                
                # Prevent path traversal
                if ".." in entry_name or entry_name.startswith('/') or entry_name.startswith('\\'):
                    raise SecurityError(f"Path traversal attempt during extraction: {entry_name}")
                
                # Construct safe extraction path
                extract_path = extract_to / entry_name
                
                # Ensure extracted path is within extract_to (final safety check)
                try:
                    extract_path.resolve().relative_to(extract_to.resolve())
                except ValueError:
                    raise SecurityError(f"Path traversal detected: {entry_name} escapes extraction directory")
                
                # Extract the file
                zf.extract(info, extract_to)
        
        logger.info(f"Safely extracted zip to: {extract_to}")
        return extract_to
        
    except SecurityError:
        # Clean up on security error
        cleanup_temp_directory(extract_to)
        raise
    except Exception as e:
        # Clean up on any error
        cleanup_temp_directory(extract_to)
        logger.error(f"Extraction failed: {e}")
        raise RuntimeError(f"Failed to extract zip: {str(e)}")


def cleanup_temp_directory(directory: Path) -> None:
    """Securely delete a temporary directory and all its contents.
    
    Args:
        directory: Path to directory to delete
        
    Example:
        cleanup_temp_directory(Path("/tmp/save_12345"))
    """
    if not directory.exists():
        logger.warning(f"Directory does not exist, skipping cleanup: {directory}")
        return
    
    try:
        shutil.rmtree(directory)
        logger.info(f"Cleaned up temporary directory: {directory}")
    except Exception as e:
        logger.error(f"Failed to cleanup directory {directory}: {e}")
        # Don't raise - cleanup failures shouldn't break the application
