import json
import re
from datetime import date, datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Personal Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="auto",
)

DATA_FILE = Path(__file__).resolve().parent / "expenses.json"
BUDGET_FILE = Path(__file__).resolve().parent / "budgets.json"

CATEGORIES = [
    "Food",
    "Travel",
    "Bills",
    "Grocery",
    "Shopping",
    "Education",
    "Entertainment",
    "Other",
]

CATEGORY_COLORS = {
    "Food": "#F59E0B",
    "Travel": "#38BDF8",
    "Bills": "#F87171",
    "Grocery": "#34D399",
    "Shopping": "#A78BFA",
    "Education": "#2DD4BF",
    "Entertainment": "#F472B6",
    "Other": "#94A3B8",
}

CATEGORY_ICONS = {
    "Food": "🍔",
    "Travel": "🚗",
    "Bills": "🧾",
    "Grocery": "🛒",
    "Shopping": "🛍️",
    "Education": "🎓",
    "Entertainment": "🎬",
    "Other": "📦",
}

NAV_ITEMS = {
    "📊  Dashboard": "Dashboard",
    "➕  Add Expense": "Add Expense",
    "🔎  View / Search": "View / Search",
    "✏️  Edit Expense": "Edit Expense",
    "🗑️  Delete Expense": "Delete Expense",
    "🧩  Category Analysis": "Category Analysis",
    "📅  Monthly Analysis": "Monthly Analysis",
    "🎯  Budget": "Budget",
}

THEMES = {
    "dark": {
        "bg": "#0B1017",
        "surface": "#121923",
        "surface2": "#182130",
        "border": "#233044",
        "text": "#E8EDF5",
        "muted": "#8A97AB",
        "input": "#0E1520",
        "accent": "#2DD4BF",
        "accent_soft": "rgba(45, 212, 191, 0.14)",
        "shadow": "0 8px 24px rgba(0, 0, 0, 0.35)",
        "button_text": "#04211D",
    },
    "light": {
        "bg": "#F3F6FA",
        "surface": "#FFFFFF",
        "surface2": "#F1F5F9",
        "border": "#E2E8F0",
        "text": "#0F172A",
        "muted": "#64748B",
        "input": "#FFFFFF",
        "accent": "#0D9488",
        "accent_soft": "rgba(13, 148, 136, 0.10)",
        "shadow": "0 6px 20px rgba(15, 23, 42, 0.07)",
        "button_text": "#FFFFFF",
    },
}


# ============================================================
# SESSION STATE
# ============================================================

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True


NAV_KEYS = list(NAV_ITEMS.keys())

if "nav_sidebar" not in st.session_state:
    st.session_state.nav_sidebar = NAV_KEYS[0]

if "close_drawer" not in st.session_state:
    st.session_state.close_drawer = False


def _nav_changed():
    # On phones the sidebar is a drawer: close it after a page is picked
    st.session_state.close_drawer = True


def is_mobile():
    """Phone detection: sidebar 'Layout' override first, then the browser's User-Agent."""
    mode = st.session_state.get("view_mode", "Auto")

    if mode == "Mobile":
        return True
    if mode == "Desktop":
        return False

    try:
        agent = st.context.headers.get("User-Agent", "")
    except Exception:
        return False

    return bool(re.search(r"Mobi|iPhone|iPod|Android.+Mobile", agent, re.I))


def theme():
    return THEMES["dark"] if st.session_state.dark_mode else THEMES["light"]


# ============================================================
# DATA FUNCTIONS
# ============================================================

def load_expenses():
    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_expenses(expenses):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(expenses, file, indent=4)


def load_budgets():
    if not BUDGET_FILE.exists():
        return {}

    try:
        with open(BUDGET_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except (json.JSONDecodeError, OSError):
        return {}


def save_budgets(budgets):
    with open(BUDGET_FILE, "w", encoding="utf-8") as file:
        json.dump(budgets, file, indent=4)


def format_rupees(amount):
    amount = float(amount)
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{abs(amount):,.2f}"


def parse_saved_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def expenses_to_dataframe(expenses):
    if not expenses:
        return pd.DataFrame(columns=["name", "amount", "category", "date"])

    df = pd.DataFrame(expenses)

    for column in ["name", "amount", "category", "date"]:
        if column not in df.columns:
            df[column] = ""

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df[["name", "amount", "category", "date"]]


def expense_label(index, expense):
    name = str(expense.get("name", "Unnamed"))
    amount = float(expense.get("amount", 0))
    category = str(expense.get("category", "Other"))

    return f"{index + 1}. {name} • {format_rupees(amount)} • {category}"


def month_total(df, month_key):
    if df.empty:
        return 0.0

    mask = df["date"].dt.strftime("%Y-%m") == month_key
    return float(df.loc[mask, "amount"].sum())


def previous_month_key(today=None):
    today = today or date.today()
    year, month = today.year, today.month - 1

    if month == 0:
        year, month = year - 1, 12

    return f"{year}-{month:02d}"


# ============================================================
# THEME / CSS
# ============================================================

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

/* ---------- Global ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: var(--bg) !important;
    color: var(--text);
    font-family: 'Manrope', 'Segoe UI', system-ui, sans-serif;
}

.stApp *:not([class*="material"]):not([data-testid="stIconMaterial"]) {
    font-family: 'Manrope', 'Segoe UI', system-ui, sans-serif;
}

/* Remove the white top bar, deploy button, menu and footer */
header[data-testid="stHeader"],
[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
    border: 0 !important;
}
[data-testid="stToolbarActions"],
[data-testid="stMainMenu"],
[data-testid="stAppDeployButton"],
.stDeployButton,
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
footer {
    display: none !important;
    visibility: hidden !important;
}

/* Sidebar open button must always be visible */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 1000001 !important;
}

/* Zero-height helper iframes should not take space */
[data-testid="stElementContainer"]:has(iframe[height="0"]) {
    position: absolute;
    width: 0;
    height: 0;
    overflow: hidden;
}
[data-testid="stHeader"] button,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button {
    color: var(--muted) !important;
}

.main .block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 2.2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--text) !important;
    letter-spacing: -0.02em;
}
p, li, label, span { color: var(--text); }
hr { border-color: var(--border) !important; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] > div { padding-top: 0.5rem; }

