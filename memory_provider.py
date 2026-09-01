#!/usr/bin/env python3
"""
Hermes Memory Provider — SQLite backend for agent memory.
Stores user facts, session logs, preferences, and scanned items.
"""
import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.expanduser("~/.hermes/memory.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            importance REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            name TEXT,
            qty INTEGER DEFAULT 1,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS scan_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date DATE,
            items_json TEXT,
            total_qty INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            key, value, category, content='memories', content_rowid='id'
        );

        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, key, value, category)
            VALUES (new.id, new.key, new.value, new.category);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, key, value, category)
            VALUES ('delete', old.id, old.key, old.value, old.category);
        END;

        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, key, value, category)
            VALUES ('delete', old.id, old.key, old.value, old.category);
            INSERT INTO memories_fts(rowid, key, value, category)
            VALUES (new.id, new.key, new.value, new.category);
        END;
    """)
    conn.commit()
    conn.close()

def set_memory(key, value, category="general", importance=0.5):
    conn = get_db()
    conn.execute("""
        INSERT INTO memories (key, value, category, importance, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            category = excluded.category,
            importance = excluded.importance,
            updated_at = datetime('now')
    """, (key, value, category, importance))
    conn.commit()
    conn.close()

def get_memory(key):
    conn = get_db()
    row = conn.execute("SELECT value FROM memories WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else None

def search_memories(query):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.key, m.value, m.category
        FROM memories_fts f
        JOIN memories m ON m.id = f.rowid
        WHERE memories_fts MATCH ?
        ORDER BY rank
        LIMIT 20
    """, (query,)).fetchall()
    conn.close()
    return [{"key": r["key"], "value": r["value"], "category": r["category"]} for r in rows]

def get_all_memories(category=None):
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT key, value, category, importance FROM memories WHERE category = ? ORDER BY importance DESC",
            (category,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT key, value, category, importance FROM memories ORDER BY category, importance DESC"
        ).fetchall()
    conn.close()
    return [{"key": r["key"], "value": r["value"], "category": r["category"], "importance": r["importance"]} for r in rows]

def log_session(session_id, role, content):
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content[:1000])
    )
    conn.commit()
    conn.close()

def add_inventory_item(barcode, name, qty=1):
    conn = get_db()
    conn.execute(
        "INSERT INTO inventory (barcode, name, qty) VALUES (?, ?, ?)",
        (barcode, name, qty)
    )
    conn.commit()
    conn.close()

def get_inventory():
    conn = get_db()
    rows = conn.execute("""
        SELECT name, barcode, SUM(qty) as total_qty, COUNT(*) as scan_count, MAX(scanned_at) as last_scan
        FROM inventory
        GROUP BY barcode, name
        ORDER BY last_scan DESC
    """).fetchall()
    conn.close()
    return [{"name": r["name"], "barcode": r["barcode"], "qty": r["total_qty"], "scans": r["scan_count"], "last_scan": r["last_scan"]} for r in rows]

def clear_inventory():
    conn = get_db()
    conn.execute("DELETE FROM inventory")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("✅ Memory database ready")
