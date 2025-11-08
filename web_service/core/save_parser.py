"""Save file parser for extracting player information from Palworld saves.

This module provides functions to analyze Level.sav files and extract player
information without any GUI dependencies.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional

from loguru import logger

# Import from the copied palworld_save_tools
from web_service.core.palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from web_service.core.palworld_save_tools.gvas import GvasFile
from web_service.core.palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES as SKP_PALWORLD_CUSTOM_PROPERTIES


class Player:
    """Represents a player extracted from save files."""
    
    def __init__(self, guid: str, name: str, guild_id: str):
        self.guid = guid.upper().replace('-', '')  # Normalize to uppercase without dashes
        self.name = name
        self.guild_id = guild_id
    
    def to_dict(self) -> Dict[str, str]:
        """Convert player to dictionary for JSON serialization."""
        return {
            "guid": self.guid,
            "name": self.name,
            "guild_id": self.guild_id
        }
    
    def __repr__(self):
        return f"Player(guid={self.guid}, name={self.name}, guild_id={self.guild_id})"


def sav_to_json(filepath: Path) -> dict:
    """Convert a .sav file to JSON dictionary.
    
    Args:
        filepath: Path to the .sav file
        
    Returns:
        Dictionary representation of the save file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If file cannot be parsed
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Save file not found: {filepath}")
    
    try:
        with open(filepath, "rb") as f:
            data = f.read()
            raw_gvas, save_type = decompress_sav_to_gvas(data)
        
        gvas_file = GvasFile.read(
            raw_gvas, 
            PALWORLD_TYPE_HINTS, 
            SKP_PALWORLD_CUSTOM_PROPERTIES, 
            allow_nan=True
        )
        return gvas_file.dump()
    except Exception as e:
        logger.error(f"Failed to parse save file {filepath}: {e}")
        raise RuntimeError(f"Failed to parse save file: {str(e)}")


def json_to_sav(json_data: dict, output_filepath: Path) -> None:
    """Convert JSON dictionary back to .sav file.
    
    Args:
        json_data: Dictionary representation of save data
        output_filepath: Path where to write the .sav file
        
    Raises:
        RuntimeError: If conversion fails
    """
    try:
        gvas_file = GvasFile.load(json_data)
        
        # Determine save type based on class name
        save_type = 0x32 if (
            "Pal.PalworldSaveGame" in gvas_file.header.save_game_class_name or 
            "Pal.PalLocalWorldSaveGame" in gvas_file.header.save_game_class_name
        ) else 0x31
        
        sav_file = compress_gvas_to_sav(
            gvas_file.write(SKP_PALWORLD_CUSTOM_PROPERTIES), 
            save_type
        )
        
        with open(output_filepath, "wb") as f:
            f.write(sav_file)
            
        logger.info(f"Successfully wrote save file to {output_filepath}")
    except Exception as e:
        logger.error(f"Failed to write save file {output_filepath}: {e}")
        raise RuntimeError(f"Failed to write save file: {str(e)}")


def extract_players(save_directory: Path) -> List[Player]:
    """Extract player information from a Palworld save directory.
    
    Parses the Level.sav file and extracts all players from guild data.
    
    Args:
        save_directory: Path to directory containing Level.sav and Players/ folder
        
    Returns:
        List of Player objects with guid, name, and guild_id
        
    Raises:
        FileNotFoundError: If Level.sav or Players/ folder not found
        RuntimeError: If save file cannot be parsed
        
    Example:
        players = extract_players(Path("/tmp/save_12345"))
        for player in players:
            print(f"{player.name}: {player.guid}")
    """
    level_sav_path = save_directory / "Level.sav"
    players_folder = save_directory / "Players"
    
    # Validate structure
    if not level_sav_path.exists():
        raise FileNotFoundError(f"Level.sav not found in {save_directory}")
    
    if not players_folder.exists() or not players_folder.is_dir():
        raise FileNotFoundError(f"Players folder not found in {save_directory}")
    
    # Check for at least one player save file
    player_files = list(players_folder.glob("*.sav"))
    if not player_files:
        raise FileNotFoundError(f"No player .sav files found in {players_folder}")
    
    logger.info(f"Parsing Level.sav from {save_directory}")
    
    try:
        # Parse Level.sav
        level_json = sav_to_json(level_sav_path)
        
        # Extract players from guild data
        group_data_list = level_json['properties']['worldSaveData']['value']['GroupSaveDataMap']['value']
        
        players = []
        for group in group_data_list:
            # Only process guild groups
            if group['value']['GroupType']['value']['value'] == 'EPalGroupType::Guild':
                # Extract guild ID
                key = group['key']
                if isinstance(key, dict) and 'InstanceId' in key:
                    guild_id = key['InstanceId']['value']
                else:
                    guild_id = str(key)
                
                # Extract players from this guild
                raw_data = group['value']['RawData']['value']
                guild_players = raw_data.get('players', [])
                
                for player_data in guild_players:
                    uid = str(player_data.get('player_uid', '')).replace('-', '')
                    name = player_data.get('player_info', {}).get('player_name', 'Unknown')
                    
                    if uid:  # Only add if GUID is valid
                        players.append(Player(uid, name, guild_id))
        
        logger.info(f"Extracted {len(players)} players from save")
        return players
        
    except KeyError as e:
        logger.error(f"Failed to extract players: missing key {e}")
        raise RuntimeError(f"Save file structure invalid: missing key {e}")
    except Exception as e:
        logger.error(f"Failed to extract players: {e}")
        raise RuntimeError(f"Failed to extract players: {str(e)}")


def validate_save_structure(save_directory: Path) -> tuple[bool, Optional[str]]:
    """Validate that a directory contains a valid Palworld save structure.
    
    Args:
        save_directory: Path to directory to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str or None)
        
    Example:
        is_valid, error = validate_save_structure(Path("/tmp/save_12345"))
        if not is_valid:
            print(f"Invalid save: {error}")
    """
    level_sav_path = save_directory / "Level.sav"
    players_folder = save_directory / "Players"
    
    if not level_sav_path.exists():
        # Check one level deeper (common zip structure)
        subdirs = [d for d in save_directory.iterdir() if d.is_dir()]
        if len(subdirs) == 1:
            nested_level = subdirs[0] / "Level.sav"
            if nested_level.exists():
                return True, None
        
        return False, "Level.sav not found in uploaded archive"
    
    if not players_folder.exists():
        return False, "Players folder not found in uploaded archive"
    
    if not players_folder.is_dir():
        return False, "Players must be a directory"
    
    # Check for at least one player file
    player_files = list(players_folder.glob("*.sav"))
    if not player_files:
        return False, "No player .sav files found in Players folder"
    
    return True, None
