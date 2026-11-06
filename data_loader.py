import os
import glob
import pandas as pd
import streamlit as st
from config import DATA_DIR


@st.cache_data(ttl=300)
def find_data_files():
    cellhr_pattern = os.path.join(DATA_DIR, "Cellhr Daily review*.xlsx")
    summary_pattern = os.path.join(DATA_DIR, "SUMMARY_AYY*.xlsx")
    cellhr_files = sorted(glob.glob(cellhr_pattern))
    summary_files = sorted(glob.glob(summary_pattern))
    return cellhr_files, summary_files


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
def load_cellhr_detail(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Cell_h Detail", header=1)
        # Clean column names: replace newlines with spaces
        df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]

        # Drop rows where SITE_ID is missing
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
                pass  # Skip — this col is actually Start Time in the Excel
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

        # Also try to find Cell*h if not yet matched
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


@st.cache_data(ttl=300)
def load_tco_power(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="TCO power")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_mytel_power(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Mytel power")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_tx_report(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="TX report")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_tx_detail(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="TX Detail")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_hub_down(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Hub down")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_manpower(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Manpower")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_site_database(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="AYY_Site database")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_cable_routes(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Cable Routes Database")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_flood_sites(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Flood sites")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_mw_links(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="AYY_MW link")
        return df
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
