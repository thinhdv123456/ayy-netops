import io
import pandas as pd
import streamlit as st


def _map_cellhr_columns(df):
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


def _safe_read(file_bytes, sheet, header=0):
    try:
        return pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=header)
    except Exception:
        return pd.DataFrame()


def process_uploads(cellhr_bytes, summary_bytes=None):
    data = {}

    try:
        raw = pd.read_excel(io.BytesIO(cellhr_bytes), sheet_name="Cell_h Detail", header=1)
        df, col_map = _map_cellhr_columns(raw)
        data["cellhr_detail"] = df
        data["col_map"] = col_map
    except Exception as e:
        data["cellhr_detail"] = pd.DataFrame()
        data["col_map"] = {}
        data["cellhr_error"] = str(e)

    try:
        raw_rpt = pd.read_excel(io.BytesIO(cellhr_bytes), sheet_name="Cell_h Report", header=None)
        categories = []
        for idx in range(5, 15):
            row = raw_rpt.iloc[idx]
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
        data["cellhr_report"] = categories
    except Exception:
        data["cellhr_report"] = []

    data["tco_power"] = _safe_read(cellhr_bytes, "TCO power")
    data["mytel_power"] = _safe_read(cellhr_bytes, "Mytel power")
    data["tx_report"] = _safe_read(cellhr_bytes, "TX report")
    data["tx_detail"] = _safe_read(cellhr_bytes, "TX Detail")
    data["hub_down"] = _safe_read(cellhr_bytes, "Hub down")

    if summary_bytes:
        data["manpower"] = _safe_read(summary_bytes, "Manpower")
        data["site_db"] = _safe_read(summary_bytes, "AYY_Site database")
        data["cable_routes"] = _safe_read(summary_bytes, "Cable Routes Database")
        data["flood_sites"] = _safe_read(summary_bytes, "Flood sites")
        data["mw_links"] = _safe_read(summary_bytes, "AYY_MW link")
    else:
        for key in ["manpower", "site_db", "cable_routes", "flood_sites", "mw_links"]:
            data[key] = pd.DataFrame()

    data["has_data"] = True
    st.session_state["app_data"] = data
    return data


def get_data():
    return st.session_state.get("app_data")


def require_data(lang="vi"):
    data = get_data()
    if data and data.get("has_data"):
        return data
    st.warning("📂 " + (
        "Chưa có dữ liệu. Vui lòng vào trang **Tổng quan** để upload file Excel."
        if lang == "vi" else
        "No data loaded. Please go to **Dashboard** to upload Excel files."
    ))
    st.stop()
