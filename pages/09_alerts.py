import os
import streamlit as st
import pandas as pd
from config import CELLHR_TARGET
from i18n import t
from session_data import require_data
from database import query_cellhr_events, get_import_history

lang = st.session_state.get("lang", "vi")
st.markdown(f"## ⚠️ {t('smart_alerts', lang)}")

data = require_data(lang)
detail_df, col_map = data["cellhr_detail"], data["col_map"]

if detail_df.empty:
    st.warning(t("no_data", lang))
    st.stop()

# === THRESHOLD ALERTS ===
st.subheader(f"🚨 {t('threshold_alert', lang)}")

if "date" in col_map and "cellhr" in col_map:
    daily = detail_df.groupby(col_map["date"])[col_map["cellhr"]].sum().reset_index()
    daily.columns = ["date", "cellhr"]
    over_days = daily[daily["cellhr"] > CELLHR_TARGET]

    if len(over_days) > 0:
        st.error(f"🔴 **{len(over_days)}/{len(daily)}** " +
                 (f"ngày vượt ngưỡng {CELLHR_TARGET:,} Cell*h" if lang == "vi"
                  else f"days exceed {CELLHR_TARGET:,} Cell*h threshold"))
        for _, row in over_days.iterrows():
            excess = row["cellhr"] - CELLHR_TARGET
            pct = (excess / CELLHR_TARGET * 100)
            st.warning(
                f"📅 {str(row['date'])[:10]} — **{row['cellhr']:,.0f}** Cell*h "
                f"(+{excess:,.0f}, {pct:.0f}% {'vượt' if lang == 'vi' else 'over'})"
            )
    else:
        st.success(f"✅ {'Tất cả ngày đều dưới ngưỡng' if lang == 'vi' else 'All days within threshold'}")

st.divider()

# === RECURRING FAULTS ===
st.subheader(f"🔄 {t('recurring_fault', lang)}")

if "site_id" in col_map and "cellhr" in col_map:
    site_counts = detail_df.groupby(col_map["site_id"]).agg({
        col_map["cellhr"]: ["sum", "count"],
    }).reset_index()
    site_counts.columns = ["site_id", "total_cellhr", "event_count"]

    recurring = site_counts[site_counts["event_count"] >= 5].sort_values("event_count", ascending=False)

    if recurring.empty:
        st.success(f"✅ {'Không có trạm lỗi lặp >= 5 lần' if lang == 'vi' else 'No sites with >= 5 recurring events'}")
    else:
        st.warning(f"⚠️ **{len(recurring)}** " +
                   ("trạm có >= 5 sự kiện" if lang == "vi" else "sites with >= 5 events"))
        st.dataframe(recurring.rename(columns={
            "site_id": t("site_id", lang),
            "total_cellhr": t("cellhr_value", lang),
            "event_count": t("count", lang),
        }), use_container_width=True, hide_index=True)

st.divider()

# === ANOMALY DETECTION ===
st.subheader(f"🔍 {t('anomaly_detected', lang)}")

if "reason_level1" in col_map and "date" in col_map and "cellhr" in col_map:
    daily_cause = detail_df.groupby([col_map["date"], col_map["reason_level1"]])[col_map["cellhr"]].sum().reset_index()
    daily_cause.columns = ["date", "cause", "cellhr"]

    cause_stats = daily_cause.groupby("cause")["cellhr"].agg(["mean", "std"]).reset_index()
    cause_stats.columns = ["cause", "mean", "std"]

    anomalies = []
    for _, row in daily_cause.iterrows():
        stats = cause_stats[cause_stats["cause"] == row["cause"]]
        if not stats.empty:
            mean_val = stats["mean"].iloc[0]
            std_val = stats["std"].iloc[0]
            if std_val > 0 and row["cellhr"] > mean_val + 2 * std_val:
                anomalies.append({
                    t("date", lang): str(row["date"])[:10],
                    t("reason", lang): row["cause"],
                    "Cell*h": round(row["cellhr"], 0),
                    "Mean": round(mean_val, 0),
                    "Std": round(std_val, 0),
                    "Z-score": round((row["cellhr"] - mean_val) / std_val, 1),
                })

    if anomalies:
        st.warning(f"⚠️ **{len(anomalies)}** " +
                   ("bất thường phát hiện (>2σ)" if lang == "vi" else "anomalies detected (>2σ)"))
        st.dataframe(pd.DataFrame(anomalies), use_container_width=True, hide_index=True)
    else:
        st.success(f"✅ {'Không có bất thường' if lang == 'vi' else 'No anomalies detected'}")

st.divider()

# === ALERTS CONFIGURATION ===
st.subheader(f"⚙️ {'Cấu hình cảnh báo' if lang == 'vi' else 'Alert Configuration'}")

with st.expander("Threshold Settings"):
    new_target = st.number_input(
        "Cell*h " + t("target", lang) + " (" + t("daily", lang) + ")",
        min_value=500, max_value=20000, value=CELLHR_TARGET, step=100,
    )
    recurring_threshold = st.number_input(
        ("Ngưỡng lỗi lặp (events)" if lang == "vi" else "Recurring fault threshold (events)"),
        min_value=2, max_value=20, value=5,
    )
    anomaly_sigma = st.number_input(
        ("Ngưỡng bất thường (σ)" if lang == "vi" else "Anomaly threshold (σ)"),
        min_value=1.0, max_value=5.0, value=2.0, step=0.5,
    )
    st.info("💡 " + ("Các thay đổi sẽ áp dụng khi tải lại trang" if lang == "vi"
                      else "Changes apply on page reload"))
