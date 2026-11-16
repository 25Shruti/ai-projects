
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "evaluations.db"


def save_evaluation(record: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_id TEXT NOT NULL,
                trace_id TEXT,
                record_json TEXT NOT NULL
            )
        """)

        cursor = conn.execute(
            """INSERT INTO evaluations
               (timestamp, alert_id, trace_id, record_json)
               VALUES (?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                record["alert_id"],
                record.get("trace_id"),
                json.dumps(record, default=str),
            ),
        )
    return cursor.lastrowid


def load_evaluations():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_id TEXT NOT NULL,
                trace_id TEXT,
                record_json TEXT NOT NULL
            )
        """)

        rows = conn.execute(
            "SELECT id, timestamp, record_json "
            "FROM evaluations ORDER BY id DESC"
        ).fetchall()

    return [
        {
            "run_id": row[0],
            "timestamp": row[1],
            **json.loads(row[2]),
        }
        for row in rows
    ]



def save_judge_result(run_id, judge_result):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS judge_evaluations (
                run_id INTEGER PRIMARY KEY,
                result_json TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES evaluations(id)
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO judge_evaluations
            (run_id, result_json)
            VALUES (?, ?)
        """, (run_id, json.dumps(judge_result, default=str)))


def load_judge_result(run_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS judge_evaluations (
                run_id INTEGER PRIMARY KEY,
                result_json TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES evaluations(id)
            )
        """)

        row = conn.execute(
            "SELECT result_json FROM judge_evaluations WHERE run_id = ?",
            (run_id,)
        ).fetchone()

    return json.loads(row[0]) if row else None
