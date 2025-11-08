"""Pydantic models for API request/response validation."""

import re
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Player(BaseModel):
    """Represents a Palworld player character."""
    
    guid: str = Field(
        ...,
        min_length=32,
        max_length=32,
        description="32-character hex GUID without dashes"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Player display name"
    )
    guild_id: str = Field(
        ...,
        description="Guild instance ID"
    )
    
    @field_validator('guid')
    @classmethod
    def validate_guid_format(cls, v: str) -> str:
        """Validate GUID is 32 hexadecimal characters."""
        if not re.match(r'^[0-9A-Fa-f]{32}$', v):
            raise ValueError('GUID must be 32 hexadecimal characters')
        return v.upper()
    
    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validate name is not whitespace only."""
        if not v.strip():
            raise ValueError('Player name cannot be empty or whitespace only')
        return v


class SaveArchive(BaseModel):
    """Represents an uploaded save file archive."""
    
    filename: str = Field(..., description="Original upload filename")
    size_bytes: int = Field(
        ...,
        gt=0,
        le=524_288_000,  # 500MB
        description="File size in bytes (max 500MB)"
    )
    temp_path: Optional[str] = Field(
        None,
        description="Server temp path (internal use)"
    )
    players: Optional[List[Player]] = Field(
        default_factory=list,
        description="Extracted players"
    )


class GuidMapping(BaseModel):
    """Single GUID mapping pair."""
    
    source_guid: str = Field(
        ...,
        pattern=r'^[0-9A-Fa-f]{32}$',
        description="Source player GUID (32 hex chars)"
    )
    target_guid: str = Field(
        ...,
        pattern=r'^[0-9A-Fa-f]{32}$',
        description="Target player GUID (32 hex chars)"
    )
    
    @model_validator(mode='after')
    def validate_guids_differ(self):
        """Ensure source and target GUIDs are different."""
        if self.source_guid.upper() == self.target_guid.upper():
            raise ValueError('Source and target GUIDs must be different')
        return self


class MigrationRequest(BaseModel):
    """Request payload for GUID migration (supports batch)."""
    
    mappings: List[GuidMapping] = Field(
        ...,
        min_length=1,
        description="List of GUID mappings to perform"
    )
    
    @model_validator(mode='after')
    def validate_no_conflicts(self):
        """Ensure no GUID is used as both source and target, and no duplicates."""
        sources = [m.source_guid.upper() for m in self.mappings]
        targets = [m.target_guid.upper() for m in self.mappings]
        
        # Check for duplicate sources
        if len(sources) != len(set(sources)):
            raise ValueError('Each source GUID can only be used once')
        
        # Check for duplicate targets
        if len(targets) != len(set(targets)):
            raise ValueError('Each target GUID can only be used once')
        
        # Check for conflicts (GUID used as both source and target)
        conflicts = set(sources) & set(targets)
        if conflicts:
            raise ValueError(f'GUIDs cannot be both source and target: {conflicts}')
        
        return self


class MigrationResponse(BaseModel):
    """Response payload after migration."""
    
    success: bool = Field(..., description="Whether migration succeeded")
    message: str = Field(..., description="Human-readable status message")
    download_url: Optional[str] = Field(
        None,
        description="URL to download migrated zip (if success=True)"
    )
    migrated_players: Optional[List[Player]] = Field(
        None,
        description="Updated player list with swapped GUIDs"
    )


class ErrorResponse(BaseModel):
    """Standardized error response."""
    
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context"
    )


class AnalyzeResponse(BaseModel):
    """Response from /analyze endpoint with extracted players."""
    
    success: bool = Field(..., description="Whether analysis succeeded")
    players: List[Player] = Field(..., description="Extracted player list")
    message: str = Field(default="", description="Optional message")
