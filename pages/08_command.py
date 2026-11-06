import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import CELLHR_TARGET, TOTAL_SITES, CAUSE_COLORS, CHART_LAYOUT
from i18n import t
from data_loader import find_data_files, load_cellhr_detail, load_manpower

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 🎯 {t('command_center', lang)}")

cellhr_files, summary_files = find_data_files()
if not cellhr_files:
    st.warning(t("no_data", lang))
    st.stop()

selected = cellhr_files[-1]
detail_df, col_map = load_cellhr_detail(selected)

if detail_df.empty:
    st.warning(t("no_data", lang))
    st.stop()

# === SLA COMPLIANCE GAUGE ===
total_cellhr = detail_df[col_map["cellhr"]].sum() if "cellhr" in col_map else 0
if "date" in col_map:
    n_days = detail_df[col_map["date"]].nunique()
else:
    n_days = 1
daily_avg = total_cellhr / max(n_days, 1)
sla_pct = min(100, max(0, (1 - (daily_avg - CELLHR_TARGET) / CELLHR_TARGET) * 100)) if CELLHR_TARGET > 0 else 0

g1, g2, g3 = st.columns(3)
with g1:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=daily_avg,
        title={"text": f"{'Cell*h TB/ngày' if lang == 'vi' else 'Avg Daily Cell*h'}"},
        delta={"reference": CELLHR_TARGET, "increasing": {"color": "red"}, "decreasing": {"color": "green"}},
        gauge={
            "axis": {"range": [0, 15000]},
            "bar": {"color": "#FF3B30" if daily_avg > CELLHR_TARGET else "#34C759"},
            "steps": [
                {"range": [0, CELLHR_TARGET], "color": "rgba(52,199,89,0.08)"},
                {"range": [CELLHR_TARGET, 10000], "color": "rgba(255,149,0,0.08)"},
                {"range": [10000, 15000], "color": "rgba(255,59,48,0.08)"},
            ],
            "threshold": {"line": {"color": "#34C759", "width": 3}, "thickness": 0.75, "value": CELLHR_TARGET},
        },
    ))
    fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20),
                            font_family=CHART_LAYOUT["font_family"],
                            paper_bgcolor=CHART_LAYOUT["paper_bgcolor"])
    st.plotly_chart(fig_gauge, use_container_width=True)

with g2:
    sites_affected = detail_df[col_map["site_id"]].nunique() if "site_id" in col_map else 0
    site_up_pct = (1 - sites_affected / TOTAL_SITES) * 100
    fig_g2 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=site_up_pct,
        title={"text": f"{'Tỷ lệ trạm UP' if lang == 'vi' else 'Sites UP Rate'}"},
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#34C759" if site_up_pct > 90 else "#FF9500"},
            "steps": [
                {"range": [0, 80], "color": "rgba(255,59,48,0.08)"},
                {"range": [80, 95], "color": "rgba(255,149,0,0.08)"},
                {"range": [95, 100], "color": "rgba(52,199,89,0.08)"},
            ],
        },
    ))
    fig_g2.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20),
                         font_family=CHART_LAYOUT["font_family"],
                         paper_bgcolor=CHART_LAYOUT["paper_bgcolor"])
    st.plotly_chart(fig_g2, use_container_width=True)

with g3:
    fig_g3 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=sla_pct,
        title={"text": t("sla_compliance", lang)},
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#007AFF"},
            "steps": [
                {"range": [0, 50], "color": "rgba(255,59,48,0.08)"},
                {"range": [50, 80], "color": "rgba(255,149,0,0.08)"},
                {"range": [80, 100], "color": "rgba(52,199,89,0.08)"},
            ],
        },
    ))
    fig_g3.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20),
                         font_family=CHART_LAYOUT["font_family"],
                         paper_bgcolor=CHART_LAYOUT["paper_bgcolor"])
    st.plotly_chart(fig_g3, use_container_width=True)

st.divider()

# === TEAM PERFORMANCE ===
st.subheader(f"🏆 {t('team_performance', lang)}")
if "team" in col_map and "cellhr" in col_map:
    team_perf = detail_df.groupby(col_map["team"]).agg({
        col_map["cellhr"]: "sum",
        col_map["site_id"]: "nunique" if "site_id" in col_map else "count",
        col_map.get("duration", col_map["cellhr"]): "mean",
    }).reset_index()
    team_perf.columns = [t("team", lang), "Total Cell*h", "Sites affected",
                          "Avg Duration" if "duration" in col_map else "Avg Cell*h"]
    team_perf = team_perf.sort_values("Total Cell*h", ascending=True)

    fig_tp = go.Figure()
    fig_tp.add_trace(go.Bar(
        y=team_perf[t("team", lang)], x=team_perf["Total Cell*h"],
        orientation="h", marker_color="#007AFF",
        text=[f"{v:,.0f}" for v in team_perf["Total Cell*h"]],
        textposition="outside",
    ))
    fig_tp.update_layout(height=400, xaxis_title="Cell*h", **CHART_LAYOUT)
    fig_tp.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
    fig_tp.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
    st.plotly_chart(fig_tp, use_container_width=True)

# === LIVE STATUS SUMMARY ===
st.divider()
st.subheader(f"📊 {t('live_status', lang)}")

if "site_id" in col_map and "reason_level1" in col_map:
    status_summary = detail_df.groupby(col_map["reason_level1"])[col_map["site_id"]].nunique().reset_index()
    status_summary.columns = [t("reason", lang), "Sites"]
    status_summary = status_summary.sort_values("Sites", ascending=False)

    total_down = status_summary["Sites"].sum()
    total_up = TOTAL_SITES - total_down

    ss1, ss2 = st.columns([1, 2])
    with ss1:
        st.metric(f"🟢 {t('status_up', lang)}", total_up)
        st.metric(f"🔴 {t('status_down', lang)}", total_down)
    with ss2:
        st.dataframe(status_summary, use_container_width=True, hide_index=True)
