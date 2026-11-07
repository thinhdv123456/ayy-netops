import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import TOTAL_SITES, TEAMS, CHART_LAYOUT
from i18n import t
from session_data import require_data

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 👥 {t('manpower', lang)}")

data = require_data(lang)

manpower_df = data.get("manpower", pd.DataFrame())
if manpower_df.empty:
    st.warning(t("no_data", lang))
    st.stop()

total_staff = len(manpower_df)

status_col = None
team_col = None
name_col = None
for col in manpower_df.columns:
    cl = str(col).lower()
    if "resign" in cl or "status" in cl:
        status_col = col
    if "team" in cl and team_col is None:
        team_col = col
    if ("name" in cl or "họ" in cl or "tên" in cl) and name_col is None:
        name_col = col

if status_col:
    working_mask = manpower_df[status_col].apply(
        lambda x: str(x).lower() not in ["resigned", "nghỉ việc", "quit", "terminated", ""]
        if pd.notna(x) else True
    )
    working = working_mask.sum()
    resigned = total_staff - working
else:
    working = total_staff
    resigned = 0

resign_rate = (resigned / total_staff * 100) if total_staff > 0 else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric(t("staff_total", lang), total_staff)
with k2:
    st.metric(t("staff_working", lang), int(working))
with k3:
    st.metric(t("staff_resigned", lang), int(resigned))
with k4:
    st.metric(t("resign_rate", lang), f"{resign_rate:.1f}%")

st.divider()

tab_team, tab_workload, tab_list = st.tabs([
    f"👥 {t('by_team', lang)}",
    f"📊 {t('workload', lang)}",
    f"📋 {'Danh sách' if lang == 'vi' else 'Staff List'}",
])

with tab_team:
    if team_col:
        team_counts = manpower_df.groupby(team_col).size().reset_index(name="count")
        if status_col:
            working_by_team = manpower_df[working_mask].groupby(team_col).size().reset_index(name="working")
            team_counts = team_counts.merge(working_by_team, on=team_col, how="left").fillna(0)
            team_counts["resigned"] = team_counts["count"] - team_counts["working"]
        team_counts = team_counts.sort_values("count", ascending=True)

        fig = go.Figure()
        if "working" in team_counts.columns:
            fig.add_trace(go.Bar(
                y=team_counts[team_col], x=team_counts["working"],
                name=t("staff_working", lang), orientation="h", marker_color="#34C759",
            ))
            fig.add_trace(go.Bar(
                y=team_counts[team_col], x=team_counts["resigned"],
                name=t("staff_resigned", lang), orientation="h", marker_color="#FF3B30",
            ))
            fig.update_layout(barmode="stack")
        else:
            fig.add_trace(go.Bar(
                y=team_counts[team_col], x=team_counts["count"],
                orientation="h", marker_color="#007AFF",
            ))
        fig.update_layout(height=400, xaxis_title=t("count", lang), **CHART_LAYOUT)
        fig.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
        fig.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
        st.plotly_chart(fig, use_container_width=True)

with tab_workload:
    detail_df, col_map = data["cellhr_detail"], data["col_map"]
    if team_col and not detail_df.empty and "team" in col_map and "site_id" in col_map:
        sites_per_team = detail_df.groupby(col_map["team"])[col_map["site_id"]].nunique().reset_index()
        sites_per_team.columns = ["team", "sites"]

        if status_col:
            staff_per_team = manpower_df[working_mask].groupby(team_col).size().reset_index(name="staff")
        else:
            staff_per_team = manpower_df.groupby(team_col).size().reset_index(name="staff")

        workload = sites_per_team.merge(staff_per_team, left_on="team", right_on=team_col, how="left")
        workload["sites_per_person"] = (workload["sites"] / workload["staff"].fillna(1)).round(1)
        workload = workload.sort_values("sites_per_person", ascending=False)

        fig2 = go.Figure(go.Bar(
            x=workload["team"], y=workload["sites_per_person"],
            marker_color="#5856D6",
            text=[f"{v:.1f}" for v in workload["sites_per_person"]],
            textposition="outside",
        ))
        fig2.update_layout(height=350, xaxis_title=t("team", lang),
                           yaxis_title=t("workload", lang), **CHART_LAYOUT)
        fig2.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
        fig2.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(workload[["team", "sites", "staff", "sites_per_person"]].rename(columns={
            "team": t("team", lang), "sites": "Sites", "staff": "Staff",
            "sites_per_person": t("workload", lang),
        }), use_container_width=True, hide_index=True)

with tab_list:
    search = st.text_input(f"🔍 {t('search', lang)}", key="staff_search")
    display_df = manpower_df.copy()
    if search:
        mask = display_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        display_df = display_df[mask]
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)