.brand { display: flex; align-items: center; gap: 12px; padding: 8px 4px 22px 4px; }
.brand-logo {
    width: 40px; height: 40px; border-radius: 12px;
    background: var(--accent-soft);
    border: 1px solid var(--accent);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
}
.brand-title { font-size: 17px; font-weight: 800; color: var(--text); line-height: 1.2; }
.brand-sub { font-size: 12px; color: var(--muted); }

.nav-label {
    font-size: 12px; font-weight: 700; color: var(--muted);
    letter-spacing: 0.04em; margin: 4px 0 8px 6px;
}

section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 4px; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    width: 100%;
    padding: 10px 14px;
    border-radius: 10px;
    border: 1px solid transparent;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label p {
    color: var(--muted) !important;
    font-weight: 600;
    font-size: 14px;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background: var(--surface2);
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background: var(--accent-soft);
    border-color: var(--accent);
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
    color: var(--text) !important;
}

section[data-testid="stSidebar"] [data-testid="stToggle"] p { color: var(--text) !important; font-weight: 600; }
.sidebar-foot { font-size: 12px; color: var(--muted); line-height: 1.7; }

/* ---------- Page header ---------- */
.page-head { margin-bottom: 22px; }
.page-title { font-size: 28px; font-weight: 800; color: var(--text); letter-spacing: -0.02em; }
.page-sub { font-size: 14px; color: var(--muted); margin-top: 4px; }

.dash-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 22px; gap: 20px; flex-wrap: wrap; }
.dash-chip {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 999px; padding: 8px 16px; font-size: 13px; color: var(--muted); font-weight: 600;
}
.dash-chip b { color: var(--accent); font-weight: 800; }

/* ---------- KPI cards ---------- */
.kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 20px;
    min-height: 132px;
    box-shadow: var(--shadow);
}
.kpi-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.kpi-title { font-size: 13px; font-weight: 600; color: var(--muted); }
.kpi-icon {
    width: 34px; height: 34px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.kpi-value { font-size: 27px; font-weight: 800; color: var(--text); letter-spacing: -0.02em; line-height: 1.15; }
.kpi-desc { font-size: 12px; color: var(--muted); margin-top: 8px; }
.up { color: #F87171 !important; font-weight: 700; }
.down { color: #34D399 !important; font-weight: 700; }

/* ---------- Section titles ---------- */
.sec-title { font-size: 17px; font-weight: 800; color: var(--text); margin-bottom: 2px; }
.sec-sub { font-size: 12.5px; color: var(--muted); margin-bottom: 6px; }

/* ---------- Bordered containers (chart cards) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface);
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    box-shadow: var(--shadow);
    padding: 6px 8px;
}

/* ---------- Forms ---------- */
[data-testid="stForm"] {
    background: var(--surface);
    border: 1px solid var(--border) !important;
    border-radius: 16px;
    padding: 24px;
    box-shadow: var(--shadow);
}

/* ---------- Inputs ---------- */
[data-testid="stWidgetLabel"] p, label[data-testid="stWidgetLabel"] {
    color: var(--text) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}

[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="textarea"],
[data-baseweb="select"] > div {
    background: var(--field) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
}
[data-baseweb="input"]:focus-within,
[data-baseweb="select"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
}
input, textarea {
    background: transparent !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    caret-color: var(--accent);
}
input::placeholder, textarea::placeholder {
    color: var(--muted) !important;
    -webkit-text-fill-color: var(--muted) !important;
    opacity: 0.75 !important;
}
[data-baseweb="select"] * { color: var(--text) !important; }
[data-baseweb="select"] svg { fill: var(--muted) !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
[data-testid="stSelectbox"] [data-baseweb="select"] div[role="combobox"] {
    background: var(--field) !important;
    border-color: var(--border) !important;
}

/* No white boxes anywhere inside input widgets, and always-readable text */
[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stTextInput"] div[data-baseweb="base-input"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInput"] div[data-baseweb="input"],
[data-testid="stNumberInput"] div[data-baseweb="base-input"],
[data-testid="stNumberInputContainer"],
[data-testid="stDateInput"] div[data-baseweb="input"],
[data-testid="stDateInput"] div[data-baseweb="base-input"],
[data-testid="stDateInputField"],
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div {
    background-color: var(--field) !important;
}

[data-testid="stTextInput"] *,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] *,
[data-testid="stSelectbox"] * {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
}

[data-testid="InputInstructions"],
[data-testid="InputInstructions"] * {
    color: var(--muted) !important;
    -webkit-text-fill-color: var(--muted) !important;
    background: transparent !important;
}

/* Dropdowns: every layer of the closed select gets the field colour */
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] * {
    background-color: var(--field) !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] svg {
    fill: var(--muted) !important;
}

/* Soft, consistent borders on all input boxes (no harsh white outline) */
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"],
[data-testid="stDateInputField"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within,
[data-testid="stDateInputField"]:focus-within,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
}
[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stTextInput"] div[data-baseweb="base-input"],
[data-testid="stNumberInput"] div[data-baseweb="input"],
[data-testid="stNumberInput"] div[data-baseweb="base-input"],
[data-testid="stDateInput"] div[data-baseweb="input"],
[data-testid="stDateInput"] div[data-baseweb="base-input"] {
    border-color: transparent !important;
    box-shadow: none !important;
}

[data-testid="stNumberInput"] button {
    background: var(--surface2) !important;
    color: var(--text) !important;
    border: 0 !important;
}
[data-testid="stNumberInput"] button svg { fill: var(--text) !important; }

/* Dropdown + calendar popups */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
ul[role="listbox"],
[data-baseweb="calendar"] {
    background: var(--surface2) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}
ul[role="listbox"] li, [data-baseweb="calendar"] * { color: var(--text) !important; }
ul[role="listbox"] li:hover { background: var(--accent-soft) !important; }

/* ---------- Buttons ---------- */
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
    width: 100%;
    min-height: 44px;
    border: 0 !important;
    border-radius: 10px;
    font-weight: 700;
    background: var(--accent) !important;
    color: var(--button-text) !important;
    transition: filter 0.15s ease, transform 0.05s ease;
}
.stButton > button p,
[data-testid="stFormSubmitButton"] > button p {
    color: var(--button-text) !important;
    font-weight: 700;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    filter: brightness(1.08);
}
.stButton > button:active,
[data-testid="stFormSubmitButton"] > button:active { transform: translateY(1px); }
.stButton > button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

/* ---------- Checkbox / alerts ---------- */
[data-testid="stCheckbox"] p { color: var(--text) !important; }
[data-testid="stAlert"] { border-radius: 12px; }

/* ---------- Custom tables ---------- */
.tbl-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: auto;
    box-shadow: var(--shadow);
}
table.tbl { width: 100%; border-collapse: collapse; font-size: 14px; }
table.tbl th {
    position: sticky; top: 0;
    background: var(--surface2);
    color: var(--muted);
    font-weight: 700; font-size: 12.5px;
    text-align: left;
    padding: 12px 18px;
    border-bottom: 1px solid var(--border);
}
table.tbl td {
    padding: 12px 18px;
    color: var(--text);
    border-bottom: 1px solid var(--border);
}
table.tbl tr:last-child td { border-bottom: 0; }
table.tbl tr:hover td { background: var(--accent-soft); }
table.tbl .num { text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; }
table.tbl th.num { text-align: right; }

.pill {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 4px 11px; border-radius: 999px;
    font-size: 12.5px; font-weight: 700;
}
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }

