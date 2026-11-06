import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import CHART_LAYOUT
from i18n import t
from data_loader import find_data_files, load_tx_report, load_tx_detail, load_cellhr_detail

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 📡 {t('transmission', lang)}")

cellhr_files, _ = find_data_files()
if not cellhr_files:
    st.warning(t("no_data", lang))
    st.stop()

selected = st.selectbox("📂 File:", cellhr_files, format_func=lambda x: os.path.basename(x), key="tx_file")

tab_incidents, tab_routes, tab_detail = st.tabs([
    f"📋 {t('incident_list', lang)}",
    f"🔄 {t('repeated_routes', lang)}",
    f"📊 {'Chi tiết' if lang == 'vi' else 'Detail'}",
])

with tab_incidents:
    tx_report = load_tx_report(selected)
    if tx_report.empty:
        st.info(t("no_data", lang))
    else:
        st.markdown(f"**{len(tx_report)}** {'sự cố truyền dẫn' if lang == 'vi' else 'transmission incidents'}")
        st.dataframe(tx_report, use_container_width=True, hide_index=True)

with tab_routes:
    tx_detail = load_tx_detail(selected)
    if tx_detail.empty:
        st.info(t("no_data", lang))
    else:
        route_col = None
        for col in tx_detail.columns:
            cl = str(col).lower()
            if "route" in cl or "cable" in cl or "link" in cl:
                route_col = col
                break

        if route_col:
            route_counts = tx_detail[route_col].value_counts().reset_index()
            route_counts.columns = ["route", "incidents"]
            repeated = route_counts[route_counts["incidents"] >= 2]

            if repeated.empty:
                st.success("✅ " + ("Không có tuyến lặp sự cố" if lang == "vi" else "No repeated fault routes"))
            else:
                st.warning(f"⚠️ {len(repeated)} " + ("tuyến có >= 2 sự cố" if lang == "vi" else "routes with >= 2 incidents"))
                fig = go.Figure(go.Bar(
                    x=repeated["route"], y=repeated["incidents"],
                    marker_color="#AF52DE",
                    text=repeated["incidents"], textposition="outside",
                ))
                fig.update_layout(height=350, xaxis_title="Route", yaxis_title=t("count", lang), **CHART_LAYOUT)
                fig.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
                fig.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(repeated, use_container_width=True, hide_index=True)
        else:
            st.dataframe(tx_detail, use_container_width=True, hide_index=True)

with tab_detail:
    detail_df, col_map = load_cellhr_detail(selected)
    if not detail_df.empty and "reason_level1" in col_map:
        tx_events = detail_df[detail_df[col_map["reason_level1"]] == "Transmission"]
        if tx_events.empty:
            st.info("No transmission events in Cell_h Detail")
        else:
            st.markdown(f"**{len(tx_events)}** Cell*h events for Transmission")
            display_cols = []
            rename = {}
            for key, label in [("site_id", t("site_id", lang)), ("date", t("date", lang)),
                                ("start_time", t("start_time", lang)), ("end_time", t("end_time", lang)),
                                ("duration", t("duration_h", lang)), ("cellhr", t("cellhr_value", lang)),
                                ("team", t("team", lang)), ("reason_level3", "Detail")]:
                if key in col_map:
                    display_cols.append(col_map[key])
                    rename[col_map[key]] = label
            if display_cols:
                st.dataframe(tx_events[display_cols].rename(columns=rename),
                             use_container_width=True, hide_index=True)
