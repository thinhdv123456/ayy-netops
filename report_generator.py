import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Pt
from datetime import datetime


def _find_title_shape(slide):
    for shape in slide.shapes:
        if shape.name.startswith("Arrow: Pentagon"):
            return shape
    return None


def _update_text_preserving_format(shape, new_text):
    if not shape.has_text_frame:
        return
    for para in shape.text_frame.paragraphs:
        if para.runs:
            para.runs[0].text = new_text
            for run in para.runs[1:]:
                run.text = ""
            return


def _find_date_table(slide):
    for shape in slide.shapes:
        if shape.has_table and len(list(shape.table.rows)) == 1 and len(shape.table.columns) == 1:
            return shape
    return None


def _replace_picture(slide, picture_name, img_bytes):
    for shape in list(slide.shapes):
        if shape.name == picture_name:
            left, top, width, height = shape.left, shape.top, shape.width, shape.height
            sp = shape._element
            sp.getparent().remove(sp)
            slide.shapes.add_picture(io.BytesIO(img_bytes), left, top, width, height)
            return True
    return False


def _replace_first_picture(slide, img_bytes):
    for shape in list(slide.shapes):
        if shape.name.startswith("Picture"):
            left, top, width, height = shape.left, shape.top, shape.width, shape.height
            sp = shape._element
            sp.getparent().remove(sp)
            slide.shapes.add_picture(io.BytesIO(img_bytes), left, top, width, height)
            return True
    return False


