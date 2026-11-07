import os
import io
import streamlit as st
import pandas as pd
from datetime import datetime
from config import DATA_DIR, CELLHR_TARGET, BASE_DIR
from i18n import t
from session_data import require_data
from database import query_cellhr_events, query_cellhr_summary, get_import_history

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 📈 {t('reports', lang)}")

data = require_data(lang)
detail_df = data["cellhr_detail"]
col_map = data["col_map"]

tab_weekly, tab_excel, tab_db_report = st.tabs([
    f"📊 {t('weekly', lang)} PPTX",
    f"📋 {t('export_excel', lang)}",
    f"🗄️ {'Báo cáo từ DB' if lang == 'vi' else 'DB Report'}",
])

with tab_weekly:
    st.subheader("Weekly PPTX Report")
    st.info("💡 " + (
        "Chức năng xuất PPTX tự động từ template Week Report. Chọn template để tạo báo cáo."
        if lang == "vi" else
        "Auto-generate weekly PPTX from template. Select template to generate."
    ))

    all_templates = {}
    for search_dir in [TEMPLATE_DIR, DATA_DIR]:
        if os.path.isdir(search_dir):
            for f in os.listdir(search_dir):
                if f.endswith(".pptx") and "Week" in f:
                    all_templates[f] = os.path.join(search_dir, f)

    if not all_templates:
        st.warning("⚠️ " + (
            "Chưa có file template PPTX."
            if lang == "vi" else
            "No PPTX templates found."
        ))
    else:
        template_names = list(all_templates.keys())
        template = st.selectbox("📝 Template:", template_names, key="rpt_template")
        template_path = all_templates[template]

        week_num = st.number_input("Week #", min_value=1, max_value=52, value=45)

        if st.button("🚀 " + ("Tạo báo cáo" if lang == "vi" else "Generate Report"), type="primary"):
            try:
                from pptx import Presentation
                prs = Presentation(template_path)
                output_name = f"Week-{week_num}_Report_{datetime.now().strftime('%d_%b_%y')}.pptx"

                buf = io.BytesIO()
                prs.save(buf)
                buf.seek(0)

                st.success(f"✅ {output_name}")
                st.download_button(
                    "📥 Download PPTX", buf, file_name=output_name,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
            except Exception as e:
                st.error(f"Error: {e}")

with tab_excel:
    st.subheader(t("export_excel", lang))

    if detail_df.empty:
        st.warning("Không thể đọc dữ liệu" if lang == "vi" else "Cannot read data")
    else:
        total_cellhr = detail_df[col_map["cellhr"]].sum() if "cellhr" in col_map else 0
        total_events = len(detail_df)
        sites = detail_df[col_map["site_id"]].nunique() if "site_id" in col_map else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Cell*h", f"{total_cellhr:,.0f}")
        c2.metric("Events" if lang == "en" else "Sự kiện", f"{total_events:,}")
        c3.metric("Sites", f"{sites}")

        if st.button("📊 " + ("Xuất Excel tổng hợp" if lang == "vi" else "Export Summary Excel"), type="primary"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                if "reason_level1" in col_map and "cellhr" in col_map:
                    cause_summary = detail_df.groupby(col_map["reason_level1"]).agg({
                        col_map["cellhr"]: ["sum", "count", "mean"],
                    }).reset_index()
                    cause_summary.columns = ["Cause", "Total Cell*h", "Events", "Avg Cell*h"]
                    cause_summary = cause_summary.sort_values("Total Cell*h", ascending=False)
                    cause_summary.to_excel(writer, sheet_name="By Cause", index=False)

                if "team" in col_map and "cellhr" in col_map:
                    agg_cols = {col_map["cellhr"]: "sum"}
                    if "site_id" in col_map:
                        agg_cols[col_map["site_id"]] = "nunique"
                    team_summary = detail_df.groupby(col_map["team"]).agg(agg_cols).reset_index()
                    cols = ["Team", "Total Cell*h"]
                    if "site_id" in col_map:
                        cols.append("Sites")
                    team_summary.columns = cols
                    team_summary = team_summary.sort_values("Total Cell*h", ascending=False)
                    team_summary.to_excel(writer, sheet_name="By Team", index=False)

                if "date" in col_map and "cellhr" in col_map:
                    daily = detail_df.groupby(col_map["date"])[col_map["cellhr"]].sum().reset_index()
                    daily.columns = ["Date", "Cell*h"]
                    daily = daily.sort_values("Date")
                    daily.to_excel(writer, sheet_name="Daily", index=False)

                if "site_id" in col_map and "cellhr" in col_map:
                    worst = detail_df.groupby(col_map["site_id"])[col_map["cellhr"]].sum().reset_index()
                    worst.columns = ["Site ID", "Cell*h"]
                    worst = worst.sort_values("Cell*h", ascending=False).head(30)
                    worst.to_excel(writer, sheet_name="Worst Sites", index=False)

                detail_df.to_excel(writer, sheet_name="Raw Data", index=False)

            output.seek(0)
            st.success("✅ " + ("File Excel đã tạo xong!" if lang == "vi" else "Excel file generated!"))
            st.download_button(
                "📥 Download Excel", output,
                file_name=f"AYY_Summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with tab_db_report:
    st.subheader("Database Historical Report" if lang == "en" else "Báo cáo lịch sử từ Database")

    history = get_import_history()
    if history.empty:
        st.info("💡 " + (
            "Chưa có dữ liệu trong database."
            if lang == "vi" else
            "No data in database."
        ))

        st.divider()
        st.markdown("**" + ("Tóm tắt từ dữ liệu hiện tại:" if lang == "vi" else "Summary from current data:") + "**")
        if not detail_df.empty:
            if "reason_level1" in col_map and "cellhr" in col_map:
                cause_df = detail_df.groupby(col_map["reason_level1"]).agg({
                    col_map["cellhr"]: ["sum", "count"],
                }).reset_index()
                cause_df.columns = [
                    "Nguyên nhân" if lang == "vi" else "Cause",
                    "Tổng Cell*h" if lang == "vi" else "Total Cell*h",
                    "Số sự kiện" if lang == "vi" else "Events",
                ]
                cause_df = cause_df.sort_values(cause_df.columns[1], ascending=False)
                st.dataframe(cause_df, use_container_width=True, hide_index=True)

            if "team" in col_map and "cellhr" in col_map:
                team_df = detail_df.groupby(col_map["team"])[col_map["cellhr"]].sum().reset_index()
                team_df.columns = [
                    "Team",
                    "Tổng Cell*h" if lang == "vi" else "Total Cell*h",
                ]
                team_df = team_df.sort_values(team_df.columns[1], ascending=False)
                st.dataframe(team_df, use_container_width=True, hide_index=True)
    else:
        st.markdown(f"**{len(history)}** {'file đã import' if lang == 'vi' else 'files imported'}")

        cause_summary = query_cellhr_summary("reason_level1")
        if not cause_summary.empty:
            st.subheader(t("cause_breakdown", lang) + " — All Time")
            st.dataframe(cause_summary, use_container_width=True, hide_index=True)

        team_summary = query_cellhr_summary("team")
        if not team_summary.empty:
            st.subheader(t("by_team", lang) + " — All Time")
            st.dataframe(team_summary, use_container_width=True, hide_index=True)
