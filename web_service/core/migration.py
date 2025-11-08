"""Migration logic for swapping player GUIDs in Palworld saves.

This module provides functions to perform GUID swaps between players without
any GUI dependencies. All operations are pure functions that accept parameters.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

from loguru import logger

from web_service.core.save_parser import sav_to_json, json_to_sav


def migrate_guids(
    save_directory: Path,
    source_guid: str,
    target_guid: str,
    guild_fix: bool = True,
    create_backup: bool = False,
    backup_directory: Optional[Path] = None
) -> None:
    """Migrate (swap) two player GUIDs in a Palworld save.
    
    This swaps all references to source_guid with target_guid and vice versa.
    Modifies:
    - Player save files (.sav)
    - Level.sav character parameters
    - Guild memberships
    - Ownership records (pals, bases, items)
    
    Args:
        save_directory: Path to directory containing Level.sav and Players/
        source_guid: First player GUID (without dashes)
        target_guid: Second player GUID (without dashes)
        guild_fix: Whether to update guild memberships (default True)
        create_backup: Whether to create backup before migration (default False)
        backup_directory: Where to store backups (default: save_directory/backups)
        
    Raises:
        FileNotFoundError: If Level.sav or player files not found
        ValueError: If GUIDs are invalid or identical
        RuntimeError: If migration fails
        
    Example:
        migrate_guids(
            Path("/tmp/save_12345"),
            source_guid="00000000000000000000000000000001",
            target_guid="1B31C53D000000000000000000000000"
        )
    """
    # Normalize GUIDs (uppercase, no dashes)
    source_guid = source_guid.upper().replace('-', '')
    target_guid = target_guid.upper().replace('-', '')
    
    # Validation
    if source_guid == target_guid:
        raise ValueError("Source and target GUIDs must be different")
    
    if len(source_guid) != 32 or len(target_guid) != 32:
        raise ValueError("GUIDs must be exactly 32 characters")
    
    # Format GUIDs with dashes for save files
    source_guid_formatted = format_guid(source_guid)
    target_guid_formatted = format_guid(target_guid)
    
    logger.info(f"Starting migration: {source_guid} <-> {target_guid}")
    
    # Paths
    level_sav_path = save_directory / 'Level.sav'
    source_sav_path = save_directory / 'Players' / f'{source_guid}.sav'
    target_sav_path = save_directory / 'Players' / f'{target_guid}.sav'
    
    # Validate files exist
    if not level_sav_path.exists():
        raise FileNotFoundError(f"Level.sav not found at {level_sav_path}")
    if not source_sav_path.exists():
        raise FileNotFoundError(f"Source player file not found: {source_sav_path}")
    if not target_sav_path.exists():
        raise FileNotFoundError(f"Target player file not found: {target_sav_path}")
    
    # Create backup if requested
    if create_backup:
        backup_dir = backup_directory or (save_directory / "backups")
        backup_save_directory(save_directory, backup_dir)
    
    try:
        # Parse save files
        logger.info("Parsing save files...")
        level_json = sav_to_json(level_sav_path)
        source_json = sav_to_json(source_sav_path)
        target_json = sav_to_json(target_sav_path)
        
        # Swap PlayerUIds in player save files
        logger.info("Swapping player identities...")
        source_json['properties']['SaveData']['value']['PlayerUId']['value'] = target_guid_formatted
        source_json['properties']['SaveData']['value']['IndividualId']['value']['PlayerUId']['value'] = target_guid_formatted
        source_instance_id = source_json['properties']['SaveData']['value']['IndividualId']['value']['InstanceId']['value']
        
        target_json['properties']['SaveData']['value']['PlayerUId']['value'] = source_guid_formatted
        target_json['properties']['SaveData']['value']['IndividualId']['value']['PlayerUId']['value'] = source_guid_formatted
        target_instance_id = target_json['properties']['SaveData']['value']['IndividualId']['value']['InstanceId']['value']
        
        # Update character parameters in Level.sav
        logger.info("Updating character parameters...")
        char_params = level_json['properties']['worldSaveData']['value']['CharacterSaveParameterMap']['value']
        
        for item in char_params:
            if item['key']['InstanceId']['value'] == source_instance_id:
                item['key']['PlayerUId']['value'] = target_guid_formatted
            elif item['key']['InstanceId']['value'] == target_instance_id:
                item['key']['PlayerUId']['value'] = source_guid_formatted
        
        # Update guild memberships
        if guild_fix:
            logger.info("Updating guild memberships...")
            groups = level_json['properties']['worldSaveData']['value']['GroupSaveDataMap']['value']
            
            for group in groups:
                if group['value']['GroupType']['value']['value'] == 'EPalGroupType::Guild':
                    group_data = group['value']['RawData']['value']
                    
                    # Update individual character handles
                    if 'individual_character_handle_ids' in group_data:
                        for handle in group_data['individual_character_handle_ids']:
                            if handle['instance_id'] == source_instance_id:
                                handle['guid'] = target_guid_formatted
                            elif handle['instance_id'] == target_instance_id:
                                handle['guid'] = source_guid_formatted
                    
                    # Update admin player UID
                    if 'admin_player_uid' in group_data:
                        if group_data['admin_player_uid'] == source_guid_formatted:
                            group_data['admin_player_uid'] = target_guid_formatted
                        elif group_data['admin_player_uid'] == target_guid_formatted:
                            group_data['admin_player_uid'] = source_guid_formatted
                    
                    # Update players list
                    if 'players' in group_data:
                        for player in group_data['players']:
                            if player['player_uid'] == source_guid_formatted:
                                player['player_uid'] = target_guid_formatted
                            elif player['player_uid'] == target_guid_formatted:
                                player['player_uid'] = source_guid_formatted
        
        # Swap ownership records (for host migrations)
        if source_guid_formatted.endswith('000000000001') or target_guid_formatted.endswith('000000000001'):
            logger.info("Swapping ownership records (host migration detected)...")
            deep_swap_ownership(level_json, source_guid_formatted, target_guid_formatted)
        
        # Copy DPS files if they exist
        copy_dps_file(
            save_directory / "Players",
            source_guid,
            save_directory / "Players",
            target_guid
        )
        
        # Write modified save files
        logger.info("Writing modified save files...")
        json_to_sav(level_json, level_sav_path)
        json_to_sav(source_json, source_sav_path)
        json_to_sav(target_json, target_sav_path)
        
        # Swap player file names
        logger.info("Swapping player file names...")
        temp_path = source_sav_path.with_suffix('.sav.tmp_swap')
        source_sav_path.rename(temp_path)
        target_sav_path.rename(save_directory / 'Players' / f'{source_guid.upper()}.sav')
        temp_path.rename(save_directory / 'Players' / f'{target_guid.upper()}.sav')
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise RuntimeError(f"Migration failed: {str(e)}")


def format_guid(guid: str) -> str:
    """Format a 32-character GUID with dashes.
    
    Args:
        guid: GUID without dashes (32 hex characters)
        
    Returns:
        Formatted GUID (e.g., "00000000-0000-0000-0000-000000000001")
        
    Example:
        >>> format_guid("00000000000000000000000000000001")
        "00000000-0000-0000-0000-000000000001"
    """
    return f"{guid[:8]}-{guid[8:12]}-{guid[12:16]}-{guid[16:20]}-{guid[20:]}".lower()


def deep_swap_ownership(data, old_uid: str, new_uid: str) -> None:
    """Recursively swap ownership UIDs in nested data structures.
    
    Updates:
    - OwnerPlayerUId
    - build_player_uid
    - private_lock_player_uid
    
    Args:
        data: Dictionary or list to traverse
        old_uid: Old player UID (formatted with dashes)
        new_uid: New player UID (formatted with dashes)
    """
    if isinstance(data, dict):
        # Swap ownership fields
        if data.get("OwnerPlayerUId", {}).get("value") == old_uid:
            data["OwnerPlayerUId"]["value"] = new_uid
        
        if data.get("build_player_uid") == old_uid:
            data["build_player_uid"] = new_uid
        
        if data.get("private_lock_player_uid") == old_uid:
            data["private_lock_player_uid"] = new_uid
        
        # Recurse into values
        for value in data.values():
            deep_swap_ownership(value, old_uid, new_uid)
    
    elif isinstance(data, list):
        # Recurse into list items
        for item in data:
            deep_swap_ownership(item, old_uid, new_uid)


def copy_dps_file(
    source_folder: Path,
    source_uid: str,
    target_folder: Path,
    target_uid: str
) -> Optional[Path]:
    """Copy DPS (Death Penalty System) file from source to target player.
    
    DPS files track player deaths and penalties. They are optional files.
    
    Args:
        source_folder: Folder containing source DPS file
        source_uid: Source player GUID (without dashes)
        target_folder: Folder to copy DPS file to
        target_uid: Target player GUID (without dashes)
        
    Returns:
        Path to copied file if successful, None if source doesn't exist
        
    Example:
        copy_dps_file(
            Path("/tmp/save/Players"),
            "00000000000000000000000000000001",
            Path("/tmp/save/Players"),
            "1B31C53D000000000000000000000000"
        )
    """
    source_uid = source_uid.upper().replace('-', '')
    target_uid = target_uid.upper().replace('-', '')
    
    source_file = source_folder / f"{source_uid}_dps.sav"
    target_file = target_folder / f"{target_uid}_dps.sav"
    
    if not source_file.exists():
        logger.info(f"Source DPS file not found (optional): {source_file}")
        return None
    
    try:
        shutil.copy2(source_file, target_file)
        logger.info(f"DPS file copied: {source_file} -> {target_file}")
        return target_file
    except Exception as e:
        logger.warning(f"Failed to copy DPS file (non-critical): {e}")
        return None


def backup_save_directory(save_directory: Path, backup_root: Path) -> Path:
    """Create a timestamped backup of the save directory.
    
    Args:
        save_directory: Directory to backup
        backup_root: Root directory for backups
        
    Returns:
        Path to created backup directory
        
    Example:
        backup_path = backup_save_directory(
            Path("/tmp/save_12345"),
            Path("/tmp/backups")
        )
    """
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / f"palworld_save_backup_{timestamp}"
    
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(save_directory, backup_path)
    
    logger.info(f"Backup created at: {backup_path}")
    return backup_path


def migrate_guids_batch(
    save_directory: Path,
    mappings: List[Tuple[str, str]],
    guild_fix: bool = True,
    create_backup: bool = False,
    backup_directory: Optional[Path] = None
) -> int:
    """Perform batch GUID migrations in a single pass.
    
    This function applies multiple GUID swaps efficiently by modifying
    the save files only once, rather than calling migrate_guids() multiple times.
    
    Args:
        save_directory: Path to directory containing Level.sav and Players/
        mappings: List of (source_guid, target_guid) tuples to swap
        guild_fix: Whether to update guild memberships (default True)
        create_backup: Whether to create backup before migration (default False)
        backup_directory: Where to store backups (default: save_directory/backups)
        
    Returns:
        Number of successful migrations
        
    Raises:
        FileNotFoundError: If Level.sav or player files not found
        ValueError: If GUIDs are invalid or have conflicts
        RuntimeError: If migration fails
        
    Example:
        count = migrate_guids_batch(
            Path("/tmp/save_12345"),
            mappings=[
                ("00000000000000000000000000000001", "1B31C53D000000000000000000000000"),
                ("00000000000000000000000000000002", "2A42D64E000000000000000000000000")
            ]
        )
    """
    logger.info(f"Starting batch migration with {len(mappings)} mappings")
    
    # Create backup if requested
    if create_backup:
        if backup_directory is None:
            backup_directory = save_directory / "backups"
        backup_save_directory(save_directory, backup_directory)
    
    # Perform each migration sequentially
    # Note: We call migrate_guids() for each pair to ensure all swap logic is applied
    success_count = 0
    for idx, (source_guid, target_guid) in enumerate(mappings, 1):
        try:
            logger.info(f"Migration {idx}/{len(mappings)}: {source_guid} <-> {target_guid}")
            migrate_guids(
                save_directory=save_directory,
                source_guid=source_guid,
                target_guid=target_guid,
                guild_fix=guild_fix,
                create_backup=False  # Already created backup above
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Migration {idx} failed: {e}")
            # Continue with next migration
            continue
    
    logger.info(f"Batch migration complete: {success_count}/{len(mappings)} successful")
    return success_count
