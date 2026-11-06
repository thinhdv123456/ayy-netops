import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import CAUSE_COLORS, TCO_COMPANIES, DATA_DIR, CHART_LAYOUT
from i18n import t
from data_loader import find_data_files, load_cellhr_detail, load_tco_power, load_mytel_power

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 🔋 {t('power_mgmt', lang)}")

cellhr_files, _ = find_data_files()
if not cellhr_files:
    st.warning(t("no_data", lang))
    st.stop()

selected = st.selectbox("📂 File:", cellhr_files, format_func=lambda x: os.path.basename(x), key="power_file")

tab_tco, tab_mytel, tab_overview = st.tabs([
    f"🏭 {t('tco_analysis', lang)}",
    f"⚡ {t('mytel_analysis', lang)}",
    f"📊 {'Tổng quan' if lang == 'vi' else 'Overview'}",
])

# === TCO POWER ===
with tab_tco:
    tco_df = load_tco_power(selected)
    if tco_df.empty:
        st.info(t("no_data", lang))
    else:
        st.markdown(f"**{len(tco_df)}** {'sự kiện TCO power' if lang == 'vi' else 'TCO power events'}")

        owner_col = None
        cellhr_col = None
        site_col = None
        duration_col = None
        for col in tco_df.columns:
            cl = str(col).lower()
            if cl == "owner":
                owner_col = col
            elif "cell*h" in cl or "cellhr" in cl:
                cellhr_col = col
            elif "site" in cl and "id" in cl:
                site_col = col
            elif "duration" in cl:
                duration_col = col

        if owner_col and cellhr_col:
            tco_df[cellhr_col] = pd.to_numeric(tco_df[cellhr_col], errors="coerce")
            by_owner = tco_df.groupby(owner_col).agg({
                cellhr_col: "sum",
                site_col: "nunique" if site_col else "count",
            }).reset_index()
            by_owner.columns = ["owner", "cellhr", "sites"]
            by_owner = by_owner.sort_values("cellhr", ascending=True)

            fig = go.Figure(go.Bar(
                x=by_owner["cellhr"], y=by_owner["owner"],
                orientation="h",
                marker_color="#ff7a45",
                text=[f"{v:,.0f} ({s} sites)" for v, s in zip(by_owner["cellhr"], by_owner["sites"])],
                textposition="outside",
            ))
            fig.update_layout(
                title=t("by_company", lang), height=400,
                xaxis_title="Cell*h", **CHART_LAYOUT,
            )
            fig.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            fig.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader(f"🔴 Top 15 {'trạm TCO tệ nhất' if lang == 'vi' else 'worst TCO sites'}")
        if site_col and cellhr_col:
            worst_tco = tco_df.groupby(site_col).agg({
                cellhr_col: "sum",
                owner_col: "first" if owner_col else "count",
            }).reset_index()
            worst_tco = worst_tco.sort_values(cellhr_col, ascending=False).head(15)
            rename = {site_col: t("site_id", lang), cellhr_col: t("cellhr_value", lang)}
            if owner_col:
                rename[owner_col] = t("owner", lang)
            worst_tco = worst_tco.rename(columns=rename)
            st.dataframe(worst_tco, use_container_width=True, hide_index=True)

# === MYTEL POWER ===
with tab_mytel:
    mytel_df = load_mytel_power(selected)
    if mytel_df.empty:
        st.info(t("no_data", lang))
    else:
        st.markdown(f"**{len(mytel_df)}** {'sự kiện Mytel power' if lang == 'vi' else 'Mytel power events'}")

        reason_col = None
        cellhr_col2 = None
        site_col2 = None
        for col in mytel_df.columns:
            cl = str(col).lower()
            if "reason" in cl:
                reason_col = col
            elif "cell*h" in cl or "cellhr" in cl:
                cellhr_col2 = col
            elif "site" in cl and "id" in cl:
                site_col2 = col

        if reason_col and cellhr_col2:
            mytel_df[cellhr_col2] = pd.to_numeric(mytel_df[cellhr_col2], errors="coerce")
            by_reason = mytel_df.groupby(reason_col)[cellhr_col2].sum().reset_index()
            by_reason.columns = ["reason", "cellhr"]
            by_reason = by_reason.sort_values("cellhr", ascending=False)

            fig2 = go.Figure(go.Bar(
                x=by_reason["reason"], y=by_reason["cellhr"],
                marker_color="#ffc53d",
                text=[f"{v:,.0f}" for v in by_reason["cellhr"]],
                textposition="outside",
            ))
            fig2.update_layout(title=t("by_cause", lang), height=350, xaxis_title=t("reason", lang), yaxis_title="Cell*h", **CHART_LAYOUT)
            fig2.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            fig2.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader(f"🔴 Top 15 {'trạm Mytel power tệ nhất' if lang == 'vi' else 'worst Mytel power sites'}")
        if site_col2 and cellhr_col2:
            worst_mt = mytel_df.groupby(site_col2)[cellhr_col2].sum().reset_index()
            worst_mt = worst_mt.sort_values(cellhr_col2, ascending=False).head(15)
            worst_mt = worst_mt.rename(columns={site_col2: t("site_id", lang), cellhr_col2: t("cellhr_value", lang)})
            st.dataframe(worst_mt, use_container_width=True, hide_index=True)

# === OVERVIEW ===
with tab_overview:
    detail_df, col_map = load_cellhr_detail(selected)
    if not detail_df.empty and "reason_level1" in col_map and "cellhr" in col_map:
        power_causes = ["Towerco power issue", "Mytel Power Issue", "Power down at HUB site"]
        power_df = detail_df[detail_df[col_map["reason_level1"]].isin(power_causes)]

        if not power_df.empty and "power_model" in col_map:
            by_model = power_df.groupby(col_map["power_model"])[col_map["cellhr"]].sum().reset_index()
            by_model.columns = ["model", "cellhr"]
            by_model = by_model.sort_values("cellhr", ascending=False)

            fig3 = go.Figure(data=[go.Pie(
                labels=by_model["model"], values=by_model["cellhr"],
                hole=0.4, textinfo="percent+label",
            )])
            fig3.update_layout(title=t("power_model", lang), height=350, **CHART_LAYOUT)
            st.plotly_chart(fig3, use_container_width=True)

        if "date" in col_map:
            daily_power = power_df.groupby([col_map["date"], col_map["reason_level1"]])[col_map["cellhr"]].sum().reset_index()
            daily_power.columns = ["date", "cause", "cellhr"]

            fig4 = go.Figure()
            for cause in power_causes:
                sub = daily_power[daily_power["cause"] == cause].sort_values("date")
                if not sub.empty:
                    fig4.add_trace(go.Scatter(
                        x=sub["date"], y=sub["cellhr"],
                        mode="lines+markers", name=cause,
                        line=dict(color=CAUSE_COLORS.get(cause, "#bfbfbf"), width=2.5, shape="spline"),
                        marker=dict(size=7, line=dict(width=2, color="white")),
                    ))
            fig4.update_layout(
                title="Daily power Cell*h trend", height=350,
                xaxis_title=t("date", lang), yaxis_title="Cell*h",
                legend=dict(orientation="h", y=-0.2), **CHART_LAYOUT,
            )
            fig4.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            fig4.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            st.plotly_chart(fig4, use_container_width=True)
