import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import CELLHR_TARGET, TOTAL_SITES, CAUSE_COLORS, CHART_LAYOUT
from i18n import t
from session_data import process_uploads, get_data

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 🏠 {t('dashboard', lang)}")

data = get_data()

tab_upload, tab_live = st.tabs([
    "📤 " + ("Tải dữ liệu" if lang == "vi" else "Upload Data"),
    "📊 " + ("Phân tích" if lang == "vi" else "Analysis"),
])

with tab_upload:
    st.markdown("### 📤 " + ("Tải dữ liệu để phân tích" if lang == "vi" else "Upload Data for Analysis"))

    if data and data.get("has_data"):
        st.success("✅ " + ("Đã có dữ liệu. Bạn có thể upload file mới để thay thế." if lang == "vi"
                            else "Data loaded. You can upload new files to replace."))

    st.markdown("**" + ("File bắt buộc:" if lang == "vi" else "Required file:") + "**")
    cellhr_file = st.file_uploader(
        "📊 Cellhr Daily review*.xlsx",
        type=["xlsx", "xls"],
        key="upload_cellhr",
    )

    st.markdown("**" + ("File tùy chọn:" if lang == "vi" else "Optional file:") + "**")
    summary_file = st.file_uploader(
        "📋 SUMMARY_AYY Database.xlsx",
        type=["xlsx", "xls"],
        key="upload_summary",
    )

    if cellhr_file:
        st.markdown(f"- **{cellhr_file.name}** ({cellhr_file.size / 1024:.0f} KB)")
        if summary_file:
            st.markdown(f"- **{summary_file.name}** ({summary_file.size / 1024:.0f} KB)")

        auto_process = not data or not data.get("has_data")
        if auto_process or st.button("🚀 " + ("Xử lý dữ liệu" if lang == "vi" else "Process Data"), type="primary"):
            with st.spinner("Đang xử lý..." if lang == "vi" else "Processing..."):
                cellhr_bytes = cellhr_file.getvalue()
                summary_bytes = summary_file.getvalue() if summary_file else None
                result = process_uploads(cellhr_bytes, summary_bytes)

                if result.get("cellhr_error"):
                    st.error(f"Lỗi đọc Cell_h Detail: {result['cellhr_error']}")
                else:
                    detail_df = result.get("cellhr_detail", pd.DataFrame())
                    col_map = result.get("col_map", {})
                    total = detail_df[col_map["cellhr"]].sum() if "cellhr" in col_map else 0
                    st.success(f"✅ {'Đã xử lý xong!' if lang == 'vi' else 'Done!'} — "
                               f"{len(detail_df):,} records, {total:,.0f} Cell*h")
                    if not auto_process:
                        st.rerun()
                    else:
                        data = result
    elif not data:
        st.info("📁 " + ("Kéo thả file Excel vào đây hoặc bấm Browse" if lang == "vi"
                          else "Drag & drop Excel files here or click Browse"))