.mini-bar { height: 6px; background: var(--surface2); border-radius: 999px; min-width: 120px; overflow: hidden; }
.mini-bar > div { height: 100%; border-radius: 999px; }

/* ---------- Budget bar ---------- */
.budget-track { height: 14px; background: var(--surface2); border-radius: 999px; overflow: hidden; border: 1px solid var(--border); }
.budget-fill { height: 100%; border-radius: 999px; }
.budget-meta { display: flex; justify-content: space-between; font-size: 13px; color: var(--muted); margin-top: 10px; font-weight: 600; }

/* ---------- Dropdowns (selectbox): dark box, bold readable text, visible arrow ---------- */
div[data-baseweb="select"],
div[data-baseweb="select"] *,
div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div > div,
div[data-baseweb="select"] div[role="combobox"],
div[data-baseweb="select"] input,
div[data-baseweb="select"] span {
    background-color: var(--field) !important;
    background-image: none !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
    font-weight: 600 !important;
}
div[data-baseweb="select"] > div {
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    min-height: 44px;
}
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="select"] > div:hover {
    border-color: var(--accent) !important;
}
div[data-baseweb="select"] svg {
    fill: var(--accent) !important;
    color: var(--accent) !important;
    width: 20px;
    height: 20px;
}

/* Dropdown list that opens when you click the box */
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] [role="option"] * {
    background-color: var(--surface2) !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    font-weight: 600;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] [role="option"]:hover,
div[data-baseweb="popover"] [role="option"][aria-selected="true"] {
    background-color: var(--accent-soft) !important;
}

/* ---------- Scrollbars ---------- */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
::-webkit-scrollbar-track { background: transparent; }

/* ---------- Phone layout (rendered only on phones) ---------- */
[data-testid="stMainBlockContainer"]:has(.m-appbar) { padding-top: 4.6rem !important; }

.m-appbar {
    position: fixed; top: 0; left: 0; right: 0; height: 58px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: center; gap: 10px;
    z-index: 999;
}
.m-menu-btn {
    position: absolute; left: 10px; top: 8px;
    width: 42px; height: 42px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-soft);
    border: 1px solid var(--accent);
    color: var(--text); font-size: 22px; line-height: 1;
    cursor: pointer; user-select: none;
    z-index: 1000002;
}
.m-appbar .brand-logo { width: 30px; height: 30px; border-radius: 9px; font-size: 15px; }
.m-appbar-title { font-size: 16px; font-weight: 800; color: var(--text); }

.m-hero {
    background: var(--accent-soft);
    border: 1px solid var(--accent);
    border-radius: 18px;
    padding: 18px 18px 16px 18px;
    margin-bottom: 14px;
}
.m-hero-label { font-size: 13px; font-weight: 600; color: var(--muted); }
.m-hero-value { font-size: 32px; font-weight: 800; color: var(--text); letter-spacing: -0.02em; margin: 4px 0; }
.m-hero-sub { font-size: 12.5px; color: var(--muted); }
.m-hero .budget-track { height: 8px; margin-top: 14px; }

.exp-list { display: flex; flex-direction: column; gap: 10px; }
.exp-card {
    display: flex; align-items: center; gap: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 12px 14px;
}
.exp-ico {
    width: 42px; height: 42px; border-radius: 12px; flex: 0 0 42px;
    display: flex; align-items: center; justify-content: center; font-size: 19px;
}
.exp-main { flex: 1; min-width: 0; }
.exp-name { font-size: 14.5px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.exp-meta { font-size: 12px; color: var(--muted); margin-top: 2px; }
.exp-amt { font-size: 14.5px; font-weight: 800; color: var(--text); font-variant-numeric: tabular-nums; }

/* Sidebar open/close button: always visible and easy to tap */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    box-shadow: var(--shadow);
}

