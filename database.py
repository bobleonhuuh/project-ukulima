"""Ukulima database layer.

Supports two engines behind one small interface so the rest of the app never
changes:

  * sqlite  (default) - zero-config local file, great for development.
  * mysql   (MariaDB) - set DB_ENGINE=mysql plus your connection details.

Configuration is read from environment variables, optionally loaded from a
`.env` file next to this module (see .env.example). Existing environment
variables always win over the file, so you can override at runtime.

The wrapper normalises the two drivers:
  * queries are written with `?` placeholders (converted to `%s` for MySQL);
  * rows come back key-accessible (sqlite3.Row / dict), so `row["col"]`,
    `cur.fetchone()`, `cur.fetchall()` and `cur.lastrowid` all behave the same.
"""
import os
import re
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))


def _load_dotenv():
    """Minimal .env loader (no external dependency). Does not override real env."""
    path = os.path.join(BASE, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()

ENGINE = os.environ.get("DB_ENGINE", "sqlite").strip().lower()
SQLITE_PATH = os.environ.get("UKULIMA_DB", os.path.join(BASE, "ukulima.db"))

MYSQL = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "ukulima"),
}

# Datetimes are stored as "YYYY-MM-DD HH:MM" strings on both engines so the
# existing string comparisons (created >= since) keep working identically.
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
  phone TEXT, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'farmer', county TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, crop TEXT NOT NULL, county TEXT NOT NULL,
  lat REAL, lng REAL, growth_stage TEXT, symptoms TEXT, tags TEXT, photo TEXT,
  ai_label TEXT, ai_conf REAL, ai_source TEXT, alternatives TEXT, severity TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'pending', escalated INTEGER DEFAULT 0, officer_id INTEGER, officer_label TEXT,
  officer_notes TEXT, created TEXT, reviewed TEXT);
CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, county TEXT, pest TEXT, message TEXT, level TEXT DEFAULT 'warning',
  created_by INTEGER, auto INTEGER DEFAULT 0, created TEXT);
"""

MYSQL_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users(
      id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(120) NOT NULL,
      email VARCHAR(190) NOT NULL UNIQUE,
      phone VARCHAR(40),
      password VARCHAR(255) NOT NULL,
      role VARCHAR(20) NOT NULL DEFAULT 'farmer',
      county VARCHAR(80),
      created VARCHAR(20)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS reports(
      id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT NOT NULL,
      crop VARCHAR(60) NOT NULL,
      county VARCHAR(80) NOT NULL,
      lat DOUBLE, lng DOUBLE,
      growth_stage VARCHAR(40),
      symptoms TEXT, tags TEXT, photo VARCHAR(255),
      ai_label VARCHAR(60), ai_conf DOUBLE, ai_source VARCHAR(40), alternatives TEXT,
      severity VARCHAR(10) DEFAULT 'medium',
      status VARCHAR(20) DEFAULT 'pending',
      escalated INT DEFAULT 0,
      officer_id INT, officer_label VARCHAR(60), officer_notes TEXT,
      created VARCHAR(20), reviewed VARCHAR(20),
      INDEX idx_reports_county (county), INDEX idx_reports_created (created)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS alerts(
      id INT AUTO_INCREMENT PRIMARY KEY,
      county VARCHAR(80), pest VARCHAR(60), message TEXT,
      level VARCHAR(10) DEFAULT 'warning',
      created_by INT, auto INT DEFAULT 0, created VARCHAR(20)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


class DB:
    """Thin uniform wrapper over a sqlite3 or PyMySQL connection."""

    def __init__(self, conn, engine):
        self._conn = conn
        self._engine = engine

    @property
    def engine(self):
        return self._engine

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        if self._engine == "mysql":
            sql = sql.replace("?", "%s")
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def _mysql_database_name_safe():
    return bool(re.fullmatch(r"[A-Za-z0-9_]+", MYSQL["database"]))


def _ensure_mysql_database():
    """Create the target database if it does not exist yet (convenience)."""
    import pymysql
    if not _mysql_database_name_safe():
        raise ValueError("DB_NAME may only contain letters, numbers and underscores.")
    conn = pymysql.connect(host=MYSQL["host"], port=MYSQL["port"], user=MYSQL["user"],
                           password=MYSQL["password"], charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL['database']}` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
    finally:
        conn.close()


def connect():
    """Return a DB wrapper using the configured engine."""
    if ENGINE == "mysql":
        import pymysql
        conn = pymysql.connect(host=MYSQL["host"], port=MYSQL["port"], user=MYSQL["user"],
                               password=MYSQL["password"], database=MYSQL["database"],
                               charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
                               autocommit=False)
        return DB(conn, "mysql")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return DB(conn, "sqlite")


def init():
    """Create the schema if needed. Safe to call on every start."""
    if ENGINE == "mysql":
        _ensure_mysql_database()
        con = connect()
        try:
            for stmt in MYSQL_SCHEMA:
                con.execute(stmt)
            con.commit()
        finally:
            con.close()
    else:
        con = sqlite3.connect(SQLITE_PATH)
        con.executescript(SQLITE_SCHEMA)
        con.commit()
        con.close()