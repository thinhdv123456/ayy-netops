import os

APP_NAME = "AYY NetOps"
APP_VERSION = "1.0.0"
OPERATOR = "Lê Đức Quyền"
BRANCH = "AYY Branch - VCM Myanmar"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR))

CELLHR_TARGET = 2000
TOTAL_SITES = 619
TOTAL_CELLS_PER_SITE = 6

COLORS = {
    "primary": "#007AFF",
    "success": "#34C759",
    "warning": "#FF9500",
    "danger": "#FF3B30",
    "tco_power": "#FF6B35",
    "mytel_power": "#FFB800",
    "equipment": "#5856D6",
    "transmission": "#AF52DE",
    "operation": "#30B0C7",
    "hub_down": "#FF2D55",
    "others": "#8E8E93",
    "small_cell": "#30D158",
    "majeure": "#FF3B30",
}

CHART_LAYOUT = {
    "font_family": "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "margin": dict(l=20, r=20, t=40, b=20),
    "hoverlabel": dict(
        bgcolor="rgba(28,28,30,0.92)",
        font_color="#FFFFFF",
        font_size=13,
        bordercolor="rgba(255,255,255,0.1)",
    ),
}

CAUSE_COLORS = {
    "Towerco power issue": COLORS["tco_power"],
    "Mytel Power Issue": COLORS["mytel_power"],
    "Equipment": COLORS["equipment"],
    "Transmission": COLORS["transmission"],
    "Operation": COLORS["operation"],
    "Power down at HUB site": COLORS["hub_down"],
    "Others": COLORS["others"],
    "Small Cell Down": COLORS["small_cell"],
    "Majeure cause": COLORS["majeure"],
}

TCO_COMPANIES = ["Edotco", "OCK", "PAT", "MNTH", "IGT", "EFT", "Apollo"]
TEAMS = [f"Team{i:02d}" for i in range(1, 12)] + ["Back Office"]
