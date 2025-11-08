# Batch Migration Feature

## Overview
The Palworld Save Migration Tool now supports **batch migration** - you can migrate multiple players in a single operation.

## How It Works

### Single Migration (Before)
- Select 1 source player
- Select 1 target player
- Migrate: A → C

### Batch Migration (Now)
- Select multiple source players (A, B)
- Select multiple target players (C, D)
- Migrate: A → C **AND** B → D simultaneously

## Usage Instructions

### Frontend (Web UI)

1. **Upload your save file** (same as before)

2. **Select multiple players:**
   - Click a player to select it (row turns blue)
   - Click again to deselect
   - Select players on BOTH sides

3. **Requirements:**
   - Must select **same number** of players on source and target
   - No overlap (a player can't be both source and target)
   - Minimum 1 pair

4. **Click "Migrate Players"** to process all mappings at once

### Example Scenarios

#### Scenario 1: Two Friends Joining Server
```
Source (Local Save):          Target (Server):
- Alice (00...01)      →      - ServerSlot1 (AA...01)
- Bob   (00...02)      →      - ServerSlot2 (BB...01)
```

#### Scenario 2: Four Players Migrating
```
Source:                       Target:
- Player A (00...01)   →      - Slot1 (11...00)
- Player B (00...02)   →      - Slot2 (22...00)
- Player C (00...03)   →      - Slot3 (33...00)
- Player D (00...04)   →      - Slot4 (44...00)
```

## API Changes

### Old Endpoint (Single Migration)
```
POST /migrate
FormData:
  - file: <save.zip>
  - source_guid: "00000000000000000000000000000001"
  - target_guid: "1B31C53D000000000000000000000000"
```

### New Endpoint (Batch Migration)
```
POST /migrate
FormData:
  - file: <save.zip>
  - mappings_json: '[
      {"source_guid": "00...01", "target_guid": "AA...01"},
      {"source_guid": "00...02", "target_guid": "BB...01"}
    ]'
```

## Backend Implementation

### New Models (`web_service/models.py`)

```python
class GuidMapping(BaseModel):
    source_guid: str  # 32 hex chars
    target_guid: str  # 32 hex chars
    
class MigrationRequest(BaseModel):
    mappings: List[GuidMapping]  # Array of mappings
```

### Validation
- Each source GUID must be unique
- Each target GUID must be unique
- No GUID can be both source and target
- All GUIDs must exist in the save file
- Source and target in each pair must be different

### New Function (`web_service/core/migration.py`)

```python
def migrate_guids_batch(
    save_directory: Path,
    mappings: List[Tuple[str, str]],
    guild_fix: bool = True,
    create_backup: bool = False
) -> int:
    """Perform multiple GUID migrations sequentially."""
```

## Benefits

1. **Efficiency:** Migrate 4 players in one operation instead of 4 separate operations
2. **Convenience:** Perfect for friend groups joining servers together
3. **Atomic Backup:** Single backup for entire batch operation
4. **Better UX:** See all migrations in one progress indicator

## Technical Details

### Order of Execution
Migrations are performed **sequentially** (one after another) to ensure consistency:
```
1. Backup save (if requested)
2. Migrate A → C
3. Migrate B → D
4. Migrate E → F
5. Create output zip
```

### Error Handling
- If one migration fails, the system continues with remaining migrations
- Returns success count: e.g., "3/4 successful"
- All successful migrations are applied even if one fails

## Backwards Compatibility

The system still works with single migrations:
```javascript
// Old way (still works via array with 1 item)
mappings_json: '[{"source_guid": "...", "target_guid": "..."}]'
```

## File Structure Changes

### Modified Files
1. `web_service/models.py` - Added `GuidMapping` and updated `MigrationRequest`
2. `web_service/core/migration.py` - Added `migrate_guids_batch()`
3. `web_service/app.py` - Updated `/migrate` endpoint
4. `web_service/static/app.js` - Multi-select UI logic
5. `web_service/templates/index.html` - Instructions and hints
6. `web_service/static/styles.css` - Hint styling

## Testing

### Manual Test Steps
1. Upload a save with 4+ players
2. Select 2 players on source side (click each one)
3. Select 2 players on target side (click each one)
4. Verify button enables only when counts match
5. Click "Migrate Players"
6. Check that all migrations complete
7. Download and verify migrated.zip

### Unit Test Example
```python
def test_batch_migration():
    mappings = [
        ("00000000000000000000000000000001", "AA000000000000000000000000000001"),
        ("00000000000000000000000000000002", "BB000000000000000000000000000001")
    ]
    
    result = migrate_guids_batch(
        save_directory=test_save_dir,
        mappings=mappings
    )
    
    assert result == 2  # Both succeeded
```

## Known Limitations

1. **Order Matters:** Mappings are applied in the order provided (sequential, not parallel)
2. **Partial Success:** If migration 2 of 4 fails, migrations 1, 3, 4 still proceed
3. **No Undo:** Once batch completes, you must restore from backup to undo

## Future Improvements

- [ ] Parallel migration processing (with conflict detection)
- [ ] Visual pairing UI (drag lines between source/target)
- [ ] Import/export mapping configurations
- [ ] Dry-run mode to preview changes
- [ ] Detailed per-migration progress feedback
