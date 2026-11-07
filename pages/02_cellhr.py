import os
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from config import CELLHR_TARGET, CAUSE_COLORS, DATA_DIR, CHART_LAYOUT
from i18n import t
from session_data import require_data
from database import query_site_history

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 📊 {t('cellhr_analysis', lang)}")

data = require_data(lang)
detail_df = data["cellhr_detail"]
col_map = data["col_map"]

if detail_df.empty:
    st.warning(t("no_data", lang))
    st.stop()

# === FILTERS ===
with st.expander(f"🔍 {t('filter', lang)}", expanded=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        if "reason_level1" in col_map:
            reasons = [t("all", lang)] + sorted(detail_df[col_map["reason_level1"]].dropna().unique().tolist())
            sel_reason = st.selectbox(t("reason", lang), reasons)
        else:
            sel_reason = t("all", lang)
    with fc2:
        if "team" in col_map:
            teams = [t("all", lang)] + sorted(detail_df[col_map["team"]].dropna().unique().tolist())
            sel_team = st.selectbox(t("team", lang), teams)
        else:
            sel_team = t("all", lang)
    with fc3:
        if "owner" in col_map:
            owners = [t("all", lang)] + sorted(detail_df[col_map["owner"]].dropna().unique().tolist())
            sel_owner = st.selectbox(t("owner", lang), owners)
        else:
            sel_owner = t("all", lang)

filtered = detail_df.copy()
if sel_reason != t("all", lang) and "reason_level1" in col_map:
    filtered = filtered[filtered[col_map["reason_level1"]] == sel_reason]
if sel_team != t("all", lang) and "team" in col_map:
    filtered = filtered[filtered[col_map["team"]] == sel_team]
if sel_owner != t("all", lang) and "owner" in col_map:
    filtered = filtered[filtered[col_map["owner"]] == sel_owner]

# === STACKED BAR BY CAUSE ===
st.subheader(f"📊 {'Cell*h theo nguyên nhân mỗi ngày' if lang == 'vi' else 'Cell*h by Cause per Day'}")
if "date" in col_map and "reason_level1" in col_map and "cellhr" in col_map:
    pivot = filtered.groupby([col_map["date"], col_map["reason_level1"]])[col_map["cellhr"]].sum().reset_index()
    pivot.columns = ["date", "cause", "cellhr"]

    fig = go.Figure()
    for cause in sorted(pivot["cause"].unique()):
        sub = pivot[pivot["cause"] == cause].sort_values("date")
        fig.add_trace(go.Bar(
            x=sub["date"], y=sub["cellhr"], name=cause,
            marker_color=CAUSE_COLORS.get(cause, "#bfbfbf"),
        ))
    fig.update_layout(barmode="stack", height=400, xaxis_title=t("date", lang), yaxis_title="Cell*h",
                      legend=dict(orientation="h", y=-0.2), **CHART_LAYOUT)
    fig.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
    fig.add_hline(y=CELLHR_TARGET, line_dash="dot", line_color="#34C759", line_width=2,
                  annotation_text=f"{t('target', lang)}: {CELLHR_TARGET:,}",
                  annotation_font_color="#34C759")
    st.plotly_chart(fig, use_container_width=True)

# === HEATMAP BY HOUR ===
ch1, ch2 = st.columns(2)

with ch1:
    st.subheader(f"🌡️ {t('cellhr_by_hour', lang)}")
    if "start_time" in col_map and "cellhr" in col_map:
        df_heat = filtered.copy()
        time_col = col_map["start_time"]
        df_heat["hour"] = pd.to_datetime(df_heat[time_col], errors="coerce").dt.hour
        df_heat = df_heat.dropna(subset=["hour"])

        if "date" in col_map:
            heat_pivot = df_heat.groupby([col_map["date"], "hour"])[col_map["cellhr"]].sum().reset_index()
            heat_pivot.columns = ["date", "hour", "cellhr"]
            heat_matrix = heat_pivot.pivot_table(index="hour", columns="date", values="cellhr", fill_value=0)
            fig_heat = go.Figure(data=go.Heatmap(
                z=heat_matrix.values,
                x=[str(c)[:10] for c in heat_matrix.columns],
                y=[f"{int(h):02d}:00" for h in heat_matrix.index],
                colorscale="YlOrRd",
                hovertemplate="Date: %{x}<br>Hour: %{y}<br>Cell*h: %{z:.0f}<extra></extra>",
            ))
            fig_heat.update_layout(height=350, **CHART_LAYOUT)
            st.plotly_chart(fig_heat, use_container_width=True)

with ch2:
    st.subheader(f"🏆 {t('by_team', lang)}")
    if "team" in col_map and "cellhr" in col_map:
        team_data = filtered.groupby(col_map["team"])[col_map["cellhr"]].sum().reset_index()
        team_data.columns = ["team", "cellhr"]
        team_data = team_data.sort_values("cellhr", ascending=True)

        fig_team = go.Figure(go.Bar(
            x=team_data["cellhr"], y=team_data["team"],
            orientation="h", marker_color="#007AFF",
            text=[f"{v:,.0f}" for v in team_data["cellhr"]],
            textposition="outside",
        ))
        fig_team.update_layout(height=350, xaxis_title="Cell*h", **CHART_LAYOUT)
        fig_team.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
        fig_team.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
        st.plotly_chart(fig_team, use_container_width=True)

# === SITE DETAIL ===
st.divider()
st.subheader(f"🔎 {t('site_detail', lang)}")

if "site_id" in col_map:
    all_sites = sorted(filtered[col_map["site_id"]].dropna().unique().tolist())
    selected_site = st.selectbox(f"🏗️ {t('site_id', lang)}", all_sites, key="site_detail_select")

    if selected_site:
        site_events = filtered[filtered[col_map["site_id"]] == selected_site]
        st.markdown(f"**{t('event_history', lang)}** — {selected_site} ({len(site_events)} events)")

        display_columns = []
        rename = {}
        for key, label in [("date", t("date", lang)), ("start_time", t("start_time", lang)),
                            ("end_time", t("end_time", lang)), ("duration", t("duration_h", lang)),
                            ("reason_level1", t("reason", lang)), ("reason_level3", "Detail"),
                            ("cellhr", t("cellhr_value", lang)), ("team", t("team", lang)),
                            ("noc_comment", "NOC Comment")]:
            if key in col_map:
                display_columns.append(col_map[key])
                rename[col_map[key]] = label

        if display_columns:
            show_df = site_events[display_columns].rename(columns=rename)
            st.dataframe(show_df, use_container_width=True, hide_index=True)

        # Site summary from DB
        db_history = query_site_history(selected_site)
        if not db_history.empty:
            st.info(f"📚 {'Lịch sử từ DB' if lang == 'vi' else 'DB History'}: {len(db_history)} events")
