import sqlite3
import json
import threading
import time
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use /tmp on Vercel/Serverless, local file otherwise
            if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
                self.db_path = "/tmp/vera.db"
            else:
                self.db_path = "vera.db"
        else:
            self.db_path = db_path
            
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Contexts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                scope TEXT,
                context_id TEXT,
                version INTEGER,
                payload TEXT,
                updated_at TEXT,
                PRIMARY KEY (scope, context_id)
            )
        """)
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                merchant_id TEXT,
                status TEXT DEFAULT 'active',
                last_strategy TEXT,
                last_send_ts REAL,
                is_ended INTEGER DEFAULT 0
            )
        """)
        
        # Turns table (history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                from_role TEXT,
                message TEXT,
                timestamp TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Suppression / State table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)

        # Analytics table for self-learning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                strategy TEXT PRIMARY KEY,
                sends INTEGER DEFAULT 0,
                successes INTEGER DEFAULT 0
            )
        """)

        conn.commit()

    # ─── Contexts ─────────────────────────────────────────────────────────────
    
    def set_context(self, scope: str, context_id: str, version: int, payload: Dict):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO contexts (scope, context_id, version, payload, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(scope, context_id) DO UPDATE SET
                version = excluded.version,
                payload = excluded.payload,
                updated_at = excluded.updated_at
        """, (scope, context_id, version, json.dumps(payload), datetime.now(timezone.utc).isoformat()))
        conn.commit()

    def get_context(self, scope: str, context_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT version, payload FROM contexts WHERE scope = ? AND context_id = ?", (scope, context_id)).fetchone()
        if row:
            return {"version": row["version"], "payload": json.loads(row["payload"])}
        return None

    def get_all_context_counts(self) -> Dict[str, int]:
        conn = self._get_conn()
        rows = conn.execute("SELECT scope, COUNT(*) as cnt FROM contexts GROUP BY scope").fetchall()
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        for row in rows:
            if row["scope"] in counts:
                counts[row["scope"]] = row["cnt"]
        return counts

    # ─── Conversations & Turns ────────────────────────────────────────────────
    
    def add_turn(self, conv_id: str, role: str, message: str):
        conn = self._get_conn()
        # Ensure conversation exists
        conn.execute("INSERT OR IGNORE INTO conversations (conversation_id) VALUES (?)", (conv_id,))
        # Add turn
        conn.execute("""
            INSERT INTO turns (conversation_id, from_role, message, timestamp)
            VALUES (?, ?, ?, ?)
        """, (conv_id, role, message, datetime.now(timezone.utc).isoformat()))
        conn.commit()

    def get_turns(self, conv_id: str, limit: int = 10) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT from_role, message, timestamp 
            FROM turns 
            WHERE conversation_id = ? 
            ORDER BY timestamp DESC LIMIT ?
        """, (conv_id, limit)).fetchall()
        return [{"from": r["from_role"], "msg": r["message"], "ts": r["timestamp"]} for r in reversed(rows)]

    def is_conv_ended(self, conv_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute("SELECT is_ended FROM conversations WHERE conversation_id = ?", (conv_id,)).fetchone()
        return bool(row["is_ended"]) if row else False

    def end_conversation(self, conv_id: str):
        conn = self._get_conn()
        conn.execute("UPDATE conversations SET is_ended = 1, status = 'ended' WHERE conversation_id = ?", (conv_id,))
        conn.commit()

    # ─── Merchant State (Cooldown/Strategy) ───────────────────────────────────
    
    def get_merchant_state(self, merchant_id: str) -> Dict[str, Any]:
        # Using conversations table to store merchant-specific persistent state for now
        conn = self._get_conn()
        row = conn.execute("SELECT last_strategy, last_send_ts FROM conversations WHERE merchant_id = ? OR conversation_id = ?", (merchant_id, f"meta_{merchant_id}")).fetchone()
        if row:
            return {"last_strategy": row["last_strategy"] or "", "last_send_ts": row["last_send_ts"] or 0.0}
        return {"last_strategy": "", "last_send_ts": 0.0}

    def update_merchant_state(self, merchant_id: str, strategy: str = None, send_ts: float = None):
        conn = self._get_conn()
        cid = f"meta_{merchant_id}"
        conn.execute("INSERT OR IGNORE INTO conversations (conversation_id, merchant_id) VALUES (?, ?)", (cid, merchant_id))
        if strategy is not None:
            conn.execute("UPDATE conversations SET last_strategy = ? WHERE conversation_id = ?", (strategy, cid))
        if send_ts is not None:
            conn.execute("UPDATE conversations SET last_send_ts = ? WHERE conversation_id = ?", (send_ts, cid))
        conn.commit()

    # ─── Suppression Keys ─────────────────────────────────────────────────────
    
    def is_suppressed(self, key: str) -> bool:
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM state WHERE key = ?", (f"suppress:{key}",)).fetchone()
        return row is not None

    def suppress_key(self, key: str):
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO state (key, value, updated_at) VALUES (?, ?, ?)", 
                     (f"suppress:{key}", "1", datetime.now(timezone.utc).isoformat()))
        conn.commit()

    def suppress_merchant(self, merchant_id: str, seconds: int):
        key = f"merchant_suppress:{merchant_id}"
        exp = time.time() + seconds
        conn = self._get_conn()
        conn.execute("INSERT OR REPLACE INTO state (key, value, updated_at) VALUES (?, ?, ?)",
                     (key, str(exp), datetime.now(timezone.utc).isoformat()))
        conn.commit()

    # ─── Analytics & Self-Learning ───────────────────────────────────────────
    
    def record_send(self, strategy: str):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO analytics (strategy, sends, successes) 
            VALUES (?, 1, 0)
            ON CONFLICT(strategy) DO UPDATE SET sends = sends + 1
        """, (strategy,))
        conn.commit()

    def record_success(self, strategy: str):
        conn = self._get_conn()
        conn.execute("""
            UPDATE analytics SET successes = successes + 1 WHERE strategy = ?
        """, (strategy,))
        conn.commit()

    def get_strategy_performance(self) -> Dict[str, float]:
        conn = self._get_conn()
        rows = conn.execute("SELECT strategy, sends, successes FROM analytics").fetchall()
        # Return win rate (successes / sends) with a baseline of 0.5
        perf = {}
        for r in rows:
            if r["sends"] > 0:
                perf[r["strategy"]] = r["successes"] / r["sends"]
        return perf

    def clear_all(self):
        conn = self._get_conn()
        conn.execute("DELETE FROM contexts")
        conn.execute("DELETE FROM conversations")
        conn.execute("DELETE FROM turns")
        conn.execute("DELETE FROM state")
        conn.commit()

db = Database()
