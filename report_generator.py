import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN
from datetime import datetime


def _find_shape_by_name(slide, name_fragment):
    for shape in slide.shapes:
        if name_fragment.lower() in shape.name.lower():
            return shape
    return None


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
        if shape.has_table and shape.table.rows.__len__() == 1 and shape.table.columns.__len__() == 1:
            return shape
    return None


def _replace_shapes_with_images(slide, name_to_img):
    targets = {}
    for shape in slide.shapes:
        if shape.name in name_to_img and name_to_img[shape.name]:
            targets[shape.name] = (shape.left, shape.top, shape.width, shape.height)

    for shape in list(slide.shapes):
        if shape.name in targets:
            sp = shape._element
            sp.getparent().remove(sp)

    for name, (left, top, width, height) in targets.items():
        slide.shapes.add_picture(io.BytesIO(name_to_img[name]), left, top, width, height)


def _replace_first_picture(slide, img_bytes):
    for shape in list(slide.shapes):
        if shape.name.startswith("Picture"):
            left, top, width, height = shape.left, shape.top, shape.width, shape.height
            sp = shape._element
            sp.getparent().remove(sp)
            slide.shapes.add_picture(io.BytesIO(img_bytes), left, top, width, height)
            return True
    return False


def _replace_image(slide, old_image_name, img_bytes, left=None, top=None, width=None, height=None):
    old_shape = None
    for shape in slide.shapes:
        if shape.name == old_image_name:
            old_shape = shape
            break
    if old_shape is None:
        for shape in slide.shapes:
            if hasattr(shape, "image"):
                try:
                    _ = shape.image
                    old_shape = shape
                    break
                except Exception:
                    continue
    if old_shape is None:
        return

    if left is None:
        left = old_shape.left
    if top is None:
        top = old_shape.top
    if width is None:
        width = old_shape.width
    if height is None:
        height = old_shape.height

    sp = old_shape._element
    sp.getparent().remove(sp)

    img_stream = io.BytesIO(img_bytes)
    slide.shapes.add_picture(img_stream, left, top, width, height)


