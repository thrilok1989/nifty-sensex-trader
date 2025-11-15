# Backup & Restore System

This document explains how to use the backup and restore functionality for your NIFTY/SENSEX Trading Application.

## Overview

The backup system provides two ways to manage backups:

1. **Streamlit Web App** (`backup_app.py`) - User-friendly web interface
2. **Command-Line Tool** (`backup_manager.py`) - Fast CLI utility

## What Gets Backed Up?

The backup system creates comprehensive backups including:

### Files
- `app.py` - Main Streamlit application
- `config.py` - Configuration settings
- `market_data.py` - Market data fetcher
- `signal_manager.py` - Signal tracking module
- `strike_calculator.py` - Strike price calculator
- `trade_executor.py` - Trade execution module
- `telegram_alerts.py` - Telegram notification system
- `dhan_api.py` - DhanHQ broker integration
- `smart_trading_dashboard.py` - Smart trading dashboard
- `bias_analysis.py` - Bias analysis module
- `option_chain_analysis.py` - Option chain analyzer
- `nse_options_helpers.py` - NSE options helper functions
- `nse_options_analyzer.py` - NSE options analyzer
- `advanced_chart_analysis.py` - Advanced charting module
- `run_dashboard.py` - Standalone dashboard runner
- `example_usage.py` - Usage examples
- `requirements.txt` - Python dependencies
- `requirements_dashboard.txt` - Dashboard dependencies
- `trading_signals.json` - Trading signal data (optional)

### Directories
- `indicators/` - All custom indicator modules
  - `__init__.py`
  - `om_indicator.py`
  - `ultimate_rsi.py`
  - `volume_order_blocks.py`
  - `htf_support_resistance.py`
  - `htf_volume_footprint.py`

## Method 1: Streamlit Web App (Recommended for Beginners)

### Starting the Backup App

```bash
streamlit run backup_app.py
```

The app will open in your browser at `http://localhost:8501`

### Features

#### 📦 Create Backup Tab
- Enter custom backup name or use auto-generated timestamp
- Choose whether to include trading signals data
- Preview all files that will be backed up
- Click "Create Backup Now" button
- View backup details after creation

#### 📜 Backup History Tab
- View all existing backups in a table
- See backup details (name, date, size, file count)
- Delete old backups

#### 🔄 Restore Backup Tab
- Select backup to restore from dropdown
- View backup details before restoring
- Confirm restoration (requires checkbox)
- Old files are backed up automatically before restore

### Backup Location
All backups are stored in: `./backups/`

## Method 2: Command-Line Tool (Recommended for Advanced Users)

### Quick Start

```bash
# Create a backup
python backup_manager.py create

# List all backups
python backup_manager.py list

# Restore from backup
python backup_manager.py restore backup_20251115_123045

# Delete a backup
python backup_manager.py delete backup_20251115_123045

# Show backup info
python backup_manager.py info backup_20251115_123045
```

### Detailed Usage

#### Create Backup

```bash
# Create backup with auto-generated name (timestamp)
python backup_manager.py create

# Create backup with custom name
python backup_manager.py create my_backup_v1

# Create backup without trading signals data
python backup_manager.py create --no-data

# Create backup with custom name and no data
python backup_manager.py create my_backup_v1 --no-data
```

#### List Backups

```bash
python backup_manager.py list
```

Output example:
```
╔═══╦═══════════════════════╦═════════════════════╦═══════╦══════╦═══════╦══════╗
║ # ║ Backup Name          ║ Created             ║ Files ║ Dirs ║ Size  ║ Data ║
╠═══╬═══════════════════════╬═════════════════════╬═══════╬══════╬═══════╬══════╣
║ 1 ║ backup_20251115_1230 ║ 2025-11-15 12:30:45 ║ 19    ║ 1    ║ 2.5MB ║ ✅   ║
║ 2 ║ backup_20251114_1545 ║ 2025-11-14 15:45:12 ║ 18    ║ 1    ║ 2.3MB ║ ❌   ║
╚═══╩═══════════════════════╩═════════════════════╩═══════╩══════╩═══════╩══════╝
```

#### Restore Backup

```bash
python backup_manager.py restore backup_20251115_123045
```

**WARNING**: This will overwrite your current files!
- Current files are backed up with `.pre_restore_backup` extension
- You will be asked to confirm before proceeding

#### Delete Backup

```bash
python backup_manager.py delete backup_20251115_123045
```

You will be asked to confirm before deletion.

#### Show Backup Info

```bash
python backup_manager.py info backup_20251115_123045
```

