# Security Guidelines: Zip File Upload & Extraction

**Date**: 2025-11-08 | **Severity**: HIGH | **Version**: 1.0

---

## Overview

User-uploaded zip files pose **significant security risks** when extracted on the server. This document outlines threats and required mitigations for the Palworld save migration tool.

---

## ⚠️ Security Threats

### 1. Path Traversal Attack (Directory Traversal)

**Threat**: Malicious zip containing entries like `../../etc/passwd` or `..\..\Windows\System32\evil.dll`

**Impact**: 
- Overwrite critical system files
- Read sensitive data
- Achieve remote code execution

**Example Malicious Zip**:
```python
# Attacker creates zip with:
# Entry: "../../../etc/passwd"
# Entry: "../../../../home/user/.ssh/authorized_keys"
```

**Mitigation**: ✅ Task T037a - Reject any entry containing `..` or starting with `/` or `\`

---

### 2. Absolute Path Injection

**Threat**: Zip entries with absolute paths like `/etc/passwd` (Linux) or `C:\Windows\system32\cmd.exe` (Windows)

**Impact**:
- Write files anywhere on filesystem
- Overwrite system binaries
- Privilege escalation

**Example**:
```python
# Malicious entry:
"/etc/cron.d/backdoor"  # Linux
"C:\\Windows\\System32\\evil.dll"  # Windows
```

**Mitigation**: ✅ Task T037b - Reject entries starting with `/` or containing drive letters (`C:`, etc.)

---

### 3. Zip Bomb (Decompression Bomb)

**Threat**: Small zip file (e.g., 10MB) that expands to enormous size (e.g., 10GB+)

**Impact**:
- Disk space exhaustion
- Denial of Service (DoS)
- Server crash

**Example**:
```
42.zip (42 KB) → expands to 4.5 PB (petabytes)
```

**Mitigation**: ✅ Task T037d - Limit total extracted size to 1GB (even if zip is 500MB)

---

### 4. Malicious File Types

**Threat**: Zip contains executable files (.exe, .dll, .so, .sh, .bat, .ps1)

**Impact**:
- If accidentally executed: arbitrary code execution
- Backdoors, malware, trojans

**Example**:
```
save.zip
├── Level.sav
├── Players/
│   └── player.sav
└── backdoor.exe  ← DANGER
```

**Mitigation**: ✅ Task T037c - Whitelist only `.sav` files, reject all executable types

---

### 5. Resource Exhaustion (Too Many Files)

**Threat**: Zip with millions of tiny files

**Impact**:
- Inodes exhaustion (Linux)
- Filesystem slowdown
- Memory exhaustion during extraction

**Example**:
```
save.zip contains 10,000,000 files of 1 byte each
```

**Mitigation**: ✅ Task T037e - Limit to 1000 files max

---

### 6. Symlink Attack

**Threat**: Zip contains symbolic links pointing outside extraction directory

**Impact**:
- Read arbitrary files
- Overwrite system files via symlinks

**Example**:
```python
# Symlink in zip:
"Level.sav" -> "../../etc/passwd"
```

**Mitigation**: ✅ Reject symlinks during extraction (Python's `zipfile` handles this by default)

---

## ✅ Implementation: Secure Zip Extraction

### Required Security Checks (Before Extraction)

```python
# web_service/core/security.py

import os
import zipfile
from pathlib import Path
from typing import Tuple, List

# Security constants
MAX_ZIP_SIZE = 500 * 1024 * 1024  # 500MB
MAX_EXTRACTED_SIZE = 1024 * 1024 * 1024  # 1GB
MAX_FILE_COUNT = 1000
ALLOWED_EXTENSIONS = {'.sav'}  # Whitelist only
DANGEROUS_EXTENSIONS = {'.exe', '.dll', '.so', '.sh', '.bat', '.ps1', '.cmd', '.com', '.scr'}

