"""Dark and light themes: Qt stylesheet plus matching chart colours."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str
    surface2: str
    border: str
    text: str
    text2: str
    muted: str
    accent: str
    accent_text: str
    good: str
    bad: str
    warn: str
    input_bg: str
    series: tuple[str, ...]
    grid: str


DARK = Palette(
    name="dark", bg="#14171c", surface="#1d2229", surface2="#252b34", border="#323a45",
    text="#eef1f5", text2="#c2c9d3", muted="#8a94a3", accent="#3987e5", accent_text="#ffffff",
    good="#3fbf7f", bad="#ef6b6b", warn="#e0a33a", input_bg="#11151a",
    series=("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"),
    grid="#2c333d")

LIGHT = Palette(
    name="light", bg="#eef1f5", surface="#ffffff", surface2="#f5f7fa", border="#d5dbe3",
    text="#121821", text2="#3d4756", muted="#6b7585", accent="#2a78d6", accent_text="#ffffff",
    good="#1f8f57", bad="#c93636", warn="#a86f00", input_bg="#ffffff",
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"),
    grid="#e3e7ed")


def palette(name: str) -> Palette:
    return LIGHT if name == "light" else DARK


def stylesheet(p: Palette, base_pt: int = 10) -> str:
    return f"""
* {{ font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif; font-size: {base_pt}pt; }}
QMainWindow, QWidget#Page, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {p.bg}; color: {p.text}; }}
QWidget {{ color: {p.text}; }}
QLabel {{ background: transparent; }}
QLabel#H1 {{ font-size: {base_pt + 10}pt; font-weight: 700; }}
QLabel#H2 {{ font-size: {base_pt + 4}pt; font-weight: 600; }}
QLabel#H3 {{ font-size: {base_pt + 1}pt; font-weight: 600; color: {p.text2}; }}
QLabel#Muted {{ color: {p.muted}; }}
QLabel#Good {{ color: {p.good}; font-weight: 600; }}
QLabel#Bad {{ color: {p.bad}; font-weight: 600; }}
QLabel#Warn {{ color: {p.warn}; font-weight: 600; }}
QFrame#Card {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px; }}
QFrame#Sidebar {{ background: {p.surface}; border-right: 1px solid {p.border}; }}
QLabel#Brand {{ font-size: {base_pt + 3}pt; font-weight: 700; color: {p.accent}; padding: 8px 6px; }}
QListWidget#Nav {{ background: transparent; border: none; outline: 0; }}
QListWidget#Nav::item {{ padding: 9px 10px; border-radius: 7px; margin: 1px 4px; color: {p.text2}; }}
QListWidget#Nav::item:hover {{ background: {p.surface2}; }}
QListWidget#Nav::item:selected {{ background: {p.accent}; color: {p.accent_text}; }}
QPushButton {{ background: {p.surface2}; border: 1px solid {p.border}; border-radius: 7px; padding: 7px 14px; }}
QPushButton:hover {{ border-color: {p.accent}; }}
QPushButton:disabled {{ color: {p.muted}; }}
QPushButton#Primary {{ background: {p.accent}; color: {p.accent_text}; border: none; font-weight: 600; }}
QPushButton#Primary:disabled {{ background: {p.border}; color: {p.muted}; }}
QPushButton#Danger {{ background: {p.bad}; color: white; border: none; }}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {p.input_bg}; border: 1px solid {p.border}; border-radius: 6px; padding: 5px; color: {p.text};
    selection-background-color: {p.accent}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {p.accent}; }}
QComboBox QAbstractItemView {{ background: {p.surface}; color: {p.text}; selection-background-color: {p.accent}; }}
QTextBrowser {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; padding: 10px; color: {p.text}; }}
QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 8px; background: {p.surface}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {p.text2}; padding: 8px 14px; border: none; margin-right: 2px; }}
QTabBar::tab:selected {{ color: {p.accent}; border-bottom: 2px solid {p.accent}; font-weight: 600; }}
QTreeWidget, QListWidget {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 6px; color: {p.text};
    outline: 0; }}
QTreeWidget::item {{ padding: 3px 2px; color: {p.text}; }}
QTreeWidget::item:selected {{ background: {p.accent}; color: {p.accent_text}; }}
QTreeWidget::item:hover:!selected {{ background: {p.surface2}; }}
QTabBar QToolButton {{ background: {p.surface2}; border: 1px solid {p.border}; border-radius: 4px; color: {p.text}; }}
QSplitter::handle {{ background: {p.bg}; }}
QTableWidget, QTableView {{ background: {p.surface}; alternate-background-color: {p.surface2}; gridline-color: {p.grid};
    border: 1px solid {p.border}; border-radius: 6px; color: {p.text}; }}
QHeaderView::section {{ background: {p.surface2}; color: {p.text2}; padding: 5px; border: none;
    border-bottom: 1px solid {p.border}; font-weight: 600; }}
QProgressBar {{ background: {p.surface2}; border: none; border-radius: 5px; height: 10px; text-align: center; color: {p.text}; }}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 5px; }}
QCheckBox, QRadioButton {{ background: transparent; spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; border: 2px solid {p.muted};
    background: {p.input_bg}; }}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {p.accent}; }}
QCheckBox::indicator:checked {{ background: {p.accent}; border-color: {p.accent}; }}
QRadioButton::indicator:checked {{ background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
    stop:0 {p.accent_text}, stop:0.35 {p.accent_text}, stop:0.45 {p.accent}, stop:1 {p.accent}); border-color: {p.accent}; }}
QGroupBox {{ border: 1px solid {p.border}; border-radius: 8px; margin-top: 14px; padding: 10px; background: {p.surface}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {p.text2}; font-weight: 600; }}
QSlider::groove:horizontal {{ height: 6px; background: {p.surface2}; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 16px; margin: -6px 0; border-radius: 8px; background: {p.accent}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 5px; min-height: 30px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {p.border}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QAbstractScrollArea::corner {{ background: transparent; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QStatusBar {{ background: {p.surface}; color: {p.muted}; }}
QToolTip {{ background: {p.surface2}; color: {p.text}; border: 1px solid {p.border}; }}
"""


def style_axes(ax, p: Palette, title: str = "", ylabel: str = ""):
    """Recessive axes and grid; text in text colours, never series colours."""
    ax.set_facecolor(p.surface)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(p.border)
    ax.tick_params(colors=p.text2, labelsize=8)
    ax.yaxis.grid(True, color=p.grid, linewidth=0.8)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, color=p.text, fontsize=10, loc="left", fontweight="bold")
    if ylabel:
        ax.set_ylabel(ylabel, color=p.text2, fontsize=8)
