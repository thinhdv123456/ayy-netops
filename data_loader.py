import os
import glob
import hashlib
import pandas as pd
import streamlit as st
from config import DATA_DIR

CACHE_DIR = os.path.join(DATA_DIR, ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL = 3600


def _parquet_path(filepath, sheet):
    key = hashlib.md5(f"{filepath}:{sheet}:{os.path.getmtime(filepath)}".encode()).hexdigest()[:12]
    safe_name = os.path.basename(filepath).replace(" ", "_").replace(".", "_")
    return os.path.join(CACHE_DIR, f"{safe_name}_{sheet}_{key}.parquet")


def _read_sheet(filepath, sheet, header=0):
    pq = _parquet_path(filepath, sheet)
    if os.path.exists(pq):
        return pd.read_parquet(pq)
    df = pd.read_excel(filepath, sheet_name=sheet, header=header)
    try:
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).replace("nan", pd.NA)
        df.to_parquet(pq, index=False)
    except Exception:
        pass
    return df


@st.cache_data(ttl=CACHE_TTL)
def find_data_files():
    cellhr_pattern = os.path.join(DATA_DIR, "Cellhr Daily review*.xlsx")
    summary_pattern = os.path.join(DATA_DIR, "SUMMARY_AYY*.xlsx")
    cellhr_files = sorted(glob.glob(cellhr_pattern))
    summary_files = sorted(glob.glob(summary_pattern))
    return cellhr_files, summary_files


@st.cache_data(ttl=CACHE_TTL)
def load_cellhr_report(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Cell_h Report", header=None)
        categories = []
        for idx in range(5, 15):
            row = df.iloc[idx]
            cat_name = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
            if not cat_name:
                continue
            daily_values = {}
            for col_idx in range(5, min(len(row), 35)):
                val = row.iloc[col_idx]
                if pd.notna(val):
                    try:
                        daily_values[col_idx] = float(val)
                    except (ValueError, TypeError):
                        pass
            categories.append({"category": cat_name, "values": daily_values})
        return categories
    except Exception as e:
        st.error(f"Error loading Cell_h Report: {e}")
        return []


@st.cache_data(ttl=CACHE_TTL)
def load_cellhr_detail(filepath):
    try:
        df = _read_sheet(filepath, "Cell_h Detail", header=1)
        df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]

        site_col_candidates = [c for c in df.columns if "SITE_ID" in c.upper()]
        if site_col_candidates:
            df = df.dropna(subset=[site_col_candidates[0]])

        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower == "site_id":
                col_map["site_id"] = col
            elif col_lower == "owner":
                col_map["owner"] = col
            elif "power model" in col_lower:
                col_map["power_model"] = col
            elif col_lower == "reason_level1":
                col_map["reason_level1"] = col
            elif col_lower == "reason_level3":
                col_map["reason_level3"] = col
            elif col_lower == "date":
                col_map["date"] = col
            elif col_lower == "cell name":
                col_map["cell_name"] = col
            elif col_lower == "start time":
                col_map["start_time"] = col
            elif col_lower == "end time":
                col_map["end_time"] = col
            elif "duration after reduction" in col_lower:
                col_map["duration"] = col
            elif col_lower == "duration" and "duration" not in col_map:
                pass
            elif "vcm branch" in col_lower:
                col_map["branch"] = col
            elif col_lower == "team":
                col_map["team"] = col
            elif "site type" in col_lower:
                col_map["site_type"] = col
            elif "site class" in col_lower:
                col_map["site_class"] = col
            elif "day/night" in col_lower:
                col_map["day_night"] = col
            elif "unsafe" in col_lower:
                col_map["unsafe"] = col
            elif "fm reason" in col_lower:
                col_map["fm_reason"] = col
            elif "cell*h" in col_lower and "after reduction" in col_lower and "before" not in col_lower and ">14days" in col_lower:
                col_map["cellhr"] = col
            elif "cell*h" in col_lower and "after reduction" in col_lower and "before" not in col_lower and ">14days" not in col_lower:
                if "cellhr" not in col_map:
                    col_map["cellhr"] = col
            elif "noc" in col_lower and "comment" in col_lower:
                col_map["noc_comment"] = col
            elif "alarm group" in col_lower:
                col_map["alarm_group"] = col
            elif "cabinet" in col_lower:
                col_map["cabinet_type"] = col

        if "cellhr" not in col_map:
            for col in df.columns:
                if "cell*h" in col.lower():
                    col_map["cellhr"] = col
                    break

        if "date" in col_map:
            df[col_map["date"]] = pd.to_datetime(df[col_map["date"]], errors="coerce")
        if "duration" in col_map:
            df[col_map["duration"]] = pd.to_numeric(df[col_map["duration"]], errors="coerce")
        if "cellhr" in col_map:
            df[col_map["cellhr"]] = pd.to_numeric(df[col_map["cellhr"]], errors="coerce")

        return df, col_map
    except Exception as e:
        st.error(f"Error loading Cell_h Detail: {e}")
        return pd.DataFrame(), {}


@st.cache_data(ttl=CACHE_TTL)
def load_tco_power(filepath):
    try:
        return _read_sheet(filepath, "TCO power")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_mytel_power(filepath):
    try:
        return _read_sheet(filepath, "Mytel power")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_tx_report(filepath):
    try:
        return _read_sheet(filepath, "TX report")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_tx_detail(filepath):
    try:
        return _read_sheet(filepath, "TX Detail")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_hub_down(filepath):
    try:
        return _read_sheet(filepath, "Hub down")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_manpower(filepath):
    try:
        return _read_sheet(filepath, "Manpower")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_site_database(filepath):
    try:
        return _read_sheet(filepath, "AYY_Site database")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_cable_routes(filepath):
    try:
        return _read_sheet(filepath, "Cable Routes Database")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_flood_sites(filepath):
    try:
        return _read_sheet(filepath, "Flood sites")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def load_mw_links(filepath):
    try:
        return _read_sheet(filepath, "AYY_MW link")
    except Exception:
        return pd.DataFrame()


def get_all_data(cellhr_file, summary_file):
    data = {}
    data["cellhr_report"] = load_cellhr_report(cellhr_file)
    data["cellhr_detail"], data["col_map"] = load_cellhr_detail(cellhr_file)
    data["tco_power"] = load_tco_power(cellhr_file)
    data["mytel_power"] = load_mytel_power(cellhr_file)
    data["tx_report"] = load_tx_report(cellhr_file)
    data["tx_detail"] = load_tx_detail(cellhr_file)
    data["hub_down"] = load_hub_down(cellhr_file)

    if summary_file:
        data["manpower"] = load_manpower(summary_file)
        data["site_db"] = load_site_database(summary_file)
        data["cable_routes"] = load_cable_routes(summary_file)
        data["flood_sites"] = load_flood_sites(summary_file)
        data["mw_links"] = load_mw_links(summary_file)
    else:
        data["manpower"] = pd.DataFrame()
        data["site_db"] = pd.DataFrame()
        data["cable_routes"] = pd.DataFrame()
        data["flood_sites"] = pd.DataFrame()
        data["mw_links"] = pd.DataFrame()

    return data
