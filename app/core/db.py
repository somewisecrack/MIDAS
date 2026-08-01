"""
db.py — SQLite schema and query helpers for MIDAS web app.
Single midas.db file at /data/midas.db relative to the project root.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve DB path relative to this file's location (app/core/ → project root/data/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = _PROJECT_ROOT / "data" / "midas.db"


class _Connection(sqlite3.Connection):
    """
    Connection that closes itself when used as a context manager.

    Plain sqlite3 connections only commit/rollback on ``with`` exit — they do
    NOT close. Every helper here uses ``with get_conn() as conn:``, so without
    this the connections leaked until the process ran out of file descriptors
    and every query failed with "unable to open database file".
    """

    def __exit__(self, *exc):
        try:
            super().__exit__(*exc)
        finally:
            self.close()


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=_Connection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ohlcv_cache (
            id       INTEGER PRIMARY KEY,
            ticker   TEXT NOT NULL,
            date     TEXT NOT NULL,
            open     REAL,
            high     REAL,
            low      REAL,
            close    REAL,
            volume   INTEGER,
            fetched_at TEXT,
            UNIQUE(ticker, date)
        );

        CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date
            ON ohlcv_cache(ticker, date);

        CREATE TABLE IF NOT EXISTS backtest_runs (
            id              TEXT PRIMARY KEY,
            created_at      TEXT NOT NULL,
            ticker          TEXT NOT NULL,
            strategy_names  TEXT NOT NULL,   -- JSON array
            date_from       TEXT NOT NULL,
            date_to         TEXT NOT NULL,
            stats           TEXT,            -- JSON blob
            label           TEXT             -- user-editable
        );

        CREATE TABLE IF NOT EXISTS backtest_trades (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id        TEXT NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
            ticker        TEXT,
            strategy      TEXT,
            entry_date    TEXT,
            exit_date     TEXT,
            entry_price   REAL,
            exit_price    REAL,
            direction     TEXT,
            return_pct    REAL,
            holding_days  INTEGER,
            mfe           REAL,
            mae           REAL
        );

        CREATE INDEX IF NOT EXISTS idx_trades_run
            ON backtest_trades(run_id);

        CREATE TABLE IF NOT EXISTS pattern_searches (
            id             TEXT PRIMARY KEY,
            created_at     TEXT NOT NULL,
            ticker         TEXT NOT NULL,
            query_type     TEXT NOT NULL,   -- 'text' | 'image'
            query          TEXT,
            matched_windows TEXT            -- JSON array
        );
        """)

        # Migration: Add ticker column to backtest_trades if it doesn't exist
        try:
            conn.execute("ALTER TABLE backtest_trades ADD COLUMN ticker TEXT")
            # Update existing trades to use their parent run's ticker
            conn.execute("""
                UPDATE backtest_trades
                SET ticker = (SELECT ticker FROM backtest_runs WHERE id = backtest_trades.run_id)
                WHERE ticker IS NULL
            """)
        except sqlite3.OperationalError:
            pass  # column already exists


# ── OHLCV Cache ────────────────────────────────────────────────────────────────

def upsert_ohlcv(rows: List[Dict[str, Any]]):
    """Insert or replace OHLCV rows. `rows` each need: ticker, date, open, high, low, close, volume."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO ohlcv_cache (ticker, date, open, high, low, close, volume, fetched_at)
               VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :fetched_at)
               ON CONFLICT(ticker, date) DO UPDATE SET
                 open=excluded.open, high=excluded.high, low=excluded.low,
                 close=excluded.close, volume=excluded.volume, fetched_at=excluded.fetched_at""",
            [{**r, "fetched_at": now} for r in rows],
        )


def get_ohlcv(ticker: str, date_from: str, date_to: str) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT date, open, high, low, close, volume
               FROM ohlcv_cache
               WHERE ticker=? AND date>=? AND date<=?
               ORDER BY date""",
            (ticker.upper(), date_from, date_to),
        ).fetchall()
    return [dict(r) for r in rows]


def get_cached_tickers() -> List[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM ohlcv_cache ORDER BY ticker"
        ).fetchall()
    return [r["ticker"] for r in rows]


def get_ticker_date_range(ticker: str) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as rows FROM ohlcv_cache WHERE ticker=?",
            (ticker.upper(),),
        ).fetchone()
    if row and row["rows"] > 0:
        return dict(row)
    return None


# ── Backtest Runs ──────────────────────────────────────────────────────────────

def save_backtest_run(
    ticker: str,
    strategy_names: List[str],
    date_from: str,
    date_to: str,
    stats: Dict,
    trades: List[Dict],
    label: str = "",
) -> str:
    run_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO backtest_runs (id, created_at, ticker, strategy_names, date_from, date_to, stats, label)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, now, ticker.upper(), json.dumps(strategy_names), date_from, date_to, json.dumps(stats), label),
        )
        if trades:
            # Ensure each trade dict has the ticker, defaulting to the run's ticker
            for t in trades:
                if "ticker" not in t:
                    t["ticker"] = ticker.upper()

            conn.executemany(
                """INSERT INTO backtest_trades
                   (run_id, ticker, strategy, entry_date, exit_date, entry_price, exit_price,
                    direction, return_pct, holding_days, mfe, mae)
                   VALUES (:run_id, :ticker, :strategy, :entry_date, :exit_date, :entry_price, :exit_price,
                    :direction, :return_pct, :holding_days, :mfe, :mae)""",
                [{**t, "run_id": run_id} for t in trades],
            )
    return run_id


def list_backtest_runs() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, created_at, ticker, strategy_names, date_from, date_to, stats, label
               FROM backtest_runs ORDER BY created_at DESC LIMIT 100"""
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["strategy_names"] = json.loads(d["strategy_names"] or "[]")
        d["stats"] = json.loads(d["stats"] or "{}")
        result.append(d)
    return result


def get_backtest_run(run_id: str) -> Optional[Dict]:
    with get_conn() as conn:
        run = conn.execute(
            "SELECT * FROM backtest_runs WHERE id=?", (run_id,)
        ).fetchone()
        if not run:
            return None
        trades = conn.execute(
            "SELECT * FROM backtest_trades WHERE run_id=? ORDER BY entry_date", (run_id,)
        ).fetchall()
    d = dict(run)
    d["strategy_names"] = json.loads(d["strategy_names"] or "[]")
    d["stats"] = json.loads(d["stats"] or "{}")
    d["trades"] = [dict(t) for t in trades]
    return d


def delete_backtest_run(run_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM backtest_runs WHERE id=?", (run_id,))


def update_backtest_run_label(run_id: str, label: str):
    with get_conn() as conn:
        conn.execute("UPDATE backtest_runs SET label=? WHERE id=?", (label, run_id))


# ── Pattern Searches ───────────────────────────────────────────────────────────

def save_pattern_search(ticker: str, query_type: str, query: str, matched_windows: List[Dict]) -> str:
    search_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO pattern_searches (id, created_at, ticker, query_type, query, matched_windows)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (search_id, now, ticker.upper(), query_type, query, json.dumps(matched_windows)),
        )
    return search_id
