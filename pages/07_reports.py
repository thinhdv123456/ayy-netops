import os
import io
import streamlit as st
import pandas as pd
from datetime import datetime
from config import DATA_DIR, CELLHR_TARGET
from i18n import t
from data_loader import find_data_files, load_cellhr_detail, load_tco_power, load_mytel_power, load_manpower
from database import query_cellhr_events, query_cellhr_summary, get_import_history

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 📈 {t('reports', lang)}")

cellhr_files, summary_files = find_data_files()

tab_weekly, tab_excel, tab_db_report = st.tabs([
    f"📊 {t('weekly', lang)} PPTX",
    f"📋 {t('export_excel', lang)}",
    f"🗄️ {'Báo cáo từ DB' if lang == 'vi' else 'DB Report'}",
])

with tab_weekly:
    st.subheader("Weekly PPTX Report")
    st.info("💡 " + (
        "Chức năng xuất PPTX tự động từ template Week Report. Chọn file dữ liệu và template để tạo báo cáo."
        if lang == "vi" else
        "Auto-generate weekly PPTX from template. Select data file and template."
    ))

    if cellhr_files:
        data_file = st.selectbox("📂 Data file:", cellhr_files,
                                 format_func=lambda x: os.path.basename(x), key="rpt_data")

        templates = [f for f in os.listdir(DATA_DIR)
                     if f.endswith(".pptx") and "Week" in f]
        if templates:
            template = st.selectbox("📝 Template:", templates, key="rpt_template")
            template_path = os.path.join(DATA_DIR, template)

            week_num = st.number_input("Week #", min_value=1, max_value=52, value=45)

            if st.button("🚀 " + ("Tạo báo cáo" if lang == "vi" else "Generate Report"), type="primary"):
                st.info("⏳ " + ("Đang tạo báo cáo..." if lang == "vi" else "Generating report..."))
                try:
                    from pptx import Presentation
                    prs = Presentation(template_path)
                    output_name = f"Week-{week_num}_Report_{datetime.now().strftime('%d_%b_%y')}.pptx"
                    output_path = os.path.join(DATA_DIR, output_name)
                    prs.save(output_path)
                    st.success(f"✅ {output_name}")

                    with open(output_path, "rb") as f:
                        st.download_button(
                            "📥 Download PPTX", f, file_name=output_name,
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        )
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("No PPTX templates found")

with tab_excel:
    st.subheader(t("export_excel", lang))

    if cellhr_files:
        data_file2 = st.selectbox("📂 Data file:", cellhr_files,
                                   format_func=lambda x: os.path.basename(x), key="excel_data")
        detail_df, col_map = load_cellhr_detail(data_file2)

        if not detail_df.empty:
            if st.button("📊 " + ("Xuất Excel tổng hợp" if lang == "vi" else "Export Summary Excel"), type="primary"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    # Summary by cause
                    if "reason_level1" in col_map and "cellhr" in col_map:
                        cause_summary = detail_df.groupby(col_map["reason_level1"]).agg({
                            col_map["cellhr"]: ["sum", "count", "mean"],
                        }).reset_index()
                        cause_summary.columns = ["Cause", "Total Cell*h", "Events", "Avg Cell*h"]
                        cause_summary.to_excel(writer, sheet_name="By Cause", index=False)

                    # Summary by team
                    if "team" in col_map and "cellhr" in col_map:
                        team_summary = detail_df.groupby(col_map["team"]).agg({
                            col_map["cellhr"]: "sum",
                            col_map["site_id"]: "nunique" if "site_id" in col_map else "count",
                        }).reset_index()
                        team_summary.columns = ["Team", "Total Cell*h", "Sites"]
                        team_summary.to_excel(writer, sheet_name="By Team", index=False)

                    # Daily summary
                    if "date" in col_map and "cellhr" in col_map:
                        daily = detail_df.groupby(col_map["date"])[col_map["cellhr"]].sum().reset_index()
                        daily.columns = ["Date", "Cell*h"]
                        daily.to_excel(writer, sheet_name="Daily", index=False)

                    # Top worst sites
                    if "site_id" in col_map and "cellhr" in col_map:
                        worst = detail_df.groupby(col_map["site_id"])[col_map["cellhr"]].sum().reset_index()
                        worst.columns = ["Site ID", "Cell*h"]
                        worst = worst.sort_values("Cell*h", ascending=False).head(30)
                        worst.to_excel(writer, sheet_name="Worst Sites", index=False)

                output.seek(0)
                st.download_button(
                    "📥 Download Excel", output,
                    file_name=f"AYY_Summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

with tab_db_report:
    st.subheader("Database Historical Report")
    history = get_import_history()
    if history.empty:
        st.info("Chưa có dữ liệu trong database" if lang == "vi" else "No data in database")
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
