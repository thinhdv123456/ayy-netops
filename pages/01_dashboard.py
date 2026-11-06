import os
import shutil
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from config import CELLHR_TARGET, TOTAL_SITES, CAUSE_COLORS, DATA_DIR, CHART_LAYOUT
from i18n import t
from data_loader import find_data_files, load_cellhr_detail, load_tco_power, load_mytel_power, load_manpower
from database import is_file_imported, import_cellhr_file, get_import_history, query_cellhr_events, get_all_dates

lang = st.session_state.get("lang", "vi")

st.markdown(f"## 🏠 {t('dashboard', lang)}")

# === DATA SOURCE ===
tab_live, tab_history, tab_upload = st.tabs([
    "📂 " + ("File trực tiếp" if lang == "vi" else "Live File"),
    "🗄️ " + ("Lịch sử Database" if lang == "vi" else "Database History"),
    "📤 " + ("Tải file mới" if lang == "vi" else "Upload New File"),
])

with tab_live:
    cellhr_files, summary_files = find_data_files()
    if not cellhr_files:
        st.warning("Không tìm thấy file Cellhr Daily review*.xlsx" if lang == "vi"
                    else "No Cellhr Daily review*.xlsx found")
        st.info(f"📁 Data directory: `{DATA_DIR}`")
        st.stop()

    selected_cellhr = st.selectbox(
        "📂 Cellhr file:",
        cellhr_files,
        format_func=lambda x: os.path.basename(x),
    )

    imported, import_info = is_file_imported(selected_cellhr)
    if imported:
        st.success(f"✅ {'Đã lưu vào DB' if lang == 'vi' else 'Already in DB'} — {import_info[2]}")
    else:
        if st.button("💾 " + ("Lưu vào Database" if lang == "vi" else "Save to Database"), type="primary"):
            with st.spinner("Importing..." if lang == "en" else "Đang nhập..."):
                detail_df, col_map = load_cellhr_detail(selected_cellhr)
                tco_df = load_tco_power(selected_cellhr)
                mytel_df = load_mytel_power(selected_cellhr)
                tx_df = pd.DataFrame()
                ok, msg = import_cellhr_file(selected_cellhr, detail_df, col_map, tco_df, mytel_df, tx_df)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.warning(msg)

    detail_df, col_map = load_cellhr_detail(selected_cellhr)
    selected_summary = summary_files[0] if summary_files else None

with tab_history:
    history = get_import_history()
    if history.empty:
        st.info("Chưa có dữ liệu trong database" if lang == "vi" else "No data in database yet")
    else:
        st.dataframe(history[["filename", "import_date", "period_start", "period_end", "total_records", "total_cellhr"]],
                      use_container_width=True, hide_index=True)

with tab_upload:
    st.markdown("### 📤 " + ("Tải dữ liệu mới" if lang == "vi" else "Upload New Data"))
    st.caption("Cellhr Daily review*.xlsx, SUMMARY_AYY Database.xlsx" if lang == "vi"
               else "Cellhr Daily review*.xlsx, SUMMARY_AYY Database.xlsx")

    uploaded_files = st.file_uploader(
        "Excel (.xlsx)" if lang == "vi" else "Excel files (.xlsx)",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key="file_uploader",
    )

    if uploaded_files:
        for uf in uploaded_files:
            dest_path = os.path.join(DATA_DIR, uf.name)
            exists = os.path.exists(dest_path)
            status = "⚠️ " + ("Sẽ ghi đè" if lang == "vi" else "Will overwrite") if exists else "🆕 " + ("File mới" if lang == "vi" else "New file")
            st.markdown(f"- **{uf.name}** — {status} ({uf.size / 1024:.0f} KB)")

        if st.button("💾 " + ("Lưu vào thư mục dữ liệu" if lang == "vi" else "Save to data folder"),
                      type="primary", key="save_uploads"):
            saved = 0
            for uf in uploaded_files:
                dest_path = os.path.join(DATA_DIR, uf.name)
                with open(dest_path, "wb") as f:
                    f.write(uf.getbuffer())
                saved += 1
            st.success(f"✅ {'Đã lưu' if lang == 'vi' else 'Saved'} {saved} file(s) → `{DATA_DIR}`")
            st.info("🔄 " + ("Tải lại trang để sử dụng dữ liệu mới" if lang == "vi"
                              else "Reload the page to use new data"))
            st.rerun()
    else:
        st.info("📁 " + ("Kéo thả file Excel vào đây hoặc bấm Browse" if lang == "vi"
                          else "Drag & drop Excel files here or click Browse"))

    st.divider()
    st.markdown("**📂 " + ("File hiện có:" if lang == "vi" else "Existing files:") + "**")
    existing = [f for f in os.listdir(DATA_DIR) if f.endswith((".xlsx", ".xls"))]
    if existing:
        for f in sorted(existing):
            size_kb = os.path.getsize(os.path.join(DATA_DIR, f)) / 1024
            st.caption(f"📄 {f} ({size_kb:.0f} KB)")
    else:
        st.caption("(" + ("Chưa có file" if lang == "vi" else "No files yet") + ")")

# === KPI METRICS ===
if detail_df.empty:
    st.warning(t("no_data", lang))
    st.stop()

if "cellhr" in col_map:
    total_cellhr = detail_df[col_map["cellhr"]].sum()
else:
    total_cellhr = 0

sites_with_events = detail_df[col_map["site_id"]].nunique() if "site_id" in col_map else 0
availability = max(0, (1 - sites_with_events / TOTAL_SITES) * 100) if TOTAL_SITES > 0 else 0

manpower_df = pd.DataFrame()
if selected_summary:
    manpower_df = load_manpower(selected_summary)

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
              delta=f"{'Vượt' if lang == 'vi' else 'Over'} {total_cellhr - CELLHR_TARGET:,.0f}" if over else f"OK",
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