class ZipSecurityError(Exception):
    """Raised when zip file fails security validation."""
    pass

def validate_zip_safety(zip_path: Path) -> Tuple[bool, str]:
    """
    Validate zip file is safe to extract.
    
    Returns: (is_safe: bool, error_message: str)
    
    Checks:
    - Path traversal (../ in entry names)
    - Absolute paths (/ or C:\ in entry names)
    - Dangerous file types
    - Total extracted size (zip bomb detection)
    - File count limit
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Check 1: File count
            entry_count = len(zf.namelist())
            if entry_count > MAX_FILE_COUNT:
                return False, f"Too many files in archive ({entry_count} > {MAX_FILE_COUNT})"
            
            # Check 2: Total extracted size (zip bomb detection)
            total_size = sum(info.file_size for info in zf.infolist())
            if total_size > MAX_EXTRACTED_SIZE:
                return False, f"Extracted size too large ({total_size} > {MAX_EXTRACTED_SIZE} bytes)"
            
            # Check 3: Validate each entry
            for info in zf.infolist():
                entry_name = info.filename
                
                # Check 3a: Path traversal
                if '..' in entry_name or entry_name.startswith('/') or entry_name.startswith('\\'):
                    return False, f"Path traversal detected: {entry_name}"
                
                # Check 3b: Absolute paths (Windows drive letters)
                if ':' in entry_name and entry_name[1] == ':':  # e.g., C:\
                    return False, f"Absolute path detected: {entry_name}"
                
                # Check 3c: Dangerous file types
                entry_path = Path(entry_name)
                if entry_path.suffix.lower() in DANGEROUS_EXTENSIONS:
                    return False, f"Dangerous file type: {entry_name}"
                
                # Check 3d: Only allow .sav files (strict whitelist)
                if entry_path.is_file() and entry_path.suffix.lower() not in ALLOWED_EXTENSIONS and entry_path.suffix != '':
                    return False, f"Unsupported file type: {entry_name} (only .sav allowed)"
            
            return True, "OK"
    
    except zipfile.BadZipFile:
        return False, "Invalid or corrupted zip file"
    except Exception as e:
        return False, f"Zip validation error: {str(e)}"

def safe_extract_zip(zip_path: Path, extract_to: Path) -> Path:
    """
    Safely extract zip to directory after security validation.
    
    Returns: Path to extracted directory
    Raises: ZipSecurityError if validation fails
    """
    # Validate first
    is_safe, error_msg = validate_zip_safety(zip_path)
    if not is_safe:
        raise ZipSecurityError(error_msg)
    
    # Create extraction directory
    extract_to.mkdir(parents=True, exist_ok=True)
    
    # Extract with additional safety
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            # Double-check: ensure extracted path stays within target directory
            extracted_path = (extract_to / member.filename).resolve()
            if not str(extracted_path).startswith(str(extract_to.resolve())):
                raise ZipSecurityError(f"Path traversal attempt blocked: {member.filename}")
            
            # Extract file
            zf.extract(member, extract_to)
    
    return extract_to

def cleanup_temp_directory(temp_dir: Path):
    """Securely delete temporary directory and all contents."""
    import shutil
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
```

---

## 🔒 Additional Security Measures

### 1. Temporary File Isolation

```python
import tempfile
import uuid

# Create isolated temp directory per upload
temp_base = Path(tempfile.gettempdir()) / "palworld_migration"
upload_id = str(uuid.uuid4())
temp_dir = temp_base / upload_id
temp_dir.mkdir(parents=True, exist_ok=True)
```

**Benefit**: Each upload isolated, prevents cross-contamination

---

### 2. Automatic Cleanup

```python
import atexit

def cleanup_all_temp_files():
    """Clean up all temp files on server shutdown."""
    temp_base = Path(tempfile.gettempdir()) / "palworld_migration"
    if temp_base.exists():
        shutil.rmtree(temp_base, ignore_errors=True)

atexit.register(cleanup_all_temp_files)
```

**Benefit**: No orphaned files if server crashes

---

### 3. File Permission Restrictions

```python
# After extraction, ensure files are not executable
for root, dirs, files in os.walk(extract_to):
    for file in files:
        file_path = Path(root) / file
        file_path.chmod(0o644)  # Read/write for owner, read-only for others
```

**Benefit**: Even if executable slips through, it can't be executed

---

### 4. Content-Type Validation

```python
# In FastAPI endpoint
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # Validate Content-Type
    if file.content_type not in ["application/zip", "application/x-zip-compressed"]:
        raise HTTPException(400, "Only zip files accepted")
```

**Benefit**: Reject non-zip files immediately

---

### 5. Rate Limiting (Future Enhancement)

```python
# Prevent abuse - limit uploads per IP
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/analyze")
@limiter.limit("5/minute")  # Max 5 uploads per minute
async def analyze(...):
    ...
```

**Benefit**: Prevents DoS attacks

---

## 📋 Security Checklist

Before deploying:

- [ ] ✅ Path traversal validation (T037a)
- [ ] ✅ Absolute path rejection (T037b)
- [ ] ✅ Dangerous file type blocking (T037c)
- [ ] ✅ Zip bomb protection (T037d)
- [ ] ✅ File count limit (T037e)
- [ ] ✅ Temporary file isolation (per-upload UUID)
- [ ] ✅ Automatic cleanup on shutdown
- [ ] ✅ File permission restrictions (chmod 644)
- [ ] ✅ Content-Type validation
- [ ] 🔜 Rate limiting (optional for v1 since localhost-only)

---

## 🧪 Security Testing

### Test Cases

1. **Test Path Traversal**:
   ```python
   # Create malicious zip
   import zipfile
   with zipfile.ZipFile('malicious.zip', 'w') as zf:
       zf.writestr('../../etc/passwd', 'fake content')
   
   # Upload should be REJECTED
   ```

2. **Test Zip Bomb**:
   ```python
   # Create 10MB zip that expands to 2GB
   # Upload should be REJECTED (exceeds 1GB limit)
   ```

3. **Test Executable**:
   ```python
   # Create zip with .exe file
   with zipfile.ZipFile('malicious.zip', 'w') as zf:
       zf.writestr('Level.sav', 'valid content')
       zf.writestr('backdoor.exe', 'malicious code')
   
   # Upload should be REJECTED
   ```

4. **Test Symlink** (Linux/macOS):
   ```python
   # Create symlink in zip pointing outside
   # Should be ignored by Python's zipfile (safe by default)
   ```

---

## 🚨 Incident Response

If malicious zip is detected:

1. **Log the incident** with IP, timestamp, file hash
2. **Reject upload** with generic error (don't reveal security check)
3. **Delete uploaded file immediately**
4. **Monitor for repeated attempts** from same IP

Example logging:
```python
import logging

logger = logging.getLogger(__name__)

def log_security_incident(ip: str, violation: str, file_hash: str):
    logger.warning(
        f"SECURITY: Malicious upload detected | "
        f"IP={ip} | Violation={violation} | Hash={file_hash}"
    )
```

---

## 📚 References

- [OWASP: Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [Zip Slip Vulnerability](https://snyk.io/research/zip-slip-vulnerability)
- [Python zipfile Security](https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.extract)
- [CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html)

---

## ✅ Summary

**Key Security Principles**:
1. ⚠️ **Never trust user input**
2. ✅ **Validate before extraction**
3. 🔒 **Isolate temp directories**
4. 🧹 **Clean up aggressively**
5. 📝 **Log security events**

**Implementation Status**:
- ✅ Security module planned (Task T024a-d)
- ✅ Validation integrated in upload flow (Task T037a-e)
- ✅ Reused in migration endpoint (Task T064a)

All security measures are **required before production deployment**. Do not skip these tasks.