def _make_cellhr_daily_chart(detail_df, col_map, target, date_range_str):
    if "date" not in col_map or "cellhr" not in col_map:
        return None

    daily = detail_df.groupby(col_map["date"])[col_map["cellhr"]].sum().reset_index()
    daily.columns = ["date", "cellhr"]
    daily = daily.sort_values("date")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(len(daily)), daily["cellhr"], color="#c0392b", width=0.6, edgecolor="white")
    ax.axhline(y=target, color="#27ae60", linestyle="--", linewidth=2, label=f"Target: {target:,}")

    for i, v in enumerate(daily["cellhr"]):
        ax.text(i, v + target * 0.02, f"{v:,.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    dates = [str(d)[:10] if hasattr(d, "strftime") else str(d)[:10] for d in daily["date"]]
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Cell*h", fontsize=11)
    ax.set_title(f"AYY Cell*h Daily — {date_range_str}", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _make_cause_pie(detail_df, col_map):
    if "reason_level1" not in col_map or "cellhr" not in col_map:
        return None

    cause = detail_df.groupby(col_map["reason_level1"])[col_map["cellhr"]].sum().reset_index()
    cause.columns = ["cause", "cellhr"]
    cause = cause[cause["cellhr"] > 0].sort_values("cellhr", ascending=False)

    if cause.empty:
        return None

    colors = ["#c0392b", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6", "#1abc9c", "#95a5a6"]
    fig, ax = plt.subplots(figsize=(5, 5))
    wedges, texts, autotexts = ax.pie(
        cause["cellhr"], labels=cause["cause"], autopct="%1.1f%%",
        colors=colors[:len(cause)], startangle=90, pctdistance=0.75,
        textprops={"fontsize": 8},
    )
    for t in autotexts:
        t.set_fontsize(7)
    ax.set_title("By Cause", fontsize=11, fontweight="bold")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _make_worst_sites_table_image(df, col_map, title, top_n=15, color="#c0392b"):
    if "site_id" not in col_map or "cellhr" not in col_map:
        return None

    agg = {col_map["cellhr"]: "sum"}
    extra_cols = []
    if "owner" in col_map:
        agg[col_map["owner"]] = "first"
        extra_cols.append(("owner", col_map["owner"]))
    if "reason_level1" in col_map:
        agg[col_map["reason_level1"]] = lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else ""
        extra_cols.append(("cause", col_map["reason_level1"]))

    worst = df.groupby(col_map["site_id"]).agg(agg).reset_index()
    worst = worst.sort_values(col_map["cellhr"], ascending=False).head(top_n)

    headers = ["#", "Site ID", "Cell*h"]
    col_keys = [None, col_map["site_id"], col_map["cellhr"]]
    for label, col in extra_cols:
        headers.append(label.title())
        col_keys.append(col)

    cell_text = []
    for i, (_, row) in enumerate(worst.iterrows(), 1):
        line = [str(i)]
        for key in col_keys[1:]:
            val = row[key]
            if isinstance(val, float):
                line.append(f"{val:,.0f}")
            else:
                line.append(str(val)[:25])
        cell_text.append(line)

    fig, ax = plt.subplots(figsize=(10, 0.4 * len(cell_text) + 1.2))
    ax.axis("off")
    table = ax.table(
        cellText=cell_text, colLabels=headers,
        loc="center", cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor(color)
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("#f9f9f9" if row % 2 == 0 else "white")
        cell.set_edgecolor("#dddddd")

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _make_team_cellhr_image(detail_df, col_map):
    if "team" not in col_map or "cellhr" not in col_map:
        return None

    team_data = detail_df.groupby(col_map["team"])[col_map["cellhr"]].sum().reset_index()
    team_data.columns = ["team", "cellhr"]
    team_data = team_data.sort_values("cellhr", ascending=True)

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.barh(team_data["team"], team_data["cellhr"], color="#3498db", edgecolor="white")
    for bar, v in zip(bars, team_data["cellhr"]):
        ax.text(v + max(team_data["cellhr"]) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v:,.0f}", va="center", fontsize=8)
    ax.set_xlabel("Cell*h", fontsize=10)
    ax.set_title("Cell*h by Team", fontsize=11, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_report(template_path, data, week_num):
    prs = Presentation(template_path)
    detail_df = data.get("cellhr_detail", pd.DataFrame())
    col_map = data.get("col_map", {})
    tco_df = data.get("tco_power", pd.DataFrame())
    mytel_df = data.get("mytel_power", pd.DataFrame())
    tx_report = data.get("tx_report", pd.DataFrame())

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

    from config import CELLHR_TARGET
    target = CELLHR_TARGET

    # === SLIDE 2: Cell*h Overview ===
    if len(prs.slides) >= 2:
        slide2 = prs.slides[1]
        title_shape = _find_title_shape(slide2)
        if title_shape:
            _update_text_preserving_format(title_shape, f"AYY Cell/Hr Week {week_num}")

        date_tbl = _find_date_table(slide2)
        if date_tbl and date_tbl.has_table:
            date_tbl.table.rows[0].cells[0].text = f"{date_range_str} Week {week_num}"

        if not detail_df.empty:
            chart_img = _make_cellhr_daily_chart(detail_df, col_map, target, date_range_str)
            cause_img = _make_cause_pie(detail_df, col_map)
            team_img = _make_team_cellhr_image(detail_df, col_map)

            replacements = {"Picture 3": chart_img, "Picture 4": cause_img, "Picture 5": team_img}
            _replace_shapes_with_images(slide2, replacements)

    # === SLIDE 3: TCO worst sites ===
    if len(prs.slides) >= 3:
        slide3 = prs.slides[2]
        title3 = _find_title_shape(slide3)
        if title3:
            _update_text_preserving_format(title3, f"Tco Down worst sites list in Week {week_num}")

        date_tbl3 = _find_date_table(slide3)
        if date_tbl3 and date_tbl3.has_table:
            date_tbl3.table.rows[0].cells[0].text = f"Cell/Hr Tco worst sites list {date_range_str}"

        if not tco_df.empty:
            tco_col_map = {}
            for col in tco_df.columns:
                cl = str(col).lower().strip()
                if cl == "sites" or (cl == "site_id"):
                    tco_col_map["site_id"] = col
                elif cl == "total" or ("cell*h" in cl) or ("cellhr" in cl):
                    tco_col_map["cellhr"] = col
                elif cl == "tco" or cl == "owner":
                    tco_col_map["owner"] = col

            if "cellhr" in tco_col_map:
                tco_df[tco_col_map["cellhr"]] = pd.to_numeric(tco_df[tco_col_map["cellhr"]], errors="coerce")

            tco_img = _make_worst_sites_table_image(tco_df, tco_col_map,
                                                     f"TCO Worst Sites — {date_range_str}", color="#e67e22")
            if tco_img:
                _replace_first_picture(slide3, tco_img)

    # === SLIDE 4: Power worst sites ===
    if len(prs.slides) >= 4:
        slide4 = prs.slides[3]
        title4 = _find_title_shape(slide4)
        if title4:
            _update_text_preserving_format(title4, f"Power Down worst sites list in Week {week_num}")

        date_tbl4 = _find_date_table(slide4)
        if date_tbl4 and date_tbl4.has_table:
            date_tbl4.table.rows[0].cells[0].text = f"Cell/Hr Power down worst sites list {date_range_str}"

        if not detail_df.empty and "reason_level1" in col_map:
            power_causes = ["Towerco power issue", "Mytel Power Issue", "Power down at HUB site"]
            power_df = detail_df[detail_df[col_map["reason_level1"]].isin(power_causes)]
            if not power_df.empty:
                power_img = _make_worst_sites_table_image(power_df, col_map,
                                                          f"Power Down Worst Sites — {date_range_str}", color="#c0392b")
                if power_img:
                    _replace_first_picture(slide4, power_img)

    # === SLIDE 16-17: Weekly Transmission ===
    if len(prs.slides) >= 16 and not tx_report.empty:
        slide16 = prs.slides[15]
        title16 = _find_title_shape(slide16)
        if title16:
            _update_text_preserving_format(title16, f"2.1, INCIDENT TRANSMISSION {date_range_str}")

    if len(prs.slides) >= 17:
        slide17 = prs.slides[16]
        title17 = _find_title_shape(slide17)
        if title17:
            _update_text_preserving_format(title17, f"2.2  INCIDENT TRANSMISSION {date_range_str}")

        if not detail_df.empty and "reason_level1" in col_map:
            tx_detail = data.get("tx_detail", pd.DataFrame())
            if not tx_detail.empty:
                route_col = None
                for col in tx_detail.columns:
                    cl = str(col).lower()
                    if "route" in cl or "cable" in cl or "link" in cl:
                        route_col = col
                        break

                if route_col:
                    route_counts = tx_detail[route_col].value_counts().reset_index()
                    route_counts.columns = ["route", "incidents"]
                    repeated = route_counts[route_counts["incidents"] >= 2].sort_values("incidents", ascending=False)

                    if not repeated.empty:
                        for shape in slide17.shapes:
                            if shape.name == "TextBox 7" and shape.has_text_frame:
                                tf = shape.text_frame
                                tf.clear()
                                p0 = tf.paragraphs[0]
                                run0 = p0.add_run()
                                run0.text = "These are list routes happened >=2 incidents:"
                                run0.font.bold = True
                                run0.font.size = Pt(14)

                                for i, (_, row) in enumerate(repeated.head(10).iterrows(), 1):
                                    p = tf.add_paragraph()
                                    r = p.add_run()
                                    r.text = f"{i}. {row['route']} — {row['incidents']} times"
                                    r.font.size = Pt(12)
                                break

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