def _table_image(headers, rows, col_widths=None, header_color="#4472C4",
                 header_text_color="white", figsize=None, title=None, fontsize=9):
    n_rows = len(rows)
    if figsize is None:
        figsize = (max(6, len(headers) * 1.2), max(2, 0.35 * n_rows + 0.8))

    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    ax.axis("tight")

    tbl = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    tbl.scale(1, 1.5)

    if col_widths:
        for ci, w in enumerate(col_widths):
            for ri in range(n_rows + 1):
                tbl[ri, ci].set_width(w)

    for ci in range(len(headers)):
        cell = tbl[0, ci]
        cell.set_facecolor(header_color)
        cell.set_text_props(color=header_text_color, fontweight="bold")
        cell.set_edgecolor("#b0b0b0")

    for ri in range(1, n_rows + 1):
        for ci in range(len(headers)):
            cell = tbl[ri, ci]
            cell.set_facecolor("#f5f5f5" if ri % 2 == 0 else "white")
            cell.set_edgecolor("#b0b0b0")

    last_row_idx = n_rows
    if n_rows > 0 and rows[-1][0] in ("Total", "Tổng"):
        for ci in range(len(headers)):
            cell = tbl[last_row_idx, ci]
            cell.set_facecolor("#FFFF00")
            cell.set_text_props(fontweight="bold")

    if title:
        ax.set_title(title, fontsize=fontsize + 2, fontweight="bold", pad=8)
    fig.tight_layout(pad=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _make_team_table(data, date_range_str):
    """Slide 2 Picture 3: Team Cell*h table (Team, Target, Total Cell, Rate)"""
    tco_df = data.get("tco_power", pd.DataFrame())
    mytel_df = data.get("mytel_power", pd.DataFrame())
    detail_df = data.get("cellhr_detail", pd.DataFrame())
    col_map = data.get("col_map", {})

    teams = {}

    if not tco_df.empty:
        tco_df["Total"] = pd.to_numeric(tco_df.get("Total", pd.Series()), errors="coerce")
        team_col = "Unnamed: 0"
        if team_col in tco_df.columns:
            for team, grp in tco_df.dropna(subset=[team_col]).groupby(team_col):
                t = str(team).strip()
                if "TEAM" in t.upper():
                    teams.setdefault(t, 0)
                    teams[t] += grp["Total"].sum()

    if not mytel_df.empty:
        mytel_df["Total"] = pd.to_numeric(mytel_df.get("Total", pd.Series()), errors="coerce")
        team_col = "Unnamed: 0"
        if team_col in mytel_df.columns:
            for team, grp in mytel_df.dropna(subset=[team_col]).groupby(team_col):
                t = str(team).strip()
                if "TEAM" in t.upper():
                    teams.setdefault(t, 0)
                    teams[t] += grp["Total"].sum()

    if not detail_df.empty and "cellhr" in col_map:
        ag_col = col_map.get("alarm_group")
        if ag_col and ag_col in detail_df.columns:
            for team, grp in detail_df.groupby(ag_col):
                t = str(team).strip()
                if "TEAM" in t.upper():
                    other_causes = 0
                    if "reason_level1" in col_map:
                        non_power = grp[~grp[col_map["reason_level1"]].isin([
                            "Towerco power issue", "Mytel Power Issue"
                        ])]
                        other_causes = non_power[col_map["cellhr"]].sum()
                    teams.setdefault(t, 0)
                    teams[t] += other_causes

    if not teams:
        return None

    rpt_categories = data.get("cellhr_report", [])
    total_cellhr = sum(teams.values())
    total_target = sum(c.get("values", {}).values() for c in rpt_categories
                       if c.get("category") == "Target") if rpt_categories else 0

    n_days = 1
    if "date" in col_map and not detail_df.empty:
        dates = pd.to_datetime(detail_df[col_map["date"]], errors="coerce").dropna().dt.date.nunique()
        if dates > 0:
            n_days = dates

    from config import CELLHR_TARGET
    daily_target = CELLHR_TARGET
    total_target_all = daily_target * n_days

    n_teams = len(teams)
    site_counts = {}
    if not tco_df.empty and "Unnamed: 0" in tco_df.columns and "Sites" in tco_df.columns:
        for team, grp in tco_df.dropna(subset=["Unnamed: 0"]).groupby("Unnamed: 0"):
            t = str(team).strip()
            if "TEAM" in t.upper():
                site_counts[t] = grp["Sites"].nunique()

    total_sites = sum(site_counts.values()) if site_counts else 1
    rows = []
    grand_target = 0
    grand_total = 0
    for team in sorted(teams.keys()):
        total = teams[team]
        if site_counts and team in site_counts:
            target = total_target_all * site_counts[team] / total_sites
        else:
            target = total_target_all / n_teams
        rate = (total / target * 100) if target > 0 else 0
        rows.append([team, f"{target:.1f}", f"{total:.1f}", f"{rate:.1f}%"])
        grand_target += target
        grand_total += total

    grand_rate = (grand_total / grand_target * 100) if grand_target > 0 else 0
    rows.append(["Total", f"{grand_target:.0f}", f"{grand_total:.0f}", f"{grand_rate:.1f}%"])

    headers = ["Team", "Target", "Total Cell", "Rate"]
    return _table_image(headers, rows,
                        header_color="#4472C4",
                        figsize=(6.5, 0.35 * len(rows) + 0.8),
                        title=f"AYY Cell*Hr {date_range_str}", fontsize=9)


def _make_tco_summary_table(data):
    """Slide 2 Picture 4: TCO breakdown table (TCO, Cell*h, Rate)"""
    rpt = data.get("cellhr_report_raw")
    if rpt is not None and len(rpt) > 47:
        rows_data = []
        total = 0
        for i in range(35, 48):
            row = rpt.iloc[i]
            name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
            val = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0
            if name:
                rows_data.append((name, val))
                total += val

        rows = []
        for name, val in rows_data:
            rate = (val / total * 100) if total > 0 else 0
            rows.append([name, f"{val:.1f}", f"{rate:.1f}%"])
        rows.append(["Total", f"{total:.1f}", ""])

        return _table_image(["TCO", "Cell*h", "Rate"], rows,
                            header_color="#FFFF00", header_text_color="black",
                            figsize=(3.8, 0.33 * len(rows) + 0.6), fontsize=8)

    tco_df = data.get("tco_power", pd.DataFrame())
    if tco_df.empty:
        return None

    tco_df["Total"] = pd.to_numeric(tco_df.get("Total", pd.Series()), errors="coerce")
    if "TCO" not in tco_df.columns:
        return None

    summary = tco_df.dropna(subset=["TCO"]).groupby("TCO")["Total"].sum().reset_index()
    summary.columns = ["TCO", "Cellhr"]
    summary = summary.sort_values("Cellhr", ascending=False)
    grand = summary["Cellhr"].sum()

    rows = []
    for _, r in summary.iterrows():
        rate = (r["Cellhr"] / grand * 100) if grand > 0 else 0
        rows.append([str(r["TCO"]), f"{r['Cellhr']:.1f}", f"{rate:.1f}%"])
    rows.append(["Total", f"{grand:.1f}", ""])

    return _table_image(["TCO", "Cell*h", "Rate"], rows,
                        header_color="#FFFF00", header_text_color="black",
                        figsize=(3.8, 0.33 * len(rows) + 0.6), fontsize=8)


def _make_reason_table(data, date_range_str):
    """Slide 2 Picture 5: Reason Group table (Reason Group, Cell*h Month, Rate)"""
    categories = [
        "Operation", "Towerco power issue", "Mytel Power Issue",
        "Transmission", "Power down at HUB site", "Others",
        "Equipment", "Small Cell Down", "Majeure cause"
    ]

    detail_df = data.get("cellhr_detail", pd.DataFrame())
    col_map = data.get("col_map", {})

    if detail_df.empty or "reason_level1" not in col_map or "cellhr" not in col_map:
        return None

    cause_data = detail_df.groupby(col_map["reason_level1"])[col_map["cellhr"]].sum()
    grand = cause_data.sum()

    rows = []
    for cat in categories:
        val = cause_data.get(cat, 0)
        if pd.isna(val):
            val = 0
        rate = (val / grand * 100) if grand > 0 else 0
        rows.append([cat, f"{val:.1f}", f"{rate:.1f}%"])
    rows.append(["Total", f"{grand:.1f}", ""])

    return _table_image(["Reason Group", f"Cell*h {date_range_str}", "Rate"], rows,
                        header_color="#FFFF00", header_text_color="black",
                        figsize=(4.0, 0.33 * len(rows) + 0.6), fontsize=8)


def _make_tco_worst_table(data, date_range_str):
    """Slide 3: TCO worst sites detailed table"""
    tco_df = data.get("tco_power", pd.DataFrame())
    if tco_df.empty or "Total" not in tco_df.columns:
        return None

    tco_df["Total"] = pd.to_numeric(tco_df["Total"], errors="coerce")
    tco_df["Times down"] = pd.to_numeric(tco_df.get("Times down", pd.Series()), errors="coerce")

    team_col = "Unnamed: 0"
    tco_col = "TCO"
    site_col = "Sites"

    has_site = tco_df[site_col].astype(str).str.startswith("AYY") if site_col in tco_df.columns else pd.Series(False, index=tco_df.index)
    worst = tco_df[has_site & (tco_df["Total"] > 0)].sort_values("Total", ascending=False).head(25)
    if worst.empty:
        return None

    rows = []
    for _, r in worst.iterrows():
        site = str(r.get(site_col, "")) if pd.notna(r.get(site_col)) else ""
        tco = str(r.get(tco_col, "")) if pd.notna(r.get(tco_col)) else ""
        team = str(r.get(team_col, "")) if pd.notna(r.get(team_col)) else ""
        cellhr = r["Total"]
        days = int(r["Times down"]) if pd.notna(r.get("Times down")) else 0
        rows.append([site, tco, team, f"{cellhr:.0f}", str(days)])

    headers = ["Site", "TCO", "Team",
               "Cell down affect\nTCO Power Issue",
               "Number of days\ndown"]

    return _table_image(headers, rows,
                        header_color="#D4A017", header_text_color="black",
                        figsize=(12, 0.32 * len(rows) + 1.0), fontsize=8)


def _make_power_worst_table(data, date_range_str):
    """Slide 4: Power worst sites detailed table"""
    mytel_df = data.get("mytel_power", pd.DataFrame())
    if mytel_df.empty or "Total" not in mytel_df.columns:
        return None

    mytel_df["Total"] = pd.to_numeric(mytel_df["Total"], errors="coerce")
    mytel_df["Times down"] = pd.to_numeric(mytel_df.get("Times down", pd.Series()), errors="coerce")

    team_col = "Unnamed: 0"
    tco_col = "Unnamed: 1"
    site_col = "Unnamed: 2"

    has_site = mytel_df[site_col].astype(str).str.startswith("AYY") if site_col in mytel_df.columns else pd.Series(False, index=mytel_df.index)
    worst = mytel_df[has_site & (mytel_df["Total"] > 0)].sort_values("Total", ascending=False).head(15)
    if worst.empty:
        return None

    rows = []
    for _, r in worst.iterrows():
        site = str(r.get(site_col, "")) if pd.notna(r.get(site_col)) else ""
        tco = str(r.get(tco_col, "")) if pd.notna(r.get(tco_col)) else ""
        team = str(r.get(team_col, "")) if pd.notna(r.get(team_col)) else ""
        power = r["Total"]
        days = int(r["Times down"]) if pd.notna(r.get("Times down")) else 0
        rows.append([site, tco, team, f"{power:.0f}", str(days)])

    headers = ["Site", "TCO", "Team", "Power", "Number of days down"]

    return _table_image(headers, rows,
                        header_color="#D4A017", header_text_color="black",
                        figsize=(12, 0.32 * len(rows) + 1.0), fontsize=8)


def generate_report(template_path, data, week_num):
    prs = Presentation(template_path)
    detail_df = data.get("cellhr_detail", pd.DataFrame())
    col_map = data.get("col_map", {})

    if "date" in col_map and not detail_df.empty:
        dates = pd.to_datetime(detail_df[col_map["date"]], errors="coerce").dropna()
        if not dates.empty:
            min_date = dates.min()
            max_date = dates.max()
            date_range_str = f"{min_date.strftime('%d-%b')} To {max_date.strftime('%d-%b-%Y')}"
        else:
            date_range_str = f"Week {week_num}"
    else:
        date_range_str = f"Week {week_num}"

    # Read raw Cell_h Report for TCO breakdown data
    cellhr_bytes = data.get("_cellhr_bytes")
    if cellhr_bytes:
        try:
            data["cellhr_report_raw"] = pd.read_excel(
                io.BytesIO(cellhr_bytes), sheet_name="Cell_h Report", header=None)
        except Exception:
            data["cellhr_report_raw"] = None

    # === SLIDE 2: Cell*h Overview (3 tables as images) ===
    if len(prs.slides) >= 2:
        slide2 = prs.slides[1]
        title_shape = _find_title_shape(slide2)
        if title_shape:
            _update_text_preserving_format(title_shape, f"AYY Cell/Hr Week {week_num}")

        date_tbl = _find_date_table(slide2)
        if date_tbl and date_tbl.has_table:
            date_tbl.table.rows[0].cells[0].text = f"{date_range_str}"

        team_img = _make_team_table(data, date_range_str)
        tco_img = _make_tco_summary_table(data)
        reason_img = _make_reason_table(data, date_range_str)

        if team_img:
            _replace_picture(slide2, "Picture 3", team_img)
        if tco_img:
            _replace_picture(slide2, "Picture 4", tco_img)
        if reason_img:
            _replace_picture(slide2, "Picture 5", reason_img)

    # === SLIDE 3: TCO worst sites ===
    if len(prs.slides) >= 3:
        slide3 = prs.slides[2]
        title3 = _find_title_shape(slide3)
        if title3:
            _update_text_preserving_format(title3, f"Tco Down worst sites list in Week {week_num}")

        date_tbl3 = _find_date_table(slide3)
        if date_tbl3 and date_tbl3.has_table:
            date_tbl3.table.rows[0].cells[0].text = f"Cell/Hr Tco worst sites list {date_range_str}"

        tco_worst_img = _make_tco_worst_table(data, date_range_str)
        if tco_worst_img:
            _replace_first_picture(slide3, tco_worst_img)

    # === SLIDE 4: Power worst sites ===
    if len(prs.slides) >= 4:
        slide4 = prs.slides[3]
        title4 = _find_title_shape(slide4)
        if title4:
            _update_text_preserving_format(title4, f"Power Down worst sites list in Week {week_num}")

        date_tbl4 = _find_date_table(slide4)
        if date_tbl4 and date_tbl4.has_table:
            date_tbl4.table.rows[0].cells[0].text = f"Cell/Hr Power down worst sites list {date_range_str}"

        power_worst_img = _make_power_worst_table(data, date_range_str)
        if power_worst_img:
            _replace_first_picture(slide4, power_worst_img)

    # === SLIDES 9-10, 16-17: Transmission ===
    for si in [8, 15]:
        if len(prs.slides) > si:
            title_s = _find_title_shape(prs.slides[si])
            if title_s:
                _update_text_preserving_format(
                    title_s, f"2.1, INCIDENT TRANSMISSION {date_range_str}")
    for si in [9, 16]:
        if len(prs.slides) > si:
            title_s = _find_title_shape(prs.slides[si])
            if title_s:
                _update_text_preserving_format(
                    title_s, f"2.2  INCIDENT TRANSMISSION {date_range_str}")

    # === SLIDE 40 (last): Thank You date ===
    last_slide = prs.slides[-1]
    for shape in last_slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                if "date" in para.text.lower() and ":" in para.text:
                    for run in para.runs:
                        if "date" in run.text.lower():
                            run.text = f"Date : {datetime.now().strftime('%d-%m-%Y')}"
                            break

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
