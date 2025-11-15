"""
Backup & Restore App for NIFTY/SENSEX Trader
===========================================

This Streamlit app allows you to:
- Create full backups of your trading application
- Restore from previous backups
- Manage backup files
- View backup history

Author: Auto-generated
Date: 2025-11-15
"""

import streamlit as st
import os
import shutil
import json
from datetime import datetime
from pathlib import Path
import zipfile
import pandas as pd

# ═══════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Backup & Restore Manager",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

# Base directory
BASE_DIR = Path(__file__).parent.absolute()
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# Files to backup (critical files only)
CRITICAL_FILES = [
    "app.py",
    "config.py",
    "market_data.py",
    "signal_manager.py",
    "strike_calculator.py",
    "trade_executor.py",
    "telegram_alerts.py",
    "dhan_api.py",
    "smart_trading_dashboard.py",
    "bias_analysis.py",
    "option_chain_analysis.py",
    "nse_options_helpers.py",
    "nse_options_analyzer.py",
    "advanced_chart_analysis.py",
    "run_dashboard.py",
    "example_usage.py",
    "requirements.txt",
    "requirements_dashboard.txt",
    "trading_signals.json"
]

# Directories to backup
CRITICAL_DIRS = [
    "indicators"
]

# ═══════════════════════════════════════════════════════════════════════
# BACKUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def create_backup(backup_name=None, include_data=True):
    """Create a complete backup of the application"""
    try:
        # Generate backup name with timestamp
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

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

        # Backup critical directories
        for dir_name in CRITICAL_DIRS:
            src_dir = BASE_DIR / dir_name
            if src_dir.exists() and src_dir.is_dir():
                dst_dir = backup_path / dir_name
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                metadata['dirs_count'] += 1

                # Count files in directory
                for root, dirs, files in os.walk(dst_dir):
                    for f in files:
                        fp = Path(root) / f
                        total_size += fp.stat().st_size

        # Update metadata
        metadata['total_size'] = total_size
        metadata['files'] = files_backed_up

        # Save metadata
        metadata_file = backup_path / "backup_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

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

        return {
            'success': True,
            'backup_name': backup_name,
            'zip_path': str(zip_path),
            'metadata': metadata
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def list_backups():
    """List all available backups"""
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
            st.warning(f"Could not read backup {zip_file.name}: {e}")

    # Sort by created date (newest first)
    backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return backups


def restore_backup(backup_name):
    """Restore application from a backup"""
    try:
        zip_path = BACKUP_DIR / f"{backup_name}.zip"

        if not zip_path.exists():
            return {
                'success': False,
                'error': 'Backup file not found'
            }

        # Create temporary restore folder
        restore_path = BACKUP_DIR / f"restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        restore_path.mkdir(exist_ok=True)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(restore_path)

        # Read metadata
        metadata_file = restore_path / "backup_metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

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

        # Clean up temporary restore folder
        shutil.rmtree(restore_path)

        return {
            'success': True,
            'backup_name': backup_name,
            'files_restored': files_restored,
            'metadata': metadata
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def delete_backup(backup_name):
    """Delete a backup"""
    try:
        zip_path = BACKUP_DIR / f"{backup_name}.zip"

        if zip_path.exists():
            zip_path.unlink()
            return {'success': True}
        else:
            return {
                'success': False,
                'error': 'Backup not found'
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def format_size(bytes):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"


# ═══════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════

st.title("💾 Backup & Restore Manager")
st.caption("Manage backups for your NIFTY/SENSEX Trading Application")

# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("📊 Backup Statistics")

    backups = list_backups()
    total_backups = len(backups)
    total_size = sum([b.get('zip_size', 0) for b in backups])

    st.metric("Total Backups", total_backups)
    st.metric("Total Size", format_size(total_size))

    if backups:
        latest_backup = backups[0]
        st.metric("Latest Backup", latest_backup.get('backup_name', 'N/A'))
        st.caption(f"Created: {latest_backup.get('created_at', 'N/A')[:19]}")

    st.divider()

    st.header("ℹ️ What Gets Backed Up?")
    st.markdown("""
    **Files:**
    - Main app (app.py)
    - All core modules
    - Configuration files
    - Trading signals data
    - Requirements files

    **Directories:**
    - indicators/ (all indicator modules)
    """)

    st.divider()

    st.header("⚙️ Backup Location")
    st.code(str(BACKUP_DIR))

# ═══════════════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs(["📦 Create Backup", "📜 Backup History", "🔄 Restore Backup"])

# ─────────────────────────────────────────────────────────────────────
# TAB 1: CREATE BACKUP
# ─────────────────────────────────────────────────────────────────────

with tab1:
    st.header("📦 Create New Backup")

    col1, col2 = st.columns([2, 1])

    with col1:
        backup_name_input = st.text_input(
            "Backup Name (optional)",
            placeholder=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            help="Leave empty for automatic timestamp-based name"
        )

    with col2:
        include_data = st.checkbox(
            "Include Trading Signals",
            value=True,
            help="Include trading_signals.json in backup"
        )

    st.divider()

    # Preview what will be backed up
    st.subheader("📋 Files to be Backed Up")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Core Files:**")
        files_to_show = [f for f in CRITICAL_FILES if f != "trading_signals.json"]
        if include_data:
            files_to_show.append("trading_signals.json")

        for file in files_to_show[:10]:
            file_path = BASE_DIR / file
            if file_path.exists():
                size = format_size(file_path.stat().st_size)
                st.text(f"✅ {file} ({size})")
            else:
                st.text(f"⚠️ {file} (not found)")

        if len(files_to_show) > 10:
            st.text(f"... and {len(files_to_show) - 10} more files")

    with col2:
        st.markdown("**Directories:**")
        for dir_name in CRITICAL_DIRS:
            dir_path = BASE_DIR / dir_name
            if dir_path.exists():
                # Count files in directory
                file_count = sum([len(files) for _, _, files in os.walk(dir_path)])
                st.text(f"✅ {dir_name}/ ({file_count} files)")
            else:
                st.text(f"⚠️ {dir_name}/ (not found)")

    st.divider()

    # Create backup button
    if st.button("🚀 Create Backup Now", type="primary", use_container_width=True):
        with st.spinner("Creating backup... This may take a moment..."):
            result = create_backup(
                backup_name=backup_name_input if backup_name_input else None,
                include_data=include_data
            )

            if result['success']:
                st.success(f"✅ Backup created successfully!")

                metadata = result['metadata']

                st.info(f"""
                **Backup Details:**
                - Name: {result['backup_name']}
                - Files: {metadata['files_count']}
                - Directories: {metadata['dirs_count']}
                - Total Size: {format_size(metadata['total_size'])}
                - Location: {result['zip_path']}
                """)

                st.balloons()
            else:
                st.error(f"❌ Backup failed: {result['error']}")

# ─────────────────────────────────────────────────────────────────────
# TAB 2: BACKUP HISTORY
# ─────────────────────────────────────────────────────────────────────

with tab2:
    st.header("📜 Backup History")

    backups = list_backups()

    if not backups:
        st.info("No backups found. Create your first backup in the 'Create Backup' tab.")
    else:
        st.write(f"Total Backups: **{len(backups)}**")

        # Create DataFrame for display
        backup_data = []
        for backup in backups:
            backup_data.append({
                'Backup Name': backup.get('backup_name', 'N/A'),
                'Created': backup.get('created_at', 'N/A')[:19],
                'Files': backup.get('files_count', 0),
                'Dirs': backup.get('dirs_count', 0),
                'Size': format_size(backup.get('zip_size', 0)),
                'Data Included': '✅' if backup.get('include_data', False) else '❌'
            })

        df = pd.DataFrame(backup_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        # Delete backup section
        st.subheader("🗑️ Delete Backup")

        col1, col2 = st.columns([2, 1])

        with col1:
            backup_to_delete = st.selectbox(
                "Select backup to delete",
                options=[b['backup_name'] for b in backups],
                key="delete_backup_select"
            )

        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                result = delete_backup(backup_to_delete)

                if result['success']:
                    st.success(f"✅ Backup '{backup_to_delete}' deleted successfully!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete backup: {result['error']}")

# ─────────────────────────────────────────────────────────────────────
# TAB 3: RESTORE BACKUP
# ─────────────────────────────────────────────────────────────────────

with tab3:
    st.header("🔄 Restore from Backup")

    backups = list_backups()

    if not backups:
        st.info("No backups available to restore. Create a backup first.")
    else:
        st.warning("""
        ⚠️ **WARNING**: Restoring from a backup will overwrite your current application files!

        - Current files will be backed up with `.pre_restore_backup` extension
        - All changes since the backup will be lost
        - The application will need to be restarted after restore
        """)

        st.divider()

        col1, col2 = st.columns([2, 1])

        with col1:
            backup_to_restore = st.selectbox(
                "Select backup to restore",
                options=[b['backup_name'] for b in backups],
                key="restore_backup_select"
            )

        # Show backup details
        selected_backup = next((b for b in backups if b['backup_name'] == backup_to_restore), None)

        if selected_backup:
            st.divider()
            st.subheader("📋 Backup Details")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Files", selected_backup.get('files_count', 0))

            with col2:
                st.metric("Directories", selected_backup.get('dirs_count', 0))

            with col3:
                st.metric("Size", format_size(selected_backup.get('zip_size', 0)))

            with col4:
                st.metric("Created", selected_backup.get('created_at', 'N/A')[:10])

            st.divider()

            # Confirmation checkbox
            confirm_restore = st.checkbox(
                "⚠️ I understand that this will overwrite my current files",
                key="confirm_restore"
            )

            # Restore button
            if st.button(
                "🔄 Restore Backup Now",
                type="primary",
                use_container_width=True,
                disabled=not confirm_restore
            ):
                with st.spinner("Restoring backup... Please wait..."):
                    result = restore_backup(backup_to_restore)

                    if result['success']:
                        st.success(f"✅ Backup restored successfully!")

                        st.info(f"""
                        **Restore Details:**
                        - Backup: {result['backup_name']}
                        - Files Restored: {len(result['files_restored'])}

                        **Next Steps:**
                        1. Restart the application
                        2. Verify that everything is working correctly
                        3. Old files are backed up with '.pre_restore_backup' extension
                        """)

                        st.balloons()
                    else:
                        st.error(f"❌ Restore failed: {result['error']}")

# ═══════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════

st.divider()
st.caption(f"Backup Manager v1.0 | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