Output example:
```
Backup Name: backup_20251115_123045
Created: 2025-11-15T12:30:45.123456
Files Count: 19
Directories Count: 1
Total Size: 2.45 MB
ZIP Size: 1.23 MB
Include Data: Yes

Files included:
  • app.py
  • config.py
  • market_data.py
  ...
```

#### Help

```bash
python backup_manager.py help
```

## Backup Files

### File Structure

```
nifty-sensex-trader/
├── backups/                     # Backup storage directory
│   ├── backup_20251115_123045.zip
│   ├── backup_20251114_154512.zip
│   └── ...
├── backup_app.py               # Streamlit backup app
├── backup_manager.py           # CLI backup utility
├── app.py                      # Main app
├── app_backup.py               # Static backup of main app
└── ...
```

### Backup Contents (Inside ZIP)

```
backup_20251115_123045.zip
├── backup_metadata.json        # Backup metadata
├── app.py
├── config.py
├── market_data.py
├── signal_manager.py
├── ...
└── indicators/
    ├── __init__.py
    ├── om_indicator.py
    ├── ultimate_rsi.py
    └── ...
```

## Best Practices

### 1. Regular Backups
- Create backups before making major changes
- Create daily backups during active development
- Keep at least 3 recent backups

### 2. Naming Convention
- Use descriptive names: `before_feature_x`, `working_version_1`
- Include dates in custom names: `backup_2025_11_15_before_update`
- Keep names short and meaningful

### 3. Data Management
- Include trading signals data for complete backups
- Use `--no-data` for code-only backups
- Regularly review and delete old backups to save space

### 4. Restoration Safety
- Always verify backup contents before restoring
- Keep current files (pre-restore backups) until verified
- Test restored application before deleting pre-restore backups

### 5. Storage
- Regularly copy important backups to external storage
- Consider cloud backup for critical production backups
- Monitor backup directory size

## Automation Examples

### Daily Backup Cron Job

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/nifty-sensex-trader && python backup_manager.py create daily_auto
```

### Backup Before Git Push

Add to `.git/hooks/pre-push`:
```bash
#!/bin/bash
cd /path/to/nifty-sensex-trader
python backup_manager.py create pre_push_$(date +%Y%m%d_%H%M%S)
```

### Weekly Cleanup Script

```bash
#!/bin/bash
# Keep only last 7 backups
cd /path/to/nifty-sensex-trader/backups
ls -t *.zip | tail -n +8 | xargs -r rm
```

## Troubleshooting

### Backup Creation Failed

**Problem**: "Permission denied" error
**Solution**: Check write permissions for `backups/` directory
```bash
chmod 755 backups/
```

**Problem**: "No space left on device"
**Solution**: Delete old backups or increase disk space

### Restore Failed

**Problem**: "Backup not found"
**Solution**: Run `python backup_manager.py list` to see available backups

**Problem**: Restored app doesn't work
**Solution**:
1. Check pre-restore backup files (`.pre_restore_backup`)
2. Restore from a different backup
3. Manual file recovery from pre-restore backups

### Backup Too Large

**Solution**:
1. Use `--no-data` flag to exclude trading signals
2. Clean up indicators if not needed
3. Remove documentation files from critical files list

## Recovery Scenarios

### Scenario 1: Accidental File Deletion

```bash
# Restore from most recent backup
python backup_manager.py list
python backup_manager.py restore backup_XXXXXXXX_XXXXXX
```

### Scenario 2: Bad Update/Change

```bash
# If you just restored and it's bad, use pre-restore backup
cd /path/to/nifty-sensex-trader
cp app.py.pre_restore_backup app.py
cp config.py.pre_restore_backup config.py
# etc...
```

### Scenario 3: Complete System Failure

```bash
# Clone repository again
git clone <repository>
cd nifty-sensex-trader

# Copy backups from external storage
cp -r /backup/location/backups ./

# Restore latest backup
python backup_manager.py restore backup_XXXXXXXX_XXXXXX
```

## Additional Files

### Static Backup
- `app_backup.py` - Static backup of main app.py created manually
- This is a simple copy, not managed by backup system
- Use as emergency fallback if backup system fails

## Support

For issues or questions:
1. Check this README
2. Review backup logs/error messages
3. Check pre-restore backup files
4. Contact system administrator

## Version History

- **v1.0** (2025-11-15)
  - Initial backup system implementation
  - Streamlit web app
  - Command-line utility
  - Automatic metadata tracking
  - ZIP compression support

---

**Last Updated**: 2025-11-15
**Author**: Auto-generated Backup System
