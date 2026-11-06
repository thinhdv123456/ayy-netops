import os
import sqlite3
import hashlib
import pandas as pd
import streamlit as st
from datetime import datetime
from config import DATA_DIR

DB_PATH = os.path.join(DATA_DIR, "ayy_netops.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL UNIQUE,
            import_date TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            total_records INTEGER,
            total_cellhr REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cellhr_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            site_id TEXT,
            owner TEXT,
            power_model TEXT,
            reason_level1 TEXT,
            reason_level3 TEXT,
            noc_comment TEXT,
            event_date TEXT,
            cell_name TEXT,
            start_time TEXT,
            end_time TEXT,
            duration REAL,
            branch TEXT,
            site_type TEXT,
            site_class TEXT,
            team TEXT,
            cabinet_type TEXT,
            alarm_group TEXT,
            day_night TEXT,
            unsafe TEXT,
            fm_reason TEXT,
            cellhr REAL,
            FOREIGN KEY (import_id) REFERENCES import_log(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tco_power_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            site_id TEXT,
            owner TEXT,
            reason TEXT,
            duration REAL,
            cellhr REAL,
            event_date TEXT,
            FOREIGN KEY (import_id) REFERENCES import_log(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS mytel_power_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            site_id TEXT,
            reason TEXT,
            duration REAL,
            cellhr REAL,
            event_date TEXT,
            FOREIGN KEY (import_id) REFERENCES import_log(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tx_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            site_id TEXT,
            route TEXT,
            reason TEXT,
            duration REAL,
            start_time TEXT,
            end_time TEXT,
            event_date TEXT,
            FOREIGN KEY (import_id) REFERENCES import_log(id)
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_cellhr_site ON cellhr_events(site_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cellhr_date ON cellhr_events(event_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cellhr_reason ON cellhr_events(reason_level1)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cellhr_team ON cellhr_events(team)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tco_site ON tco_power_events(site_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mytel_site ON mytel_power_events(site_id)")

    conn.commit()
    conn.close()


def file_hash(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def is_file_imported(filepath):
    fh = file_hash(filepath)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, filename, import_date FROM import_log WHERE file_hash = ?", (fh,))
    row = cur.fetchone()
    conn.close()
    if row:
        return True, row
    return False, None


def import_cellhr_file(filepath, detail_df, col_map, tco_df, mytel_df, tx_df):
    fh = file_hash(filepath)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM import_log WHERE file_hash = ?", (fh,))
    if cur.fetchone():
        conn.close()
        return False, "File already imported"

    dates = []
    if "date" in col_map and not detail_df.empty:
        date_col = detail_df[col_map["date"]].dropna()
        if len(date_col) > 0:
            dates = pd.to_datetime(date_col, errors="coerce").dropna()

    period_start = str(dates.min()) if len(dates) > 0 else None
    period_end = str(dates.max()) if len(dates) > 0 else None
    total_records = len(detail_df)
    total_cellhr = detail_df[col_map["cellhr"]].sum() if "cellhr" in col_map else 0

    cur.execute("""
        INSERT INTO import_log (filename, file_hash, import_date, period_start, period_end, total_records, total_cellhr)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (os.path.basename(filepath), fh, datetime.now().isoformat(), period_start, period_end, total_records, total_cellhr))
    import_id = cur.lastrowid

    if not detail_df.empty:
        records = []
        for _, row in detail_df.iterrows():
            def g(key):
                if key in col_map:
                    val = row.get(col_map[key])
                    if pd.notna(val):
                        return str(val)
                return None

            records.append((
                import_id,
                g("site_id"), g("owner"), g("power_model"),
                g("reason_level1"), g("reason_level3"), g("noc_comment"),
                g("date"), g("cell_name"), g("start_time"), g("end_time"),
                float(row[col_map["duration"]]) if "duration" in col_map and pd.notna(row.get(col_map.get("duration"))) else None,
                g("branch"), g("site_type"), g("site_class"), g("team"),
                g("cabinet_type"), g("alarm_group"), g("day_night"),
                g("unsafe"), g("fm_reason"),
                float(row[col_map["cellhr"]]) if "cellhr" in col_map and pd.notna(row.get(col_map.get("cellhr"))) else None,
            ))

        cur.executemany("""
            INSERT INTO cellhr_events (import_id, site_id, owner, power_model,
                reason_level1, reason_level3, noc_comment, event_date, cell_name,
                start_time, end_time, duration, branch, site_type, site_class,
                team, cabinet_type, alarm_group, day_night, unsafe, fm_reason, cellhr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

    if not tco_df.empty:
        tco_records = []
        for _, row in tco_df.iterrows():
            site_id = None
            owner = None
            reason = None
            duration = None
            cellhr_val = None
            event_date = None
            for col in tco_df.columns:
                cl = str(col).lower()
                if "site" in cl and "id" in cl:
                    site_id = str(row[col]) if pd.notna(row[col]) else None
                elif cl == "owner":
                    owner = str(row[col]) if pd.notna(row[col]) else None
                elif "reason" in cl:
                    reason = str(row[col]) if pd.notna(row[col]) else None
                elif "duration" in cl:
                    duration = float(row[col]) if pd.notna(row[col]) else None
                elif "cell*h" in cl or "cellhr" in cl:
                    cellhr_val = float(row[col]) if pd.notna(row[col]) else None
                elif "date" in cl:
                    event_date = str(row[col]) if pd.notna(row[col]) else None
            tco_records.append((import_id, site_id, owner, reason, duration, cellhr_val, event_date))

        cur.executemany("""
            INSERT INTO tco_power_events (import_id, site_id, owner, reason, duration, cellhr, event_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, tco_records)

    if not mytel_df.empty:
        mytel_records = []
        for _, row in mytel_df.iterrows():
            site_id = None
            reason = None
            duration = None
            cellhr_val = None
            event_date = None
            for col in mytel_df.columns:
                cl = str(col).lower()
                if "site" in cl and "id" in cl:
                    site_id = str(row[col]) if pd.notna(row[col]) else None
                elif "reason" in cl:
                    reason = str(row[col]) if pd.notna(row[col]) else None
                elif "duration" in cl:
                    duration = float(row[col]) if pd.notna(row[col]) else None
                elif "cell*h" in cl or "cellhr" in cl:
                    cellhr_val = float(row[col]) if pd.notna(row[col]) else None
                elif "date" in cl:
                    event_date = str(row[col]) if pd.notna(row[col]) else None
            mytel_records.append((import_id, site_id, reason, duration, cellhr_val, event_date))

        cur.executemany("""
            INSERT INTO mytel_power_events (import_id, site_id, reason, duration, cellhr, event_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, mytel_records)

    conn.commit()
    conn.close()
    return True, f"Imported {total_records} records"


def get_import_history():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM import_log ORDER BY import_date DESC", conn)
    conn.close()
    return df


def query_cellhr_events(where_clause="1=1", params=None):
    conn = get_connection()
    df = pd.read_sql_query(
        f"SELECT * FROM cellhr_events WHERE {where_clause}",
        conn, params=params or []
    )
    conn.close()
    return df


def query_cellhr_summary(group_by="event_date", where_clause="1=1", params=None):
    conn = get_connection()
    df = pd.read_sql_query(
        f"""SELECT {group_by},
            COUNT(*) as event_count,
            SUM(cellhr) as total_cellhr,
            COUNT(DISTINCT site_id) as site_count,
            AVG(duration) as avg_duration
        FROM cellhr_events
        WHERE {where_clause}
        GROUP BY {group_by}
        ORDER BY total_cellhr DESC""",
        conn, params=params or []
    )
    conn.close()
    return df


def query_site_history(site_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT event_date, start_time, end_time, duration,
            reason_level1, reason_level3, cellhr, team, fm_reason, noc_comment
        FROM cellhr_events
        WHERE site_id = ?
        ORDER BY event_date DESC, start_time DESC""",
        conn, params=[site_id]
    )
    conn.close()
    return df


def query_weekly_comparison(week1_start, week1_end, week2_start, week2_end):
    conn = get_connection()
    w1 = pd.read_sql_query(
        """SELECT reason_level1, SUM(cellhr) as cellhr, COUNT(DISTINCT site_id) as sites
        FROM cellhr_events WHERE event_date BETWEEN ? AND ?
        GROUP BY reason_level1""",
        conn, params=[week1_start, week1_end]
    )
    w2 = pd.read_sql_query(
        """SELECT reason_level1, SUM(cellhr) as cellhr, COUNT(DISTINCT site_id) as sites
        FROM cellhr_events WHERE event_date BETWEEN ? AND ?
        GROUP BY reason_level1""",
        conn, params=[week2_start, week2_end]
    )
    conn.close()
    return w1, w2


def get_all_dates():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT DISTINCT event_date FROM cellhr_events WHERE event_date IS NOT NULL ORDER BY event_date",
        conn
    )
    conn.close()
    return df


def get_all_sites():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT DISTINCT site_id FROM cellhr_events WHERE site_id IS NOT NULL ORDER BY site_id",
        conn
    )
    conn.close()
    return df["site_id"].tolist()


init_database()
