import os
import json
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config import DATA_DIR
from i18n import t
from session_data import require_data, get_data

lang = st.session_state.get("lang", "vi")
st.markdown(f"## 📋 {t('action_tracker', lang)}")

ACTIONS_FILE = os.path.join(DATA_DIR, "ayy_actions.json")


def load_actions():
    if os.path.exists(ACTIONS_FILE):
        with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_actions(actions):
    os.makedirs(os.path.dirname(ACTIONS_FILE), exist_ok=True)
    with open(ACTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(actions, f, ensure_ascii=False, indent=2)


actions = load_actions()

tab_pending, tab_completed, tab_suggest, tab_add = st.tabs([
    f"⏳ {t('pending_actions', lang)}",
    f"✅ {t('completed_actions', lang)}",
    f"💡 {'Đề xuất tự động' if lang == 'vi' else 'Auto Suggestions'}",
    f"➕ {'Thêm mới' if lang == 'vi' else 'Add New'}",
])

with tab_pending:
    pending = [a for a in actions if a.get("status") == "pending"]
    if not pending:
        st.info("Không có hành động chờ xử lý" if lang == "vi" else "No pending actions")
    else:
        for i, action in enumerate(pending):
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 2, 1])
                with c1:
                    st.markdown(f"**{action.get('title', 'N/A')}**")
                    st.caption(action.get("description", ""))
                with c2:
                    st.caption(f"🏗️ {action.get('site_id', 'N/A')}")
                    st.caption(f"👥 {action.get('team', 'N/A')}")
                    st.caption(f"📅 {action.get('deadline', 'N/A')}")
                with c3:
                    if st.button("✅", key=f"done_{i}"):
                        for a in actions:
                            if a.get("id") == action.get("id"):
                                a["status"] = "completed"
                                a["completed_date"] = datetime.now().isoformat()
                        save_actions(actions)
                        st.rerun()

with tab_completed:
    completed = [a for a in actions if a.get("status") == "completed"]
    if not completed:
        st.info("Chưa có hành động hoàn thành" if lang == "vi" else "No completed actions")
    else:
        for action in completed:
            with st.container(border=True):
                st.markdown(f"✅ ~~{action.get('title', 'N/A')}~~")
                st.caption(f"Completed: {action.get('completed_date', 'N/A')[:10]}")

with tab_suggest:
    st.subheader("💡 " + ("Đề xuất tự động từ dữ liệu" if lang == "vi" else "Auto suggestions from data"))

    app_data = get_data()
    if app_data and app_data.get("has_data"):
        detail_df = app_data["cellhr_detail"]
        col_map = app_data["col_map"]
        if not detail_df.empty and "site_id" in col_map and "cellhr" in col_map:
            worst = detail_df.groupby(col_map["site_id"])[col_map["cellhr"]].sum().reset_index()
            worst.columns = ["site_id", "cellhr"]
            worst = worst.sort_values("cellhr", ascending=False).head(5)

            st.markdown("### " + ("Trạm cần PM khẩn cấp" if lang == "vi" else "Sites needing urgent PM"))
            for _, row in worst.iterrows():
                suggestion = (
                    f"PM trạm {row['site_id']} — Cell*h tích lũy: {row['cellhr']:,.0f}"
                    if lang == "vi" else
                    f"PM site {row['site_id']} — Accumulated Cell*h: {row['cellhr']:,.0f}"
                )
                with st.container(border=True):
                    sc1, sc2 = st.columns([5, 1])
                    with sc1:
                        st.markdown(f"🔧 {suggestion}")
                    with sc2:
                        if st.button("➕", key=f"add_sug_{row['site_id']}"):
                            new_action = {
                                "id": f"auto_{row['site_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                "title": f"PM Site {row['site_id']}",
                                "description": suggestion,
                                "site_id": row["site_id"],
                                "team": "",
                                "deadline": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                                "status": "pending",
                                "created": datetime.now().isoformat(),
                                "source": "auto",
                            }
                            actions.append(new_action)
                            save_actions(actions)
                            st.rerun()

            if "reason_level1" in col_map:
                recurring = detail_df.groupby(col_map["site_id"]).size().reset_index(name="events")
                recurring = recurring[recurring["events"] >= 5].sort_values("events", ascending=False)

                if not recurring.empty:
                    st.markdown("### " + ("Trạm lỗi lặp nhiều lần" if lang == "vi" else "Recurring fault sites"))
                    for _, row in recurring.head(5).iterrows():
                        st.markdown(f"🔄 {row['site_id']} — {row['events']} events")
    else:
        st.info("📂 " + ("Chưa có dữ liệu. Vui lòng upload file ở Dashboard." if lang == "vi"
                          else "No data. Please upload files on Dashboard."))

with tab_add:
    st.subheader("➕ " + ("Thêm hành động mới" if lang == "vi" else "Add new action"))

    with st.form("new_action"):
        title = st.text_input("Title / Tiêu đề")
        description = st.text_area("Description / Mô tả")
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            site_id = st.text_input(t("site_id", lang))
        with ac2:
            team = st.text_input(t("team", lang))
        with ac3:
            deadline = st.date_input(t("deadline", lang))

        if st.form_submit_button("💾 " + ("Lưu" if lang == "vi" else "Save"), type="primary"):
            if title:
                new_action = {
                    "id": f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "title": title,
                    "description": description,
                    "site_id": site_id,
                    "team": team,
                    "deadline": str(deadline),
                    "status": "pending",
                    "created": datetime.now().isoformat(),
                    "source": "manual",
                }
                actions.append(new_action)
                save_actions(actions)
                st.success("✅ " + ("Đã thêm" if lang == "vi" else "Added"))
                st.rerun()
            else:
                st.warning("Title required")
