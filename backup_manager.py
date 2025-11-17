#!/usr/bin/env python3
"""
Backup Manager Utility for NIFTY/SENSEX Trader
==============================================

Command-line utility to manage backups of your trading application.

Usage:
    python backup_manager.py create [backup_name] [--no-data]
    python backup_manager.py list
    python backup_manager.py restore <backup_name>
    python backup_manager.py delete <backup_name>
    python backup_manager.py info <backup_name>
    python backup_manager.py help

Examples:
    python backup_manager.py create                     # Create backup with auto name
    python backup_manager.py create my_backup           # Create backup with custom name
    python backup_manager.py create --no-data           # Create backup without data files
    python backup_manager.py list                       # List all backups
    python backup_manager.py restore backup_20251115    # Restore from backup
    python backup_manager.py delete backup_20251115     # Delete a backup
    python backup_manager.py info backup_20251115       # Show backup details

Author: Auto-generated
Date: 2025-11-15
"""

import os
import sys
import shutil
import json
from datetime import datetime
from pathlib import Path
import zipfile
import argparse
from tabulate import tabulate

# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.absolute()
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

CRITICAL_FILES = [
    "app.py",
    "config.py",
    "market_data.py",
    "signal_manager.py",
    "strike_calculator.py",
    "trade_executor.py",
    "telegram_alerts.py",
    "dhan_api.py",
    "bias_analysis.py",
    "option_chain_analysis.py",
    "nse_options_helpers.py",
    "nse_options_analyzer.py",
    "advanced_chart_analysis.py",
    "requirements.txt",
    "trading_signals.json"
]

CRITICAL_DIRS = ["indicators"]

# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def format_size(bytes_size):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"❌ ERROR: {text}")