/* ---------- Tablet & mobile ---------- */
@media (max-width: 768px) {
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding: 3.4rem 0.9rem 2rem 0.9rem;
    }

    /* Sidebar becomes a clean slide-over drawer */
    section[data-testid="stSidebar"] {
        width: min(82vw, 320px) !important;
        min-width: 0 !important;
        box-shadow: 8px 0 30px rgba(0, 0, 0, 0.45);
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label { padding: 13px 14px; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label p { font-size: 15px; }

    .page-title { font-size: 22px; }
    .page-sub { font-size: 13px; }
    .page-head, .dash-head { margin-bottom: 14px; }
    .dash-chip { width: 100%; text-align: center; }

    .kpi { padding: 14px; min-height: auto; border-radius: 14px; }
    .kpi-top { margin-bottom: 10px; }
    .kpi-value { font-size: 21px; }
    .kpi-desc { font-size: 11.5px; }
    .kpi-icon { width: 30px; height: 30px; font-size: 14px; }

    .sec-title { font-size: 16px; }

    div[data-testid="stVerticalBlockBorderWrapper"] { padding: 4px; border-radius: 14px !important; }
    [data-testid="stForm"] { padding: 16px; }

    input, textarea { font-size: 16px !important; }

    table.tbl { min-width: 520px; font-size: 13px; }
    table.tbl th, table.tbl td { padding: 10px 12px; white-space: nowrap; }
    .tbl-wrap { -webkit-overflow-scrolling: touch; border-radius: 14px; }
}

/* ---------- Mobile: KPI cards in 2 columns, everything else stacked ---------- */
@media (max-width: 640px) {
    [data-testid="stHorizontalBlock"]:has(.kpi) {
        flex-wrap: wrap !important;
        gap: 0.6rem !important;
    }
    [data-testid="stHorizontalBlock"]:has(.kpi) > [data-testid="stColumn"]:has(.kpi),
    [data-testid="stHorizontalBlock"]:has(.kpi) > [data-testid="column"]:has(.kpi) {
        flex: 1 1 calc(50% - 0.6rem) !important;
        min-width: calc(50% - 0.6rem) !important;
        width: calc(50% - 0.6rem) !important;
    }
    [data-testid="stHorizontalBlock"]:has(.kpi) > [data-testid="stColumn"]:has(.kpi):last-child:nth-child(odd),
    [data-testid="stHorizontalBlock"]:has(.kpi) > [data-testid="column"]:has(.kpi):last-child:nth-child(odd) {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: 100% !important;
    }
}
</style>
"""


def html(markup):
    cleaned = "\n".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def inject_css():
    t = theme()

    variables = f"""
    <style>
    :root {{
        --bg: {t['bg']};
        --surface: {t['surface']};
        --surface2: {t['surface2']};
        --border: {t['border']};
        --text: {t['text']};
        --muted: {t['muted']};
        --field: {t['input']};
        color-scheme: {'dark' if st.session_state.dark_mode else 'light'};
        --accent: {t['accent']};
        --accent-soft: {t['accent_soft']};
        --shadow: {t['shadow']};
        --button-text: {t['button_text']};
    }}
    </style>
    """

    st.markdown(variables, unsafe_allow_html=True)
    st.markdown(BASE_CSS, unsafe_allow_html=True)


# ============================================================
# PLOTLY HELPERS
# ============================================================

def plotly_config():
    return {
        "displayModeBar": False,
        "scrollZoom": False,
        "responsive": True,
    }


def style_chart(fig, height=340):
    t = theme()

    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text"], size=13, family="Manrope, Segoe UI, sans-serif"),
        margin=dict(l=10, r=10, t=10, b=10),
        dragmode=False,
        showlegend=False,
        hoverlabel=dict(
            bgcolor=t["surface2"],
            bordercolor=t["border"],
            font=dict(color=t["text"], size=13),
        ),
    )

    fig.update_xaxes(
        fixedrange=True,
        showgrid=False,
        zeroline=False,
        linecolor=t["border"],
        tickfont=dict(color=t["muted"]),
        title_font=dict(color=t["muted"]),
    )

    fig.update_yaxes(
        fixedrange=True,
        gridcolor=t["border"],
        zeroline=False,
        tickfont=dict(color=t["muted"]),
        title_font=dict(color=t["muted"]),
    )

    return fig


def show_chart(fig):
    try:
        st.plotly_chart(fig, width="stretch", config=plotly_config())
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=plotly_config())


def category_bar(category_totals, height=340):
    ordered = category_totals.sort_values(ascending=True)

    fig = go.Figure(
        go.Bar(
            x=ordered.values,
            y=ordered.index,
            orientation="h",
            marker_color=[CATEGORY_COLORS.get(c, "#94A3B8") for c in ordered.index],
            text=[format_rupees(v) for v in ordered.values],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color=theme()["muted"], size=12),
            hovertemplate="<b>%{y}</b><br>Amount: ₹%{x:,.2f}<extra></extra>",
        )
    )

    fig = style_chart(fig, height)
    fig.update_xaxes(showgrid=True, gridcolor=theme()["border"], tickprefix="₹", showticklabels=False)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(margin=dict(l=10, r=70, t=10, b=10), bargap=0.45)
    return fig


def monthly_bar(monthly, height=320):
    t = theme()

    fig = go.Figure(
        go.Bar(
            x=monthly.index,
            y=monthly.values,
            marker_color=t["accent"],
            text=[format_rupees(v) for v in monthly.values],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color=t["muted"], size=12),
            hovertemplate="<b>%{x}</b><br>Amount: ₹%{y:,.2f}<extra></extra>",
        )
    )

    fig = style_chart(fig, height)
    fig.update_yaxes(tickprefix="₹")
    fig.update_layout(bargap=0.55, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def donut_chart(category_totals, height=380):
    t = theme()
    total = float(category_totals.sum())

    fig = go.Figure(
        go.Pie(
            labels=category_totals.index,
            values=category_totals.values,
            hole=0.68,
            sort=False,
            marker=dict(
                colors=[CATEGORY_COLORS.get(c, "#94A3B8") for c in category_totals.index],
                line=dict(color=t["surface"], width=3),
            ),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>Amount: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>",
        )
    )

    fig = style_chart(fig, height)
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=-0.04,
            yanchor="top",
            font=dict(color=t["text"], size=12),
        ),
        annotations=[
            dict(
                text=f"<span style='font-size:12px;color:{t['muted']}'>Total</span><br>"
                     f"<b style='font-size:20px'>{format_rupees(total)}</b>",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                align="center",
                font=dict(color=t["text"]),
            )
        ],
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig


def daily_trend(df, height=300):
    t = theme()

    daily = (
        df.dropna(subset=["date"])
        .assign(day=lambda d: d["date"].dt.normalize())
        .groupby("day")["amount"]
        .sum()
        .sort_index()
    )

    fig = go.Figure(
        go.Scatter(
            x=daily.index,
            y=daily.values,
            mode="lines+markers",
            line=dict(color=t["accent"], width=3, shape="spline", smoothing=0.6),
            marker=dict(size=7, color=t["accent"], line=dict(color=t["surface"], width=2)),
            fill="tozeroy",
            fillcolor=t["accent_soft"],
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Spent: ₹%{y:,.2f}<extra></extra>",
        )
    )

    fig = style_chart(fig, height)
    fig.update_yaxes(tickprefix="₹")
    fig.update_xaxes(tickformat="%d %b")
    return fig


# ============================================================
# UI COMPONENTS
# ============================================================

def page_header(title, subtitle=""):
    html(
        f"""
        <div class="page-head">
            <div class="page-title">{title}</div>
            <div class="page-sub">{subtitle}</div>
        </div>
        """
    )


def section_title(title, subtitle=""):
    html(
        f"""
        <div class="sec-title">{title}</div>
        <div class="sec-sub">{subtitle}</div>
        """
    )


def render_kpi(title, value, description, icon="💰", tint="#2DD4BF"):
    html(
        f"""
        <div class="kpi">
            <div class="kpi-top">
                <div class="kpi-title">{title}</div>
                <div class="kpi-icon" style="background:{tint}26;">{icon}</div>
            </div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-desc">{description}</div>
        </div>
        """
    )


def category_pill(category):
    category = str(category) if str(category) else "Other"
    color = CATEGORY_COLORS.get(category, "#94A3B8")
    return (
        f'<span class="pill" style="background:{color}26;color:{color};">'
        f'<span class="dot" style="background:{color};"></span>{escape(category)}</span>'
    )


def expense_table(df, max_height=460):
    if df.empty:
        st.info("No expenses match your filters.")
        return

    rows = []

    for _, row in df.iterrows():
        date_text = row["date"].strftime("%d %b %Y") if pd.notna(row["date"]) else "—"

        rows.append(
            "<tr>"
            f"<td>{escape(str(row['name']))}</td>"
            f"<td>{category_pill(row['category'])}</td>"
            f"<td>{date_text}</td>"
            f"<td class='num'>{format_rupees(row['amount'])}</td>"
            "</tr>"
        )

    table = (
        f'<div class="tbl-wrap" style="max-height:{max_height}px;">'
        '<table class="tbl"><thead><tr>'
        "<th>Name</th><th>Category</th><th>Date</th><th class='num'>Amount</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )

    st.markdown(table, unsafe_allow_html=True)


def expense_cards(df):
    if df.empty:
        st.info("No expenses match your filters.")
        return

    items = []

    for _, row in df.iterrows():
        category = str(row["category"]) or "Other"
        color = CATEGORY_COLORS.get(category, "#94A3B8")
        icon = CATEGORY_ICONS.get(category, "📦")
        date_text = row["date"].strftime("%d %b %Y") if pd.notna(row["date"]) else "—"

        items.append(
            '<div class="exp-card">'
            f'<div class="exp-ico" style="background:{color}26;">{icon}</div>'
            '<div class="exp-main">'
            f'<div class="exp-name">{escape(str(row["name"]))}</div>'
            f'<div class="exp-meta">{escape(category)} • {date_text}</div>'
            "</div>"
            f'<div class="exp-amt">{format_rupees(row["amount"])}</div>'
            "</div>"
        )

    st.markdown('<div class="exp-list">' + "".join(items) + "</div>", unsafe_allow_html=True)


def expense_view(df, max_height=460):
    if is_mobile():
        expense_cards(df)
    else:
        expense_table(df, max_height=max_height)


def mobile_appbar(page):
    title = page
    html(
        f"""
        <div class="m-appbar">
            <div class="m-menu-btn" id="m-menu-btn">☰</div>
            <div class="brand-logo">💰</div>
            <div class="m-appbar-title">{title}</div>
        </div>
        """
    )


def mobile_hero(this_month, last_month, month_key):
    if last_month > 0:
        change = (this_month - last_month) / last_month * 100
        css = "up" if change > 0 else "down"
        arrow = "▲" if change > 0 else "▼"
        sub = f'<span class="{css}">{arrow} {abs(change):.1f}%</span> vs last month'
    else:
        sub = date.today().strftime("%A, %d %B")

    budget = float(load_budgets().get(month_key, 0))
    bar = ""

    if budget > 0:
        used = this_month / budget * 100
        color = "#F87171" if used > 100 else "#F59E0B" if used >= 80 else "#34D399"
        bar = (
            '<div class="budget-track">'
            f'<div class="budget-fill" style="width:{min(used, 100):.1f}%;background:{color};"></div>'
            "</div>"
            f'<div class="m-hero-sub" style="margin-top:8px;">{used:.0f}% of {format_rupees(budget)} budget used</div>'
        )

    html(
        f"""
        <div class="m-hero">
            <div class="m-hero-label">Spent this month</div>
            <div class="m-hero-value">{format_rupees(this_month)}</div>
            <div class="m-hero-sub">{sub}</div>
            {bar}
        </div>
        """
    )


def mobile_scripts():
    """Wires the app-bar menu button to the sidebar and closes the drawer after picking a page."""
    should_close = bool(st.session_state.get("close_drawer"))
    st.session_state.close_drawer = False

    script = """
    <script>
    (function () {
        const win = window.parent;
        const doc = win.document;

        function findSidebar() { return doc.querySelector('section[data-testid="stSidebar"]'); }

        function openDrawer() {
            const btn =
                doc.querySelector('[data-testid="stExpandSidebarButton"]') ||
                doc.querySelector('[data-testid="stSidebarCollapsedControl"] button') ||
                doc.querySelector('[data-testid="stSidebarCollapsedControl"]');
            if (btn) btn.click();
        }

        function closeDrawer() {
            if (win.innerWidth > 768) return;
            const sb = findSidebar();
            if (!sb) return;
            const btn =
                sb.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
                sb.querySelector('[data-testid="stSidebarHeader"] button') ||
                sb.querySelector('button[kind="header"]');
            if (btn) btn.click();
        }

        if (win.__menuHandler) {
            doc.removeEventListener('click', win.__menuHandler, true);
        }
        win.__menuHandler = function (event) {
            if (event.target && event.target.closest && event.target.closest('#m-menu-btn')) {
                openDrawer();
            }
        };
        doc.addEventListener('click', win.__menuHandler, true);

        if (__SHOULD_CLOSE__) {
            setTimeout(closeDrawer, 120);
            setTimeout(closeDrawer, 450);
        }
    })();
    </script>
    """.replace("__SHOULD_CLOSE__", "true" if should_close else "false")

    try:
        components.html(script, height=0)
    except Exception:
        pass


def field_fix_script():
    """Forces readable dark boxes + bright bold text on dropdowns, whatever Streamlit version is installed."""
    dark = bool(st.session_state.dark_mode)
    t = theme()

    script = r"""
    <script>
    (function () {
        const win = window.parent;
        const doc = win.document;
        const DARK = __DARK__;
        const FIELD = "__FIELD__";
        const TEXT = "__TEXT__";
        const PROPS = ["background-color", "background-image", "color",
                       "-webkit-text-fill-color", "opacity", "font-weight"];

        function clearAll() {
            doc.querySelectorAll("[data-ff]").forEach(function (el) {
                PROPS.forEach(function (p) { el.style.removeProperty(p); });
                el.removeAttribute("data-ff");
            });
        }

        if (win.__ffObserver) { win.__ffObserver.disconnect(); win.__ffObserver = null; }

        if (!DARK) { clearAll(); return; }

        function isLight(color) {
            const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
            if (!m) return false;
            const alpha = m[4] === undefined ? 1 : parseFloat(m[4]);
            return alpha > 0.5 && +m[1] > 235 && +m[2] > 235 && +m[3] > 235;
        }

        function paint(el) {
            el.style.setProperty("background-color", FIELD, "important");
            el.style.setProperty("background-image", "none", "important");
            el.setAttribute("data-ff", "1");
        }

        function textify(el) {
            el.style.setProperty("color", TEXT, "important");
            el.style.setProperty("-webkit-text-fill-color", TEXT, "important");
            el.style.setProperty("opacity", "1", "important");
            el.style.setProperty("font-weight", "600", "important");
            el.setAttribute("data-ff", "1");
        }

        function run() {
            // 1) every layer of every dropdown
            doc.querySelectorAll('[data-baseweb="select"], [data-baseweb="select"] *, [data-testid="stSelectbox"] *')
                .forEach(function (el) {
                    if (el instanceof win.SVGElement) return;
                    paint(el);
                    textify(el);
                });

            // 2) any other pure-white box left over in dark mode
            doc.querySelectorAll("div, span, input, ul, li").forEach(function (el) {
                if (el.hasAttribute("data-ff")) return;
                if (el.closest('[data-testid="stToggle"], [data-testid="stRadio"], [data-testid="stCheckbox"], .kpi-icon')) return;
                if (isLight(win.getComputedStyle(el).backgroundColor)) {
                    paint(el);
                    textify(el);
                }
            });
        }

        let timer = null;
        function schedule() {
            if (timer) return;
            timer = setTimeout(function () { timer = null; run(); }, 60);
        }

        win.__ffObserver = new MutationObserver(schedule);
        win.__ffObserver.observe(doc.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["class", "aria-expanded"]
        });

        [50, 300, 800, 1600].forEach(function (ms) { setTimeout(run, ms); });
    })();
    </script>
    """

    script = (
        script.replace("__DARK__", "true" if dark else "false")
        .replace("__FIELD__", t["input"])
        .replace("__TEXT__", "#F8FAFC")
    )

    try:
        components.html(script, height=0)
    except Exception:
        pass


# ============================================================
# SIDEBAR
# ============================================================

def sidebar():
    with st.sidebar:
        html(
            """
            <div class="brand">
                <div class="brand-logo">💰</div>
                <div>
                    <div class="brand-title">Expense Tracker</div>
                    <div class="brand-sub">Personal finance dashboard</div>
                </div>
            </div>
            <div class="nav-label">Menu</div>
            """
        )

        st.radio(
            "Go to",
            NAV_KEYS,
            key="nav_sidebar",
            on_change=_nav_changed,
            label_visibility="collapsed",
        )

        st.write("")
        st.divider()

        dark_mode = st.toggle("Dark mode", value=st.session_state.dark_mode)

        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()

        st.selectbox(
            "Layout",
            ["Auto", "Desktop", "Mobile"],
            key="view_mode",
            help="Auto picks the right layout for your device.",
        )

        html(
            """
            <div class="sidebar-foot">
                Python • Pandas • Plotly • Streamlit
            </div>
            """
        )

    return NAV_ITEMS[st.session_state.nav_sidebar]


# ============================================================
# DASHBOARD
# ============================================================

def page_dashboard(df):
    month_key = date.today().strftime("%Y-%m")
    this_month = month_total(df, month_key)
    last_month = month_total(df, previous_month_key())

    mobile = is_mobile()

    if mobile:
        mobile_hero(this_month, last_month, month_key)
    else:
        html(
            f"""
            <div class="dash-head">
                <div>
                    <div class="page-title">Dashboard</div>
                    <div class="page-sub">Your spending at a glance — {date.today().strftime('%A, %d %B %Y')}</div>
                </div>
                <div class="dash-chip">Spent this month <b>{format_rupees(this_month)}</b></div>
            </div>
            """
        )

    if df.empty:
        st.info("No expenses yet. Open Add Expense to record your first one.")
        return

    total = float(df["amount"].sum())
    count = len(df)
    average = float(df["amount"].mean())

    if last_month > 0:
        change = (this_month - last_month) / last_month * 100
        css = "up" if change > 0 else "down"
        arrow = "▲" if change > 0 else "▼"
        month_desc = f'<span class="{css}">{arrow} {abs(change):.1f}%</span> vs last month'
    else:
        month_desc = "Current month spending"

    cols = st.columns(4)

    with cols[0]:
        render_kpi("Total spending", format_rupees(total), "All recorded expenses", "💸", "#2DD4BF")
    with cols[1]:
        render_kpi("This month", format_rupees(this_month), month_desc, "📆", "#38BDF8")
    with cols[2]:
        render_kpi("Transactions", str(count), "Recorded expenses", "🧾", "#A78BFA")
    with cols[3]:
        render_kpi("Average expense", format_rupees(average), "Per transaction", "📈", "#F59E0B")

    st.write("")

    biggest = df.loc[df["amount"].idxmax()]
    category_totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_category = category_totals.index[0]
    top_amount = float(category_totals.iloc[0])
    top_share = top_amount / total * 100 if total else 0

    budget = float(load_budgets().get(month_key, 0))

    cols = st.columns(3)

    with cols[0]:
        render_kpi(
            "Biggest expense",
            format_rupees(biggest["amount"]),
            escape(str(biggest["name"])),
            "🏆",
            "#F59E0B",
        )
    with cols[1]:
        render_kpi(
            "Top category",
            escape(str(top_category)),
            f"{format_rupees(top_amount)} • {top_share:.0f}% of spending",
            "🧩",
            CATEGORY_COLORS.get(top_category, "#94A3B8"),
        )
    with cols[2]:
        if budget > 0:
            left = budget - this_month
            used = this_month / budget * 100
            render_kpi(
                "Budget left",
                format_rupees(left),
                f"{used:.0f}% of {format_rupees(budget)} used",
                "🎯",
                "#34D399" if left >= 0 else "#F87171",
            )
        else:
            render_kpi("Budget left", "Not set", "Set a monthly budget in Budget", "🎯", "#34D399")

    st.write("")

    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            section_title("Spending by category", "Where your money goes")
            show_chart(category_bar(category_totals, 300 if mobile else 340))

    with right:
        with st.container(border=True):
            section_title("Expense distribution", "Share of total spending")
            show_chart(donut_chart(category_totals, 360 if mobile else 380))

    st.write("")

    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            section_title("Daily trend", "How much you spend each day")
            show_chart(daily_trend(df, 240 if mobile else 300))

    with right:
        with st.container(border=True):
            section_title("Monthly spending", "Total spent per month")
            monthly = (
                df.dropna(subset=["date"])
                .assign(month=lambda d: d["date"].dt.strftime("%Y-%m"))
                .groupby("month")["amount"]
                .sum()
                .sort_index()
            )
            show_chart(monthly_bar(monthly, 250 if mobile else 300))

    st.write("")
    section_title("Recent expenses", "Your latest 10 transactions")

    recent = df.sort_values("date", ascending=False).head(10)
    expense_view(recent, max_height=440)


# ============================================================
# ADD EXPENSE
# ============================================================

def page_add(expenses):
    page_header("Add expense", "Record a new expense in a few seconds.")

    left, _ = st.columns([2, 1])

    with left:
        with st.form("add_expense_form", clear_on_submit=False):
            name = st.text_input("Expense name", placeholder="Example: Coffee")

            col1, col2 = st.columns(2)

            with col1:
                amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0, format="%.2f")
            with col2:
                category = st.selectbox("Category", CATEGORIES)

            expense_date = st.date_input("Date", value=date.today())

            submitted = st.form_submit_button("Add expense")

            if submitted:
                if not name.strip():
                    st.error("Enter an expense name.")

                elif amount <= 0:
                    st.error("Amount must be greater than zero.")

                else:
                    expenses.append(
                        {
                            "name": name.strip(),
                            "amount": float(amount),
                            "category": category,
                            "date": str(expense_date),
                        }
                    )

                    save_expenses(expenses)
                    st.success("Expense added.")
                    st.rerun()


# ============================================================
# VIEW / SEARCH
# ============================================================

def page_view(df):
    page_header("View & search", "Filter your expenses by name, category or amount.")

    if df.empty:
        st.info("No expenses available.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        name_query = st.text_input("Search by name", placeholder="Enter expense name...")
    with col2:
        category = st.selectbox("Category", ["All"] + CATEGORIES)
    with col3:
        min_amount = st.number_input("Minimum amount (₹)", min_value=0.0, value=0.0, step=50.0)

    filtered = df.copy()

    if name_query:
        filtered = filtered[
            filtered["name"].astype(str).str.contains(name_query, case=False, na=False)
        ]

    if category != "All":
        filtered = filtered[filtered["category"] == category]

    if min_amount > 0:
        filtered = filtered[filtered["amount"] >= min_amount]

    filtered = filtered.sort_values("date", ascending=False)

    st.write(f"Showing **{len(filtered)}** expense(s) • Total **{format_rupees(filtered['amount'].sum())}**")

    expense_view(filtered, max_height=560)


# ============================================================
# EDIT EXPENSE
# ============================================================

def page_edit(expenses):
    page_header("Edit expense", "Pick an expense and update its details.")

    if not expenses:
        st.info("No expenses available.")
        return

    selected_index = st.selectbox(
        "Select expense",
        range(len(expenses)),
        format_func=lambda index: expense_label(index, expenses[index]),
    )

    selected = expenses[selected_index]

    left, _ = st.columns([2, 1])

    with left:
        with st.form("edit_expense_form"):
            name = st.text_input("Expense name", value=str(selected.get("name", "")).strip())

            col1, col2 = st.columns(2)

            with col1:
                amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.0,
                    value=float(selected.get("amount", 0)),
                    step=1.0,
                )

            current_category = selected.get("category", "Other")
            if current_category not in CATEGORIES:
                current_category = "Other"

            with col2:
                category = st.selectbox(
                    "Category",
                    CATEGORIES,
                    index=CATEGORIES.index(current_category),
                )

            saved_date = parse_saved_date(selected.get("date")) or date.today()
            expense_date = st.date_input("Date", value=saved_date)

            submitted = st.form_submit_button("Save changes")

            if submitted:
                if not name.strip():
                    st.error("Expense name cannot be empty.")

                elif amount <= 0:
                    st.error("Amount must be greater than zero.")

                else:
                    expenses[selected_index] = {
                        "name": name.strip(),
                        "amount": float(amount),
                        "category": category,
                        "date": str(expense_date),
                    }

                    save_expenses(expenses)
                    st.success("Expense updated.")
                    st.rerun()


# ============================================================
# DELETE EXPENSE
# ============================================================

def page_delete(expenses):
    page_header("Delete expense", "Remove an expense permanently.")

    if not expenses:
        st.info("No expenses available.")
        return

    selected_index = st.selectbox(
        "Select expense to delete",
        range(len(expenses)),
        format_func=lambda index: expense_label(index, expenses[index]),
    )

    selected = expenses[selected_index]

    st.warning("You are about to delete this expense:")

    html(
        f"""
        <div class="kpi" style="min-height:auto;margin-bottom:16px;">
            <div class="kpi-title">{escape(str(selected.get('name', 'Unnamed')))}</div>
            <div class="kpi-value">{format_rupees(float(selected.get('amount', 0)))}</div>
            <div class="kpi-desc">{category_pill(selected.get('category', 'Other'))}</div>
        </div>
        """
    )

    confirm = st.checkbox("I understand this expense will be permanently deleted.")

    if st.button("Delete expense", disabled=not confirm):
        expenses.pop(selected_index)
        save_expenses(expenses)
        st.success("Expense deleted.")
        st.rerun()


# ============================================================
# CATEGORY ANALYSIS
# ============================================================

def page_category(df):
    page_header("Category analysis", "See which categories take the biggest share.")

    if df.empty:
        st.info("No expenses available.")
        return

    stats = (
        df.groupby("category")["amount"]
        .agg(["count", "sum"])
        .sort_values("sum", ascending=False)
    )
    total = float(stats["sum"].sum())
    category_totals = stats["sum"]

    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            section_title("Spending by category", "Total per category")
            show_chart(category_bar(category_totals))

    with right:
        with st.container(border=True):
            section_title("Share of spending", "Percentage of total")
            show_chart(donut_chart(category_totals))

    st.write("")

    rows = []
    for category, row in stats.iterrows():
        share = row["sum"] / total * 100 if total else 0
        color = CATEGORY_COLORS.get(category, "#94A3B8")

        rows.append(
            "<tr>"
            f"<td>{category_pill(category)}</td>"
            f"<td>{int(row['count'])}</td>"
            f"<td><div class='mini-bar'><div style='width:{share:.1f}%;background:{color};'></div></div></td>"
            f"<td>{share:.1f}%</td>"
            f"<td class='num'>{format_rupees(row['sum'])}</td>"
            "</tr>"
        )

    table = (
        '<div class="tbl-wrap"><table class="tbl"><thead><tr>'
        "<th>Category</th><th>Transactions</th><th>Share</th><th>%</th><th class='num'>Total</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )

    st.markdown(table, unsafe_allow_html=True)


# ============================================================
# MONTHLY ANALYSIS
# ============================================================

def page_monthly(df):
    page_header("Monthly analysis", "Track how your spending changes month to month.")

    valid = df.dropna(subset=["date"])

    if valid.empty:
        st.info("No expenses available.")
        return

    monthly = (
        valid.assign(month=valid["date"].dt.strftime("%Y-%m"))
        .groupby("month")["amount"]
        .agg(["count", "sum"])
        .sort_index()
    )

    with st.container(border=True):
        section_title("Monthly spending", "Total spent per month")
        show_chart(monthly_bar(monthly["sum"], 340))

    st.write("")

    rows = []
    previous = None

    for month, row in monthly.iterrows():
        if previous and previous > 0:
            change = (row["sum"] - previous) / previous * 100
            css = "up" if change > 0 else "down"
            arrow = "▲" if change > 0 else "▼"
            change_html = f'<span class="{css}">{arrow} {abs(change):.1f}%</span>'
        else:
            change_html = "—"

        previous = row["sum"]

        rows.append(
            "<tr>"
            f"<td>{month}</td>"
            f"<td>{int(row['count'])}</td>"
            f"<td>{change_html}</td>"
            f"<td class='num'>{format_rupees(row['sum'])}</td>"
            "</tr>"
        )

    table = (
        '<div class="tbl-wrap"><table class="tbl"><thead><tr>'
        "<th>Month</th><th>Transactions</th><th>Change</th><th class='num'>Total</th>"
        "</tr></thead><tbody>" + "".join(reversed(rows)) + "</tbody></table></div>"
    )

    st.markdown(table, unsafe_allow_html=True)


# ============================================================
# BUDGET
# ============================================================

def page_budget(df):
    page_header("Budget", "Set a monthly budget and compare it with your spending.")

    budgets = load_budgets()
    month_key = date.today().strftime("%Y-%m")
    current_budget = float(budgets.get(month_key, 0))

    left, _ = st.columns([2, 1])

    with left:
        budget = st.number_input(
            f"Budget for {month_key} (₹)",
            min_value=0.0,
            value=current_budget,
            step=500.0,
        )

        if st.button("Save budget"):
            budgets[month_key] = float(budget)
            save_budgets(budgets)
            st.success(f"Budget saved for {month_key}.")
            st.rerun()

    spending = month_total(df, month_key)
    remaining = budget - spending

    st.write("")

    cols = st.columns(3)

    with cols[0]:
        render_kpi("Monthly budget", format_rupees(budget), month_key, "🎯", "#2DD4BF")
    with cols[1]:
        render_kpi("Monthly spending", format_rupees(spending), "Current month", "💸", "#38BDF8")
    with cols[2]:
        render_kpi(
            "Remaining",
            format_rupees(remaining),
            "Budget remaining" if remaining >= 0 else "Over budget",
            "🧮",
            "#34D399" if remaining >= 0 else "#F87171",
        )

    st.write("")

    if budget <= 0:
        st.info("Set a budget above to start tracking this month.")
        return

    used = spending / budget * 100

    if used > 100:
        color, message = "#F87171", "You have exceeded your monthly budget."
    elif used >= 80:
        color, message = "#F59E0B", "You have used more than 80% of your budget."
    else:
        color, message = "#34D399", "You are within your budget."

    html(
        f"""
        <div class="kpi" style="min-height:auto;">
            <div class="kpi-title">{message}</div>
            <div class="budget-track" style="margin-top:12px;">
                <div class="budget-fill" style="width:{min(used, 100):.1f}%;background:{color};"></div>
            </div>
            <div class="budget-meta">
                <span>{used:.1f}% used</span>
                <span>{format_rupees(spending)} of {format_rupees(budget)}</span>
            </div>
        </div>
        """
    )


# ============================================================
# MAIN
# ============================================================

def main():
    inject_css()
    field_fix_script()

    expenses = load_expenses()
    df = expenses_to_dataframe(expenses)

    page = sidebar()

    if is_mobile():
        mobile_appbar(page)
        mobile_scripts()

    if page == "Dashboard":
        page_dashboard(df)
    elif page == "Add Expense":
        page_add(expenses)
    elif page == "View / Search":
        page_view(df)
    elif page == "Edit Expense":
        page_edit(expenses)
    elif page == "Delete Expense":
        page_delete(expenses)
    elif page == "Category Analysis":
        page_category(df)
    elif page == "Monthly Analysis":
        page_monthly(df)
    elif page == "Budget":
        page_budget(df)


if __name__ == "__main__":
    main()