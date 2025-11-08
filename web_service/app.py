"""FastAPI application for Palworld save migration web service.

Provides REST API endpoints for:
- Uploading save archives
- Analyzing and extracting player data
- Performing GUID migrations
- Downloading migrated saves
"""

import tempfile
import shutil
from pathlib import Path
from typing import Optional
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from web_service.models import (
    Player, ErrorResponse, AnalyzeResponse, MigrationResponse
)
from web_service.core.security import (
    validate_zip_safety, safe_extract_zip, cleanup_temp_directory, SecurityError
)
from web_service.core.save_parser import extract_players, validate_save_structure
from web_service.core.migration import migrate_guids


# Configure loguru
logger.add(
    "logs/web_service.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)

# Initialize FastAPI app
app = FastAPI(
    title="Palworld Save Migration Tool",
    description="Web-based tool for migrating Palworld saves between host/co-op and dedicated server",
    version="1.0.0"
)

# CORS middleware (localhost only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Temporary storage for uploaded files (in-memory cache)
# In production, consider using Redis or database
_upload_cache: dict[str, Path] = {}

# Constants
MAX_UPLOAD_SIZE = 524_288_000  # 500MB


@app.get("/", response_class=HTMLResponse)
async def serve_homepage(request: Request):
    """Serve the main HTML page with dual-panel player selection UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_save(file: UploadFile = File(...)):
    """Analyze uploaded save archive and extract player list.
    
    Steps:
    1. Validate file size (max 500MB)
    2. Save to temporary location
    3. Validate zip security (path traversal, zip bombs, etc.)
    4. Extract zip safely
    5. Validate save structure (Level.sav + Players/)
    6. Extract player data
    7. Return player list as JSON
    
    Returns:
        AnalyzeResponse with player list
        
    Raises:
        HTTPException 413: File too large
        HTTPException 400: Invalid structure or security violation
        HTTPException 422: Invalid file format
    """
    logger.info(f"Analyzing upload: {file.filename}")
    
    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error="INVALID_FILE_TYPE",
                message="Only .zip files are accepted",
                details={"filename": file.filename}
            ).model_dump()
        )
    
    # Create temp directory for this upload in the repo
    upload_id = str(uuid.uuid4())
    uploads_base = Path(__file__).parent / "uploads"
    uploads_base.mkdir(exist_ok=True)
    temp_dir = uploads_base / f"palworld_upload_{upload_id}"
    temp_dir.mkdir(exist_ok=True)
    zip_path = temp_dir / "upload.zip"
    logger.info(f"Upload directory: {temp_dir.absolute()}")
    
    try:
        # Save uploaded file
        logger.info(f"Saving upload to {zip_path}")
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=ErrorResponse(
                    error="FILE_TOO_LARGE",
                    message=f"File size {len(content)} bytes exceeds maximum {MAX_UPLOAD_SIZE} bytes (500MB)",
                    details={"size_bytes": len(content), "max_bytes": MAX_UPLOAD_SIZE}
                ).model_dump()
            )
        
        with open(zip_path, "wb") as f:
            f.write(content)
        
        # Security validation
        logger.info("Validating zip security...")
        is_safe, error_msg = validate_zip_safety(zip_path)
        if not is_safe:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="SECURITY_VIOLATION",
                    message=error_msg,
                    details={"filename": file.filename}
                ).model_dump()
            )
        
        # Extract zip
        logger.info("Extracting zip archive...")
        extract_dir = temp_dir / "extracted"
        try:
            safe_extract_zip(zip_path, extract_dir)
        except SecurityError as e:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="EXTRACTION_FAILED",
                    message=str(e),
                    details={"filename": file.filename}
                ).model_dump()
            )
        
        # Find the save directory (might be one level deep)
        save_dir = extract_dir
        if not (extract_dir / "Level.sav").exists():
            # Check subdirectories
            subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if len(subdirs) == 1 and (subdirs[0] / "Level.sav").exists():
                save_dir = subdirs[0]
        
        # Validate save structure
        logger.info("Validating save structure...")
        is_valid, error_msg = validate_save_structure(save_dir)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="INVALID_STRUCTURE",
                    message=error_msg,
                    details={"filename": file.filename}
                ).model_dump()
            )
        
        # Extract players
        logger.info("Extracting player data...")
        players = extract_players(save_dir)
        
        # Convert to Pydantic models
        player_models = [
            Player(guid=p.guid, name=p.name, guild_id=p.guild_id)
            for p in players
        ]
        
        # Cache the extracted directory for migration
        _upload_cache[upload_id] = save_dir
        
        logger.info(f"Analysis complete: {len(player_models)} players found")
        
        return AnalyzeResponse(
            success=True,
            players=player_models,
            message=f"Found {len(player_models)} players in save file"
        )
    
    except HTTPException:
        # Clean up on error
        cleanup_temp_directory(temp_dir)
        raise
    except Exception as e:
        # Clean up on unexpected error
        cleanup_temp_directory(temp_dir)
        logger.error(f"Unexpected error during analysis: {e}")
        
        # Check if it's an Oodle compression error
        error_str = str(e)
        if "PLM format" in error_str or "Oodle" in error_str or "ooz library" in error_str:
            raise HTTPException(
                status_code=422,
                detail=ErrorResponse(
                    error="UNSUPPORTED_COMPRESSION",
                    message="This save file uses Oodle compression (PLM format) which is not currently supported.",
                    details={
                        "filename": file.filename,
                        "reason": "Missing ooz library",
                        "solution": "Please use a save file with standard compression (PLZ/CNK format), or contact the developer for Oodle support instructions."
                    }
                ).model_dump()
            )
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=f"Failed to analyze save file: {str(e)}",
                details={"filename": file.filename}
            ).model_dump()
        )


@app.post("/migrate")
async def migrate_save(
    file: UploadFile = File(...),
    mappings_json: str = Form(...)
):
    """Perform batch GUID migration and return migrated save as downloadable zip.
    
    Steps:
    1. Validate and extract uploaded save (reuse analyze logic)
    2. Validate all source and target GUIDs exist
    3. Perform batch migration
    4. Create new zip archive
    5. Stream zip file to client
    6. Clean up temporary files
    
    Args:
        file: Uploaded save archive (.zip)
        mappings_json: JSON array of {"source_guid": "...", "target_guid": "..."} objects
        
    Returns:
        StreamingResponse with migrated.zip
        
    Raises:
        HTTPException 400: Invalid GUIDs, conflicts, or save structure
        HTTPException 404: GUID not found in save
        HTTPException 500: Migration failed
        
    Example mappings_json:
        [{"source_guid": "00...01", "target_guid": "1B...00"},
         {"source_guid": "00...02", "target_guid": "2A...00"}]
    """
    import json
    from web_service.models import MigrationRequest, GuidMapping
    
    # Parse and validate mappings
    try:
        mappings_data = json.loads(mappings_json)
        # Convert to GuidMapping objects for validation
        guid_mappings = [GuidMapping(**m) for m in mappings_data]
        # Validate with MigrationRequest
        migration_req = MigrationRequest(mappings=guid_mappings)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="INVALID_JSON",
                message=f"Invalid JSON in mappings: {str(e)}",
                details={}
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="INVALID_MAPPINGS",
                message=str(e),
                details={}
            ).model_dump()
        )
    
    logger.info(f"Batch migration request with {len(guid_mappings)} mappings")
    
    # Create temp directory in the repo
    upload_id = str(uuid.uuid4())
    uploads_base = Path(__file__).parent / "uploads"
    uploads_base.mkdir(exist_ok=True)
    temp_dir = uploads_base / f"palworld_migrate_{upload_id}"
    temp_dir.mkdir(exist_ok=True)
    zip_path = temp_dir / "upload.zip"
    logger.info(f"Migration directory: {temp_dir.absolute()}")
    
    try:
        # Save uploaded file
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 500MB)")
        
        with open(zip_path, "wb") as f:
            f.write(content)
        
        # Security validation (reuse from analyze)
        is_safe, error_msg = validate_zip_safety(zip_path)
        if not is_safe:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="SECURITY_VIOLATION",
                    message=error_msg
                ).model_dump()
            )
        
        # Extract zip
        extract_dir = temp_dir / "extracted"
        safe_extract_zip(zip_path, extract_dir)
        
        # Find save directory
        save_dir = extract_dir
        if not (extract_dir / "Level.sav").exists():
            subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if len(subdirs) == 1 and (subdirs[0] / "Level.sav").exists():
                save_dir = subdirs[0]
        
        # Validate all GUIDs exist in save
        players = extract_players(save_dir)
        player_guids = {p.guid for p in players}
        
        # Check all mappings
        for mapping in guid_mappings:
            source = mapping.source_guid.upper().replace('-', '')
            target = mapping.target_guid.upper().replace('-', '')
            
            if source not in player_guids:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error="GUID_NOT_FOUND",
                        message=f"Source GUID {source} not found in save file",
                        details={"guid": source, "available_guids": list(player_guids)}
                    ).model_dump()
                )
            
            if target not in player_guids:
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error="GUID_NOT_FOUND",
                        message=f"Target GUID {target} not found in save file",
                        details={"guid": target, "available_guids": list(player_guids)}
                    ).model_dump()
                )
        
        # Perform batch migration
        from web_service.core.migration import migrate_guids_batch
        
        logger.info("Performing batch GUID migration...")
        mappings_list = [
            (m.source_guid.upper().replace('-', ''), m.target_guid.upper().replace('-', ''))
            for m in guid_mappings
        ]
        
        success_count = migrate_guids_batch(
            save_directory=save_dir,
            mappings=mappings_list,
            guild_fix=True,
            create_backup=False  # No backup in temp directory
        )
        
        logger.info(f"Batch migration result: {success_count}/{len(mappings_list)} successful")
        
        # Create output zip
        logger.info("Creating migrated archive...")
        output_zip_path = temp_dir / "migrated.zip"
        shutil.make_archive(
            str(output_zip_path.with_suffix('')),
            'zip',
            save_dir
        )
        
        logger.info("Migration complete, streaming zip file...")
        
        # Stream the zip file
        def iterfile():
            with open(output_zip_path, 'rb') as f:
                yield from f
        
        response = StreamingResponse(
            iterfile(),
            media_type='application/zip',
            headers={
                'Content-Disposition': 'attachment; filename="migrated.zip"'
            }
        )
        
        # Note: Cleanup happens after response is sent (FastAPI handles this)
        # In production, use background tasks for cleanup
        
        return response
    
    except HTTPException:
        cleanup_temp_directory(temp_dir)
        raise
    except Exception as e:
        cleanup_temp_directory(temp_dir)
        logger.error(f"Migration failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="MIGRATION_FAILED",
                message=f"Migration failed: {str(e)}"
            ).model_dump()
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