def print_warning(text):
    """Print warning message"""
    print(f"⚠️  WARNING: {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


# ═══════════════════════════════════════════════════════════════════════
# BACKUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def create_backup(backup_name=None, include_data=True):
    """Create a complete backup of the application"""
    print_header("Creating Backup")

    try:
        # Generate backup name with timestamp
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

        print_info(f"Backup name: {backup_name}")
        print_info(f"Include data: {'Yes' if include_data else 'No'}")

        # Create backup folder
        backup_path = BACKUP_DIR / backup_name
        backup_path.mkdir(exist_ok=True)

        # Create metadata
        metadata = {
            "backup_name": backup_name,
            "created_at": datetime.now().isoformat(),
            "files_count": 0,
            "dirs_count": 0,
            "total_size": 0,
            "include_data": include_data
        }

        files_backed_up = []
        total_size = 0

        print_info("Backing up files...")

        # Backup critical files
        for file in CRITICAL_FILES:
            src_file = BASE_DIR / file
            if src_file.exists():
                # Skip data files if not including data
                if not include_data and file == "trading_signals.json":
                    continue

                dst_file = backup_path / file
                shutil.copy2(src_file, dst_file)
                files_backed_up.append(file)
                total_size += src_file.stat().st_size
                metadata['files_count'] += 1
                print(f"  ✓ {file}")

        print_info("Backing up directories...")

        # Backup critical directories
        for dir_name in CRITICAL_DIRS:
            src_dir = BASE_DIR / dir_name
            if src_dir.exists() and src_dir.is_dir():
                dst_dir = backup_path / dir_name
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                metadata['dirs_count'] += 1

                # Count files in directory
                file_count = 0
                for root, dirs, files in os.walk(dst_dir):
                    for f in files:
                        fp = Path(root) / f
                        total_size += fp.stat().st_size
                        file_count += 1

                print(f"  ✓ {dir_name}/ ({file_count} files)")

        # Update metadata
        metadata['total_size'] = total_size
        metadata['files'] = files_backed_up

        # Save metadata
        metadata_file = backup_path / "backup_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print_info("Creating ZIP archive...")

        # Create ZIP archive
        zip_path = BACKUP_DIR / f"{backup_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(backup_path)
                    zipf.write(file_path, arcname)

        # Remove temporary backup folder (keep only ZIP)
        shutil.rmtree(backup_path)

        zip_size = zip_path.stat().st_size

        print_success("Backup created successfully!")
        print()
        print(f"  Backup Name: {backup_name}")
        print(f"  Files: {metadata['files_count']}")
        print(f"  Directories: {metadata['dirs_count']}")
        print(f"  Total Size: {format_size(total_size)}")
        print(f"  ZIP Size: {format_size(zip_size)}")
        print(f"  Location: {zip_path}")
        print()

        return True

    except Exception as e:
        print_error(f"Backup failed: {e}")
        return False


def list_backups():
    """List all available backups"""
    print_header("Available Backups")

    backups = []

    for zip_file in BACKUP_DIR.glob("*.zip"):
        try:
            # Extract metadata from ZIP
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                if 'backup_metadata.json' in zipf.namelist():
                    with zipf.open('backup_metadata.json') as f:
                        metadata = json.load(f)
                        metadata['zip_file'] = zip_file.name
                        metadata['zip_size'] = zip_file.stat().st_size
                        backups.append(metadata)
        except Exception as e:
            print_warning(f"Could not read backup {zip_file.name}: {e}")

    if not backups:
        print_info("No backups found.")
        return

    # Sort by created date (newest first)
    backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Create table
    table_data = []
    for i, backup in enumerate(backups, 1):
        table_data.append([
            i,
            backup.get('backup_name', 'N/A'),
            backup.get('created_at', 'N/A')[:19],
            backup.get('files_count', 0),
            backup.get('dirs_count', 0),
            format_size(backup.get('zip_size', 0)),
            '✅' if backup.get('include_data', False) else '❌'
        ])

    headers = ['#', 'Backup Name', 'Created', 'Files', 'Dirs', 'Size', 'Data']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    print()
    print(f"Total Backups: {len(backups)}")
    print(f"Total Size: {format_size(sum([b.get('zip_size', 0) for b in backups]))}")
    print()


def restore_backup(backup_name):
    """Restore application from a backup"""
    print_header(f"Restoring Backup: {backup_name}")

    try:
        zip_path = BACKUP_DIR / f"{backup_name}.zip"

        if not zip_path.exists():
            print_error(f"Backup '{backup_name}' not found!")
            return False

        print_warning("This will overwrite your current application files!")
        print_warning("Current files will be backed up with '.pre_restore_backup' extension")
        print()

        # Confirm restore
        response = input("Do you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print_info("Restore cancelled.")
            return False

        # Create temporary restore folder
        restore_path = BACKUP_DIR / f"restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        restore_path.mkdir(exist_ok=True)

        print_info("Extracting backup...")

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(restore_path)

        # Read metadata
        metadata_file = restore_path / "backup_metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        print_info("Restoring files...")

        # Restore files
        files_restored = []
        for file in metadata.get('files', []):
            src_file = restore_path / file
            dst_file = BASE_DIR / file

            if src_file.exists():
                # Create backup of current file before overwriting
                if dst_file.exists():
                    backup_current = dst_file.parent / f"{dst_file.name}.pre_restore_backup"
                    shutil.copy2(dst_file, backup_current)

                shutil.copy2(src_file, dst_file)
                files_restored.append(file)
                print(f"  ✓ {file}")

        print_info("Restoring directories...")

        # Restore directories
        for dir_name in CRITICAL_DIRS:
            src_dir = restore_path / dir_name
            dst_dir = BASE_DIR / dir_name

            if src_dir.exists():
                # Backup current directory
                if dst_dir.exists():
                    backup_current = dst_dir.parent / f"{dst_dir.name}_pre_restore_backup"
                    if backup_current.exists():
                        shutil.rmtree(backup_current)
                    shutil.copytree(dst_dir, backup_current)
                    shutil.rmtree(dst_dir)

                shutil.copytree(src_dir, dst_dir)

                # Count files
                file_count = sum([len(files) for _, _, files in os.walk(dst_dir)])
                print(f"  ✓ {dir_name}/ ({file_count} files)")

        # Clean up temporary restore folder
        shutil.rmtree(restore_path)

        print_success("Backup restored successfully!")
        print()
        print(f"  Backup: {backup_name}")
        print(f"  Files Restored: {len(files_restored)}")
        print()
        print_info("Please restart the application for changes to take effect.")
        print()

        return True

    except Exception as e:
        print_error(f"Restore failed: {e}")
        return False


def delete_backup(backup_name):
    """Delete a backup"""
    print_header(f"Deleting Backup: {backup_name}")

    try:
        zip_path = BACKUP_DIR / f"{backup_name}.zip"

        if not zip_path.exists():
            print_error(f"Backup '{backup_name}' not found!")
            return False

        # Confirm deletion
        response = input("Are you sure you want to delete this backup? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print_info("Deletion cancelled.")
            return False

        zip_path.unlink()

        print_success(f"Backup '{backup_name}' deleted successfully!")
        print()

        return True

    except Exception as e:
        print_error(f"Delete failed: {e}")
        return False


def show_backup_info(backup_name):
    """Show detailed information about a backup"""
    print_header(f"Backup Information: {backup_name}")

    try:
        zip_path = BACKUP_DIR / f"{backup_name}.zip"

        if not zip_path.exists():
            print_error(f"Backup '{backup_name}' not found!")
            return False

        # Extract metadata from ZIP
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            if 'backup_metadata.json' in zipf.namelist():
                with zipf.open('backup_metadata.json') as f:
                    metadata = json.load(f)

                    print(f"Backup Name: {metadata.get('backup_name', 'N/A')}")
                    print(f"Created: {metadata.get('created_at', 'N/A')}")
                    print(f"Files Count: {metadata.get('files_count', 0)}")
                    print(f"Directories Count: {metadata.get('dirs_count', 0)}")
                    print(f"Total Size: {format_size(metadata.get('total_size', 0))}")
                    print(f"ZIP Size: {format_size(zip_path.stat().st_size)}")
                    print(f"Include Data: {'Yes' if metadata.get('include_data', False) else 'No'}")
                    print()

                    if metadata.get('files'):
                        print("Files included:")
                        for file in metadata['files']:
                            print(f"  • {file}")
                        print()

                    return True
            else:
                print_error("Backup metadata not found in ZIP file!")
                return False

    except Exception as e:
        print_error(f"Failed to read backup info: {e}")
        return False


def show_help():
    """Show help information"""
    print_header("Backup Manager - Help")

    help_text = """
USAGE:
    python backup_manager.py <command> [options]

COMMANDS:
    create [name] [--no-data]   Create a new backup
    list                         List all available backups
    restore <name>              Restore from a backup
    delete <name>               Delete a backup
    info <name>                 Show detailed backup information
    help                        Show this help message

OPTIONS:
    --no-data                   Exclude trading signals data from backup

EXAMPLES:
    python backup_manager.py create
        Create a backup with auto-generated name (timestamp-based)

    python backup_manager.py create my_backup
        Create a backup with custom name

    python backup_manager.py create --no-data
        Create a backup without trading signals data

    python backup_manager.py list
        List all available backups

    python backup_manager.py restore backup_20251115_123045
        Restore from the specified backup

    python backup_manager.py delete backup_20251115_123045
        Delete the specified backup

    python backup_manager.py info backup_20251115_123045
        Show detailed information about the backup

BACKUP CONTENTS:
    • All core Python modules (app.py, config.py, etc.)
    • All indicator modules (indicators/ directory)
    • Configuration files (requirements.txt, etc.)
    • Trading signals data (optional, included by default)

BACKUP LOCATION:
    {backup_dir}

NOTES:
    • Backups are stored as ZIP files
    • Restoring will backup current files with '.pre_restore_backup' extension
    • Always verify backups after creation
    """.format(backup_dir=BACKUP_DIR)

    print(help_text)


# ═══════════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == 'create':
        backup_name = None
        include_data = True

        # Parse arguments
        if len(sys.argv) > 2:
            if '--no-data' in sys.argv:
                include_data = False
                # Get backup name if provided
                args = [arg for arg in sys.argv[2:] if arg != '--no-data']
                if args:
                    backup_name = args[0]
            else:
                backup_name = sys.argv[2]

        create_backup(backup_name, include_data)

    elif command == 'list':
        list_backups()

    elif command == 'restore':
        if len(sys.argv) < 3:
            print_error("Please specify backup name to restore")
            print_info("Usage: python backup_manager.py restore <backup_name>")
            return

        backup_name = sys.argv[2]
        restore_backup(backup_name)

    elif command == 'delete':
        if len(sys.argv) < 3:
            print_error("Please specify backup name to delete")
            print_info("Usage: python backup_manager.py delete <backup_name>")
            return

        backup_name = sys.argv[2]
        delete_backup(backup_name)

    elif command == 'info':
        if len(sys.argv) < 3:
            print_error("Please specify backup name")
            print_info("Usage: python backup_manager.py info <backup_name>")
            return

        backup_name = sys.argv[2]
        show_backup_info(backup_name)

    elif command == 'help' or command == '--help' or command == '-h':
        show_help()

    else:
        print_error(f"Unknown command: {command}")
        print_info("Run 'python backup_manager.py help' for usage information")


if __name__ == "__main__":
    main()