with tab_live:
    if not data or not data.get("has_data"):
        st.info("👉 " + ("Vào tab 'Tải dữ liệu' để upload file Excel" if lang == "vi"
                          else "Go to 'Upload Data' tab to upload Excel files"))
        st.stop()

    detail_df = data["cellhr_detail"]
    col_map = data["col_map"]
    manpower_df = data.get("manpower", pd.DataFrame())

    if detail_df.empty:
        st.warning(t("no_data", lang))
        st.stop()

    # === KPI METRICS ===
    if "cellhr" in col_map:
        total_cellhr = detail_df[col_map["cellhr"]].sum()
    else:
        total_cellhr = 0

    sites_with_events = detail_df[col_map["site_id"]].nunique() if "site_id" in col_map else 0
    availability = max(0, (1 - sites_with_events / TOTAL_SITES) * 100) if TOTAL_SITES > 0 else 0

    staff_str = "N/A"
    if not manpower_df.empty:
        total_staff = len(manpower_df)
        resigned_cols = [c for c in manpower_df.columns if "resign" in str(c).lower() or "status" in str(c).lower()]
        if resigned_cols:
            status_col = resigned_cols[0]
            working = manpower_df[status_col].apply(
                lambda x: str(x).lower() not in ["resigned", "nghỉ việc", "quit", "terminated", ""]
                if pd.notna(x) else True
            ).sum()
        else:
            working = total_staff
        staff_str = f"{int(working)}/{total_staff}"

    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        over = total_cellhr > CELLHR_TARGET
        st.metric(t("total_cellhr", lang), f"{total_cellhr:,.0f}",
                  delta=f"{'Vượt' if lang == 'vi' else 'Over'} {total_cellhr - CELLHR_TARGET:,.0f}" if over else "OK",
                  delta_color="inverse" if over else "normal")
    with k2:
        st.metric(t("sites_down", lang), f"{sites_with_events}", delta=f"/ {TOTAL_SITES} sites")
    with k3:
        st.metric(t("availability", lang), f"{availability:.1f}%")
    with k4:
        st.metric(t("staff_active", lang), staff_str)

    st.divider()

    # === CHARTS ===
    chart1, chart2 = st.columns([3, 2])

    with chart1:
        st.subheader(f"📈 {t('daily_trend', lang)}")
        if "date" in col_map and "cellhr" in col_map:
            daily = detail_df.groupby(col_map["date"])[col_map["cellhr"]].sum().reset_index()
            daily.columns = ["date", "cellhr"]
            daily = daily.sort_values("date")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily["date"], y=daily["cellhr"],
                mode="lines+markers+text", name=t("actual", lang),
                line=dict(color="#FF3B30", width=2.5, shape="spline"),
                marker=dict(size=9, color="#FF3B30", line=dict(width=2, color="white")),
                text=[f"{v:,.0f}" for v in daily["cellhr"]],
                textposition="top center",
                textfont=dict(size=12, color="rgba(0,0,0,0.65)"),
            ))
            fig.add_hline(y=CELLHR_TARGET, line_dash="dot", line_color="#34C759", line_width=2,
                          annotation_text=f"{t('target', lang)}: {CELLHR_TARGET:,}",
                          annotation_font_color="#34C759")
            fig.update_layout(height=380, hovermode="x unified",
                              xaxis_title=t("date", lang), yaxis_title="Cell*h",
                              **CHART_LAYOUT)
            fig.update_xaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            fig.update_yaxes(gridcolor="rgba(142,142,147,0.12)", zeroline=False)
            st.plotly_chart(fig, use_container_width=True)

    with chart2:
        st.subheader(f"🍩 {t('cause_breakdown', lang)}")
        if "reason_level1" in col_map and "cellhr" in col_map:
            cause = detail_df.groupby(col_map["reason_level1"])[col_map["cellhr"]].sum().reset_index()
            cause.columns = ["cause", "cellhr"]
            cause = cause[cause["cellhr"] > 0].sort_values("cellhr", ascending=False)
            colors = [CAUSE_COLORS.get(c, "#bfbfbf") for c in cause["cause"]]
            fig2 = go.Figure(data=[go.Pie(
                labels=cause["cause"], values=cause["cellhr"],
                hole=0.5, marker_colors=colors,
                textinfo="percent+label", textposition="outside",
                textfont=dict(size=11),
                pull=[0.03] * len(cause),
            )])
            fig2.update_layout(height=380, showlegend=False,
                               **CHART_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

    # === TOP WORST SITES ===
    st.divider()
    st.subheader(f"🔴 {t('top_worst_sites', lang)} — Top 15")
    if "site_id" in col_map and "cellhr" in col_map:
        agg_dict = {col_map["cellhr"]: "sum"}
        if "owner" in col_map:
            agg_dict[col_map["owner"]] = "first"
        if "reason_level1" in col_map:
            agg_dict[col_map["reason_level1"]] = lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "N/A"
        if "team" in col_map:
            agg_dict[col_map["team"]] = "first"
        if "duration" in col_map:
            agg_dict[col_map["duration"]] = "sum"

        worst = detail_df.groupby(col_map["site_id"]).agg(agg_dict).reset_index()
        worst = worst.sort_values(col_map["cellhr"], ascending=False).head(15)

        display_cols = {col_map["site_id"]: t("site_id", lang)}
        if "owner" in col_map:
            display_cols[col_map["owner"]] = t("owner", lang)
        if "reason_level1" in col_map:
            display_cols[col_map["reason_level1"]] = t("reason", lang)
        if "team" in col_map:
            display_cols[col_map["team"]] = t("team", lang)
        if "duration" in col_map:
            display_cols[col_map["duration"]] = t("duration_h", lang)
        display_cols[col_map["cellhr"]] = t("cellhr_value", lang)

        worst = worst.rename(columns=display_cols)
        if t("cellhr_value", lang) in worst.columns:
            worst[t("cellhr_value", lang)] = worst[t("cellhr_value", lang)].round(1)
        if t("duration_h", lang) in worst.columns:
            worst[t("duration_h", lang)] = worst[t("duration_h", lang)].round(1)

        st.dataframe(worst, use_container_width=True, hide_index=True)
