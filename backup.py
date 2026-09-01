#!/usr/bin/env python3
"""Daily backup of SQLite memory database to GitHub repo."""
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

DB_PATH = Path("/root/.hermes/memory.db")
REPO_PATH = Path("/root/hermes-memory")
BACKUP_DIR = REPO_PATH / "backups"

def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)

def backup():
    if not DB_PATH.exists():
        print("❌ Database not found")
        return
    
    # Create backup directory
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Copy with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d")
    backup_file = BACKUP_DIR / f"memory_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_file)
    
    # Also overwrite latest
    latest = REPO_PATH / "memory_latest.db"
    shutil.copy2(DB_PATH, latest)
    
    # Git commit and push
    os.chdir(REPO_PATH)
    run("git add -A")
    result = run(f'git commit -m "Daily backup {timestamp}"')
    if result.returncode == 0:
        run("git push")
        print(f"✅ Backup saved: {backup_file.name}")
    else:
        print(f"⚠️ Nothing to commit or push failed: {result.stderr}")

if __name__ == "__main__":
    import os
    backup()
