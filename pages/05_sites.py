import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import TOTAL_SITES, CHART_LAYOUT
from i18n import t
from data_loader import find_data_files, load_cellhr_detail, load_site_database, load_flood_sites
from database import query_site_history

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 🏗️ {t('site_mgmt', lang)}")

cellhr_files, summary_files = find_data_files()
if not cellhr_files:
    st.warning(t("no_data", lang))
    st.stop()

selected_cellhr = st.selectbox("📂 Cellhr:", cellhr_files, format_func=lambda x: os.path.basename(x), key="site_cellhr")
selected_summary = summary_files[0] if summary_files else None

tab_db, tab_detail, tab_special = st.tabs([
    f"📋 {'CSDL Trạm' if lang == 'vi' else 'Site Database'}",
    f"🔎 {t('site_detail', lang)}",
    f"⚠️ {'Trạm đặc biệt' if lang == 'vi' else 'Special Sites'}",
])

with tab_db:
    if selected_summary:
        site_db = load_site_database(selected_summary)
        if site_db.empty:
            st.info(t("no_data", lang))
        else:
            st.markdown(f"**{len(site_db)}** {'trạm trong CSDL' if lang == 'vi' else 'sites in database'}")

            search = st.text_input(f"🔍 {t('search', lang)} (Site ID, Owner, Team...)", key="site_search")
            if search:
                mask = site_db.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
                site_db = site_db[mask]
                st.caption(f"{len(site_db)} {'kết quả' if lang == 'vi' else 'results'}")

            st.dataframe(site_db, use_container_width=True, hide_index=True, height=500)
    else:
        st.info("SUMMARY_AYY Database.xlsx not found")

with tab_detail:
    detail_df, col_map = load_cellhr_detail(selected_cellhr)
    if detail_df.empty:
        st.info(t("no_data", lang))
    else:
        if "site_id" in col_map:
            all_sites = sorted(detail_df[col_map["site_id"]].dropna().unique().tolist())
            site_id = st.selectbox(f"🏗️ {t('site_id', lang)}", all_sites, key="site_lookup")

            if site_id:
                site_data = detail_df[detail_df[col_map["site_id"]] == site_id]

                # Site summary cards
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    total_ch = site_data[col_map["cellhr"]].sum() if "cellhr" in col_map else 0
                    st.metric("Total Cell*h", f"{total_ch:,.1f}")
                with sc2:
                    st.metric(t("count", lang) + " events", f"{len(site_data)}")
                with sc3:
                    total_dur = site_data[col_map["duration"]].sum() if "duration" in col_map else 0
                    st.metric(t("duration_h", lang), f"{total_dur:,.1f}h")
                with sc4:
                    if "owner" in col_map:
                        owner = site_data[col_map["owner"]].iloc[0] if len(site_data) > 0 else "N/A"
                        st.metric(t("owner", lang), owner)

                # Event timeline
                st.subheader(f"📋 {t('event_history', lang)}")
                display_cols = []
                rename = {}
                for key, label in [
                    ("date", t("date", lang)), ("start_time", t("start_time", lang)),
                    ("end_time", t("end_time", lang)), ("duration", t("duration_h", lang)),
                    ("reason_level1", t("reason", lang)), ("reason_level3", "Detail"),
                    ("cellhr", t("cellhr_value", lang)), ("team", t("team", lang)),
                    ("day_night", "Day/Night"), ("noc_comment", "NOC Comment"),
                ]:
                    if key in col_map:
                        display_cols.append(col_map[key])
                        rename[col_map[key]] = label

                if display_cols:
                    show = site_data[display_cols].rename(columns=rename)
                    st.dataframe(show, use_container_width=True, hide_index=True)

                # Cause breakdown for this site
                if "reason_level1" in col_map and "cellhr" in col_map:
                    cause = site_data.groupby(col_map["reason_level1"])[col_map["cellhr"]].sum().reset_index()
                    cause.columns = ["cause", "cellhr"]
                    cause = cause[cause["cellhr"] > 0].sort_values("cellhr", ascending=False)

                    if not cause.empty:
                        fig = go.Figure(data=[go.Pie(
                            labels=cause["cause"], values=cause["cellhr"],
                            hole=0.4, textinfo="percent+label",
                        )])
                        fig.update_layout(title=f"{site_id} — {t('cause_breakdown', lang)}", height=300, **CHART_LAYOUT)
                        st.plotly_chart(fig, use_container_width=True)

                # DB history
                db_hist = query_site_history(site_id)
                if not db_hist.empty:
                    st.divider()
                    st.subheader(f"🗄️ {'Lịch sử từ Database' if lang == 'vi' else 'Database History'}")
                    st.caption(f"{len(db_hist)} {'sự kiện trong DB' if lang == 'vi' else 'events in DB'}")
                    st.dataframe(db_hist, use_container_width=True, hide_index=True)

with tab_special:
    sp1, sp2 = st.columns(2)
    with sp1:
        st.subheader(f"🌊 {t('flood_sites', lang)}")
        if selected_summary:
            flood = load_flood_sites(selected_summary)
            if flood.empty:
                st.info(t("no_data", lang))
            else:
                st.markdown(f"**{len(flood)}** {'trạm ngập lụt' if lang == 'vi' else 'flood sites'}")
                st.dataframe(flood, use_container_width=True, hide_index=True)

    with sp2:
        st.subheader(f"⚠️ {t('unsafe_sites', lang)}")
        detail_df2, col_map2 = load_cellhr_detail(selected_cellhr)
        if not detail_df2.empty and "unsafe" in col_map2:
            unsafe = detail_df2[detail_df2[col_map2["unsafe"]].astype(str).str.lower().str.contains("unsafe", na=False)]
            if unsafe.empty:
                st.success("✅ " + ("Không có trạm unsafe" if lang == "vi" else "No unsafe sites"))
            else:
                unsafe_sites = unsafe[col_map2["site_id"]].unique() if "site_id" in col_map2 else []
                st.warning(f"**{len(unsafe_sites)}** {'trạm unsafe' if lang == 'vi' else 'unsafe sites'}")
                if "site_id" in col_map2:
                    st.dataframe(
                        unsafe.groupby(col_map2["site_id"]).agg({
                            col_map2.get("cellhr", col_map2["site_id"]): "sum",
                            col_map2.get("owner", col_map2["site_id"]): "first",
                        }).reset_index().sort_values(
                            col_map2.get("cellhr", col_map2["site_id"]), ascending=False
                        ),
                        use_container_width=True, hide_index=True,
                    )
